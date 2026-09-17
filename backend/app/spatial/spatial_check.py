"""
Spatial Neighbor Coherence Checker.
Compares a station's current measurement against the spatial median of neighboring
stations within the network. Differentiates isolated sensor faults from regional weather events.
"""
from typing import Dict, Any, List, Optional
import numpy as np
from app.config import (
    SPATIAL_TEMP_DEV_THRESHOLD,
    SPATIAL_PRESSURE_DEV_THRESHOLD,
    SPATIAL_HUMIDITY_DEV_THRESHOLD
)


class SpatialValidator:
    def __init__(self):
        # Keeps track of the most recent reading from every station
        # { station_id: { "temp": float, "pressure": float, "humidity": float, "timestamp": str } }
        self.latest_network_readings: Dict[str, Dict[str, Any]] = {}

    def update_network_reading(self, station_id: str, temp: float, pressure: float, humidity: float, timestamp: str) -> None:
        """Stores latest reading for neighbor comparison."""
        self.latest_network_readings[station_id] = {
            "temp": temp,
            "pressure": pressure,
            "humidity": humidity,
            "timestamp": timestamp
        }

    def check_spatial_coherence(
        self,
        target_station_id: str,
        current_temp: float,
        current_pressure: float,
        current_humidity: float
    ) -> Dict[str, Any]:
        """
        Compares target station against all other currently active neighbor stations.
        Returns:
            {
                "is_isolated_anomaly": bool,
                "is_regional_event": bool,
                "neighbor_count": int,
                "temp_dev": float,
                "pressure_dev": float,
                "humidity_dev": float,
                "neighbor_median_temp": float,
                "reason": str
            }
        """
        # Gather neighbors (all other stations)
        neighbors = [
            r for sid, r in self.latest_network_readings.items()
            if sid != target_station_id
        ]

        if len(neighbors) < 2:
            return {
                "is_isolated_anomaly": False,
                "is_regional_event": False,
                "neighbor_count": len(neighbors),
                "reason": "Insufficient neighboring stations reporting concurrently."
            }

        neighbor_temps = [n["temp"] for n in neighbors]
        neighbor_pressures = [n["pressure"] for n in neighbors]
        neighbor_humidities = [n["humidity"] for n in neighbors]

        median_temp = float(np.median(neighbor_temps))
        median_pres = float(np.median(neighbor_pressures))
        median_hum = float(np.median(neighbor_humidities))

        temp_dev = abs(current_temp - median_temp)
        pres_dev = abs(current_pressure - median_pres)
        hum_dev = abs(current_humidity - median_hum)

        # Check neighbor internal dispersion (are neighbors in agreement?)
        neighbor_temp_std = float(np.std(neighbor_temps))

        is_temp_discordant = temp_dev > SPATIAL_TEMP_DEV_THRESHOLD
        is_pres_discordant = pres_dev > SPATIAL_PRESSURE_DEV_THRESHOLD
        is_hum_discordant = hum_dev > SPATIAL_HUMIDITY_DEV_THRESHOLD

        # If target station strongly disagrees while neighbors agree among themselves
        is_isolated = (
            (is_temp_discordant or is_pres_discordant or is_hum_discordant)
            and neighbor_temp_std < 2.5
        )

        # If multiple stations are showing high variance / shift across the region
        is_regional = neighbor_temp_std >= 2.5

        reasons = []
        if is_temp_discordant:
            reasons.append(
                f"Station temperature ({current_temp:.1f}°C) deviates by {temp_dev:.1f}°C "
                f"from neighbor median ({median_temp:.1f}°C)."
            )
        if is_pres_discordant:
            reasons.append(
                f"Pressure ({current_pressure:.1f} hPa) deviates by {pres_dev:.1f} hPa "
                f"from neighbor median ({median_pres:.1f} hPa)."
            )

        reason_str = " ".join(reasons) if reasons else "Spatial readings coherent with network."

        return {
            "is_isolated_anomaly": is_isolated,
            "is_regional_event": is_regional,
            "neighbor_count": len(neighbors),
            "temp_dev": round(temp_dev, 2),
            "pressure_dev": round(pres_dev, 2),
            "humidity_dev": round(hum_dev, 2),
            "neighbor_median_temp": round(median_temp, 2),
            "neighbor_median_pressure": round(median_pres, 2),
            "reason": reason_str
        }
