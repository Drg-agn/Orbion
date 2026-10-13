"""
Orchestrator: Anomaly Detection and Fault vs. Weather Event Classification.
Combines Physics Engine, ML Temporal Score, and Spatial Neighbor Validation
using the multi-variable consistency logic from Algorithm 1 of the paper.
"""
from typing import Dict, Any, List, Optional
from app.physics.engine import PhysicsEngine
from app.spatial.spatial_check import SpatialValidator
from app.ml.model_interface import MLModelInterface
from app.database import update_station_health, insert_alert, insert_reading


class AnomalyDetector:
    def __init__(self):
        self.physics = PhysicsEngine()
        self.spatial = SpatialValidator()
        self.ml = MLModelInterface()

        # Sliding window of readings per station for ML & spike reversal check
        # { station_id: [ {"temp": float, "humidity": float, "pressure": float, "dew_point": float, "timestamp": str} ] }
        self.station_windows: Dict[str, List[Dict[str, Any]]] = {}

        # Station health scores (cached in-memory, persisted in SQLite)
        self.station_health: Dict[str, float] = {}

    def _get_window(self, station_id: str) -> List[Dict[str, Any]]:
        if station_id not in self.station_windows:
            self.station_windows[station_id] = []
        return self.station_windows[station_id]

    def _get_health(self, station_id: str) -> float:
        if station_id not in self.station_health:
            self.station_health[station_id] = 100.0
        return self.station_health[station_id]

    def _update_health(self, station_id: str, delta: float) -> float:
        current = self._get_health(station_id)
        updated = max(0.0, min(100.0, current + delta))
        self.station_health[station_id] = round(updated, 1)

        # Status category
        if updated >= 80.0:
            status = "healthy"
        elif updated >= 60.0:
            status = "warning"
        elif updated >= 30.0:
            status = "critical"
        else:
            status = "offline"

        update_station_health(station_id, updated, status)
        return updated

    def process_reading(
        self,
        station_id: str,
        timestamp: str,
        temp: float,
        humidity: float,
        pressure: float
    ) -> Dict[str, Any]:
        """
        Processes an incoming sensor reading through:
          1. Physics validation (dew point, limits, rate of change, frozen)
          2. Spatial neighbor comparison
          3. ML Temporal feature extraction & scoring
          4. Fault vs. Event classification (Algorithm 1)
        """
        # 1. Physics Engine Check
        phys_result = self.physics.evaluate(station_id, temp, humidity, pressure)
        dew_point = phys_result["dew_point"]

        # 2. Update Spatial Validator
        self.spatial.update_network_reading(station_id, temp, pressure, humidity, timestamp)
        spatial_result = self.spatial.check_spatial_coherence(station_id, temp, pressure, humidity)

        # 3. Maintain sliding window (up to 36 readings = 6 hours)
        window = self._get_window(station_id)
        current_entry = {
            "temp": temp,
            "humidity": humidity,
            "pressure": pressure,
            "dew_point": dew_point,
            "timestamp": timestamp
        }
        window.append(current_entry)
        if len(window) > 36:
            window.pop(0)

        # 4. ML Temporal Score
        ml_result = self.ml.predict(window)

        # 5. Insert reading into SQLite
        insert_reading(station_id, timestamp, temp, dew_point, humidity, pressure)

        # 6. Fault vs. Event Classification Engine (Algorithm 1)
        alert: Optional[Dict[str, Any]] = None
        classification: Optional[str] = None
        severity = "info"
        confidence = 0.90
        reason = ""
        rule = "normal"
        suspect_sensor = None

        # Check Step 1: Physical Limits or Dew Point Violation
        hard_violations = [v for v in phys_result["violations"] if "out_of_bounds" in v["rule"] or v["rule"] == "dew_point_violation"]
        frozen_violations = [v for v in phys_result["violations"] if "frozen" in v["rule"]]
        roc_violations = [v for v in phys_result["violations"] if "rate_limit" in v["rule"]]

        if hard_violations:
            first_v = hard_violations[0]
            classification = "sensor_fault"
            severity = "critical"
            confidence = first_v.get("confidence", 0.99)
            reason = first_v.get("reason", "Physical law or absolute limit violation.")
            rule = first_v.get("rule", "physical_violation")
            suspect_sensor = first_v.get("suspect_sensor", "temperature")
            self._update_health(station_id, -30.0)

        elif frozen_violations:
            first_v = frozen_violations[0]
            classification = "sensor_fault"
            severity = "critical"
            confidence = first_v.get("confidence", 0.95)
            reason = first_v.get("reason", "Sensor reading frozen at constant value.")
            rule = first_v.get("rule", "frozen_sensor")
            suspect_sensor = first_v.get("suspect_sensor", "temperature")
            self._update_health(station_id, -25.0)

        elif roc_violations or ml_result["is_anomaly"] or spatial_result["is_isolated_anomaly"]:
            # We have an anomaly! Now decide: SENSOR FAULT vs GENUINE WEATHER EVENT
            # Check multivariate co-movement:
            # Weather events change >= 2 variables coherently (e.g. cold front: temp drops & pressure rises)
            # Sensor faults affect only 1 variable (e.g. temp spikes while pressure/humidity are steady)
            prev_entry = window[-2] if len(window) >= 2 else current_entry
            d_temp = temp - prev_entry["temp"]
            d_pres = pressure - prev_entry["pressure"]
            d_hum = humidity - prev_entry["humidity"]

            # Significant changes defined by thresholds
            temp_moved = abs(d_temp) >= 2.0
            pres_moved = abs(d_pres) >= 1.5
            hum_moved = abs(d_hum) >= 8.0

            variables_moved = sum([temp_moved, pres_moved, hum_moved])

            # Spike reversal check (paper step 10): did a huge jump reverse immediately?
            is_spike = False
            if len(window) >= 3:
                two_back = window[-3]
                if abs(temp - two_back["temp"]) < 1.0 and abs(prev_entry["temp"] - two_back["temp"]) >= 3.0:
                    is_spike = True

            if is_spike:
                classification = "sensor_fault"
                severity = "critical"
                confidence = 0.98
                rule = "spike_anomaly"
                suspect_sensor = "temperature"
                reason = f"Transient electrical spike detected: reading jumped to {prev_entry['temp']:.1f}°C and promptly reversed."
                self._update_health(station_id, -20.0)

            elif variables_moved >= 2 and (not spatial_result["is_isolated_anomaly"] or spatial_result["is_regional_event"]):
                # Physically consistent co-movement + regional coherence = WEATHER EVENT
                classification = "weather_event"
                severity = "warning"
                confidence = 0.92
                rule = "co_movement_weather_event"
                suspect_sensor = None
                reason = (
                    f"Genuine regional weather event (e.g. cold front / thunderstorm outflow): "
                    f"multi-variable co-movement confirmed (ΔT={d_temp:+.1f}°C, ΔP={d_pres:+.1f} hPa, ΔH={d_hum:+.1f}%) "
                    f"with coherent neighbor response across {spatial_result.get('neighbor_count', 0)} stations."
                )
                # Weather events don't degrade sensor health permanently!
                self._update_health(station_id, -2.0)

            elif spatial_result["is_isolated_anomaly"]:
                # Single station deviated while neighbors stayed quiet = SENSOR FAULT
                classification = "sensor_fault"
                severity = "critical"
                confidence = 0.94
                rule = "spatial_discordance_fault"
                suspect_sensor = "temperature" if temp_moved else ("pressure" if pres_moved else "humidity")
                reason = (
                    f"Isolated sensor fault: {spatial_result['reason']} "
                    f"Neighboring stations report stable conditions without corresponding shift."
                )
                self._update_health(station_id, -20.0)

            else:
                # Moderate single-variable drift / rate limit warning
                classification = "sensor_fault"
                severity = "warning"
                confidence = 0.85
                rule = roc_violations[0]["rule"] if roc_violations else "temporal_drift_anomaly"
                suspect_sensor = roc_violations[0].get("suspect_sensor", "temperature") if roc_violations else "temperature"
                reason = roc_violations[0]["reason"] if roc_violations else f"Single-variable drift detected without multivariate backing (anomaly score: {ml_result['anomaly_score']})."
                self._update_health(station_id, -10.0)

        else:
            # Everything is normal: gradual health recovery
            self._update_health(station_id, +1.0)

        # Save alert if anomaly detected
        if classification:
            alert_id = insert_alert(
                station_id=station_id,
                timestamp=timestamp,
                classification=classification,
                severity=severity,
                confidence=confidence,
                suspect_sensor=suspect_sensor or "none",
                reason=reason,
                rule=rule
            )
            alert = {
                "id": alert_id,
                "station_id": station_id,
                "timestamp": timestamp,
                "classification": classification,
                "severity": severity,
                "confidence": confidence,
                "suspect_sensor": suspect_sensor,
                "reason": reason,
                "rule": rule
            }

        current_health = self._get_health(station_id)

        return {
            "station_id": station_id,
            "timestamp": timestamp,
            "reading": {
                "temperature": temp,
                "dew_point": dew_point,
                "humidity": humidity,
                "pressure": pressure
            },
            "physics": phys_result,
            "spatial": spatial_result,
            "ml": ml_result,
            "alert": alert,
            "health_score": current_health
        }
