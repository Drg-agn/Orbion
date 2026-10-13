"""
Unified Physics Engine.
Combines Dew Point constraint, Hard Physical Bounds, Rate-of-Change step limits,
and Frozen Sensor checks into a single validated report.
"""
from typing import List, Dict, Any, Optional
from app.physics.dew_point import check_dew_point_violation, calculate_dew_point
from app.physics.bounds import check_physical_bounds
from app.physics.rate_change import check_rate_of_change
from app.physics.frozen_sensor import check_frozen_sensors


class PhysicsEngine:
    def __init__(self):
        # Rolling historical buffers per station for temporal checks
        self.history: Dict[str, Dict[str, List[float]]] = {}

    def _get_history(self, station_id: str) -> Dict[str, List[float]]:
        if station_id not in self.history:
            self.history[station_id] = {
                "temp": [],
                "humidity": [],
                "pressure": []
            }
        return self.history[station_id]

    def evaluate(
        self,
        station_id: str,
        temp: float,
        humidity: float,
        pressure: float
    ) -> Dict[str, Any]:
        """
        Executes all physical rule checks on the current reading.
        Returns:
            {
                "dew_point": float,
                "is_valid": bool,
                "violations": List[Dict[str, Any]],
                "max_severity": str,   # 'normal', 'warning', 'critical'
                "suspect_sensors": List[str]
            }
        """
        hist = self._get_history(station_id)
        prev_t = hist["temp"][-1] if hist["temp"] else None
        prev_h = hist["humidity"][-1] if hist["humidity"] else None
        prev_p = hist["pressure"][-1] if hist["pressure"] else None

        violations: List[Dict[str, Any]] = []

        # 1. Dew Point Constraint (Rule 1)
        dew_point = calculate_dew_point(temp, humidity)
        dp_violation = check_dew_point_violation(temp, humidity)
        if dp_violation:
            violations.append(dp_violation)

        # 2. Hard Physical Bounds (Rule 2)
        bounds_violations = check_physical_bounds(temp, humidity, pressure)
        violations.extend(bounds_violations)

        # 3. Rate of Change Limits (Rule 3)
        roc_violations = check_rate_of_change(temp, humidity, pressure, prev_t, prev_h, prev_p)
        violations.extend(roc_violations)

        # 4. Frozen Sensor Checks (Rule 4)
        frozen_violations = check_frozen_sensors(hist["temp"], hist["humidity"], hist["pressure"])
        violations.extend(frozen_violations)

        # Update historical memory buffer (keep last 60 readings = 10 hours)
        hist["temp"].append(temp)
        hist["humidity"].append(humidity)
        hist["pressure"].append(pressure)
        if len(hist["temp"]) > 60:
            hist["temp"].pop(0)
            hist["humidity"].pop(0)
            hist["pressure"].pop(0)

        # Determine severity and suspect sensors
        is_valid = len(violations) == 0
        severities = [v.get("severity", "warning") for v in violations]
        max_severity = "critical" if "critical" in severities else ("warning" if "warning" in severities else "normal")

        suspect_sensors = list({v.get("suspect_sensor") for v in violations if v.get("suspect_sensor")})

        return {
            "dew_point": dew_point,
            "is_valid": is_valid,
            "violations": violations,
            "max_severity": max_severity,
            "suspect_sensors": suspect_sensors
        }
