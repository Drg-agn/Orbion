"""
Frozen / Stuck Sensor Detector.
Flags sensors reporting flatlined, constant values over extended time windows.
In nature, real atmospheric micro-turbulences produce minor continuous fluctuations.
"""
from typing import List, Dict, Any
import numpy as np
from app.config import FROZEN_WINDOW_SIZE, FROZEN_VARIANCE_EPS


def check_frozen_sensors(
    temp_history: List[float],
    humidity_history: List[float],
    pressure_history: List[float],
    min_window: int = FROZEN_WINDOW_SIZE
) -> List[Dict[str, Any]]:
    """
    Checks if any sensor has variance near zero (< epsilon) over window size.
    Exceptions: Fog conditions allow humidity to hover near 100%.
    """
    violations = []

    # Check Temperature
    if len(temp_history) >= min_window:
        recent_t = temp_history[-min_window:]
        variance = float(np.var(recent_t))
        if variance < FROZEN_VARIANCE_EPS:
            violations.append({
                "rule": "frozen_temperature_sensor",
                "severity": "critical",
                "confidence": 0.96,
                "suspect_sensor": "temperature",
                "variance": variance,
                "reason": (
                    f"Temperature sensor stuck at {recent_t[-1]:.2f}°C without variation "
                    f"over {len(recent_t)} consecutive readings ({len(recent_t)*10 // 60} hours)."
                )
            })

    # Check Pressure
    if len(pressure_history) >= min_window:
        recent_p = pressure_history[-min_window:]
        variance = float(np.var(recent_p))
        if variance < FROZEN_VARIANCE_EPS:
            violations.append({
                "rule": "frozen_pressure_sensor",
                "severity": "critical",
                "confidence": 0.95,
                "suspect_sensor": "pressure",
                "variance": variance,
                "reason": (
                    f"Barometric pressure sensor stuck flat at {recent_p[-1]:.2f} hPa "
                    f"over {len(recent_p)} readings."
                )
            })

    # Check Humidity (Exclude persistent saturation near 100% in fog)
    if len(humidity_history) >= min_window:
        recent_h = humidity_history[-min_window:]
        variance = float(np.var(recent_h))
        is_fog = all(v >= 99.5 for v in recent_h)
        if variance < FROZEN_VARIANCE_EPS and not is_fog:
            violations.append({
                "rule": "frozen_humidity_sensor",
                "severity": "critical",
                "confidence": 0.94,
                "suspect_sensor": "humidity",
                "variance": variance,
                "reason": (
                    f"Humidity sensor stuck at {recent_h[-1]:.1f}% over "
                    f"{len(recent_h)} readings (unrelated to 100% fog saturation)."
                )
            })

    return violations
