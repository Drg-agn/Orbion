"""
Absolute Earth/Atmospheric Physical Bounds Validator.
Checks whether sensor values fall within climatological limits.
"""
from typing import List, Dict, Any
from app.config import (
    TEMP_MIN, TEMP_MAX,
    PRESSURE_MIN, PRESSURE_MAX,
    HUMIDITY_MIN, HUMIDITY_MAX
)


def check_physical_bounds(temp: float, humidity: float, pressure: float) -> List[Dict[str, Any]]:
    """
    Validates sensor values against hard Earth extremes.
    Values outside these ranges are impossible in real weather.
    """
    violations = []

    # Temperature bounds
    if not (TEMP_MIN <= temp <= TEMP_MAX):
        violations.append({
            "rule": "temperature_out_of_bounds",
            "severity": "critical",
            "confidence": 1.0,
            "suspect_sensor": "temperature",
            "reason": f"Temperature {temp:.1f}°C is outside realistic physical limits [{TEMP_MIN}, {TEMP_MAX}]°C."
        })

    # Pressure bounds
    if not (PRESSURE_MIN <= pressure <= PRESSURE_MAX):
        violations.append({
            "rule": "pressure_out_of_bounds",
            "severity": "critical",
            "confidence": 1.0,
            "suspect_sensor": "pressure",
            "reason": f"Pressure {pressure:.1f} hPa is outside realistic physical limits [{PRESSURE_MIN}, {PRESSURE_MAX}] hPa."
        })

    # Humidity bounds
    if not (HUMIDITY_MIN <= humidity <= HUMIDITY_MAX):
        violations.append({
            "rule": "humidity_out_of_bounds",
            "severity": "critical",
            "confidence": 1.0,
            "suspect_sensor": "humidity",
            "reason": f"Relative Humidity {humidity:.1f}% is outside physically valid bounds [0, 100]%."
        })

    return violations
