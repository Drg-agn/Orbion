"""
Dew Point Calculation and Physical Constraint Verification.
Uses the Magnus-Tetens formula:
  gamma = ln(RH / 100) + (b * T) / (c + T)
  Td    = (c * gamma) / (b - gamma)
where b = 17.62, c = 243.12°C.

Physical Law: Dew point temperature can NEVER exceed ambient air temperature (Td <= T).
A violation indicates a 100% certain sensor fault in either the temperature or humidity sensor.
"""
import math
from typing import Optional, Dict, Any
from app.config import DEW_POINT_TOLERANCE

B_CONST = 17.62
C_CONST = 243.12


def calculate_dew_point(temp: float, humidity: float) -> float:
    """
    Computes Dew Point (Td) in °C using Magnus approximation.
    Handles edge conditions (RH clamped to [0.1, 100]).
    """
    rh_clamped = max(0.1, min(100.0, humidity))
    try:
        gamma = math.log(rh_clamped / 100.0) + (B_CONST * temp) / (C_CONST + temp)
        if B_CONST - gamma == 0:
            return temp
        td = (C_CONST * gamma) / (B_CONST - gamma)
        return round(td, 2)
    except Exception:
        return round(temp, 2)


def check_dew_point_violation(temp: float, humidity: float, tolerance: float = DEW_POINT_TOLERANCE) -> Optional[Dict[str, Any]]:
    """
    Verifies the dew point constraint: Td <= T + tolerance.
    Returns anomaly dictionary if violated, None otherwise.
    """
    td = calculate_dew_point(temp, humidity)
    diff = td - temp

    if diff > tolerance:
        # If humidity is high and T is very low, or vice versa, isolate suspect sensor
        suspect = "humidity" if humidity >= 95.0 else "temperature"
        return {
            "rule": "dew_point_violation",
            "severity": "critical",
            "confidence": 0.99,
            "dew_point": td,
            "temp": temp,
            "humidity": humidity,
            "suspect_sensor": suspect,
            "reason": (
                f"Physical dew point violation: Td ({td:.1f}°C) exceeds ambient temperature "
                f"({temp:.1f}°C) by {diff:.1f}°C (tolerance is {tolerance}°C)."
            )
        }
    return None
