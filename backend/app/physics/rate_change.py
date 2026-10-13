"""
Rate-of-Change (Step Check) Validator.
Calculates delta changes between consecutive readings and flags unphysical jumps.
"""
from typing import List, Dict, Any, Optional
from app.config import (
    MAX_TEMP_CHANGE_PER_10MIN,
    MAX_PRESSURE_CHANGE_PER_10MIN,
    MAX_HUMIDITY_CHANGE_PER_10MIN
)


def check_rate_of_change(
    current_temp: float,
    current_humidity: float,
    current_pressure: float,
    prev_temp: Optional[float] = None,
    prev_humidity: Optional[float] = None,
    prev_pressure: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Checks if 10-minute step change exceeds maximum natural meteorological gradient.
    Sudden huge jumps usually indicate electrical noise spikes.
    """
    violations = []
    if prev_temp is None:
        return violations

    delta_t = abs(current_temp - prev_temp)
    if delta_t > MAX_TEMP_CHANGE_PER_10MIN:
        violations.append({
            "rule": "temperature_rate_limit",
            "severity": "warning" if delta_t <= MAX_TEMP_CHANGE_PER_10MIN * 1.8 else "critical",
            "confidence": min(0.98, round(0.70 + (delta_t / MAX_TEMP_CHANGE_PER_10MIN) * 0.1, 2)),
            "suspect_sensor": "temperature",
            "delta": round(delta_t, 2),
            "reason": (
                f"Abrupt temperature change of {delta_t:.1f}°C in 10 minutes exceeds "
                f"maximum limit of {MAX_TEMP_CHANGE_PER_10MIN}°C/step."
            )
        })

    if prev_pressure is not None:
        delta_p = abs(current_pressure - prev_pressure)
        if delta_p > MAX_PRESSURE_CHANGE_PER_10MIN:
            violations.append({
                "rule": "pressure_rate_limit",
                "severity": "warning",
                "confidence": 0.85,
                "suspect_sensor": "pressure",
                "delta": round(delta_p, 2),
                "reason": (
                    f"Atmospheric pressure jump of {delta_p:.1f} hPa in 10 minutes "
                    f"exceeds physical rate threshold ({MAX_PRESSURE_CHANGE_PER_10MIN} hPa)."
                )
            })

    if prev_humidity is not None:
        delta_h = abs(current_humidity - prev_humidity)
        if delta_h > MAX_HUMIDITY_CHANGE_PER_10MIN:
            violations.append({
                "rule": "humidity_rate_limit",
                "severity": "warning",
                "confidence": 0.80,
                "suspect_sensor": "humidity",
                "delta": round(delta_h, 2),
                "reason": (
                    f"Relative humidity jumped {delta_h:.1f}% in 10 minutes "
                    f"(maximum expected is {MAX_HUMIDITY_CHANGE_PER_10MIN}%)."
                )
            })

    return violations
