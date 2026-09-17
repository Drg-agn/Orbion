import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.config import DEFAULT_STATIONS, DEFAULT_SAMPLE_CSV


def generate_synthetic_stream(output_file: Path = DEFAULT_SAMPLE_CSV, num_hours: int = 48) -> Path:
    """
    Generates 48 hours of 10-minute readings across 6 weather stations (288 time steps per station = 1728 records).
    Injects realistic test scenarios:
      - Normal baseline with solar diurnal curves
      - Station A01: Isolated electrical temperature spike (+15°C) at step 50
      - Station A03: Frozen sensor (stuck flat for 24 steps = 4 hours) starting step 90
      - Station A04: Slow subtle sensor drift (+0.08°C/step) starting step 140
      - Station A05: Physics dew point violation (RH boosted to 99% while T is high) at step 190
      - All stations (A01-A06): Genuine regional thunderstorm / cold front at step 230
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    base_time = datetime(2026, 4, 1, 0, 0, 0)
    steps = num_hours * 6  # 6 steps per hour (10-min intervals)

    records = []

    # Elevation temperature lapse rate ~ 0.65°C per 100m
    station_offsets = {
        "A01": 0.0,
        "A02": 0.3,
        "A03": 0.1,
        "A04": -0.4,
        "A05": 0.5,
        "A06": 0.2
    }

    for step in range(steps):
        t_curr = base_time + timedelta(minutes=10 * step)
        t_str = t_curr.strftime("%Y-%m-%d %H:%M:%S")

        # Diurnal curve: lowest at 05:00, peak at 14:00
        hour_frac = t_curr.hour + t_curr.minute / 60.0
        diurnal_t = 24.0 + 7.0 * np.sin(2 * np.pi * (hour_frac - 8.0) / 24.0)
        diurnal_p = 1012.0 - 2.0 * np.sin(2 * np.pi * (hour_frac - 9.0) / 12.0)
        diurnal_h = 60.0 - 25.0 * np.sin(2 * np.pi * (hour_frac - 8.0) / 24.0)

        # Genuine regional cold front / thunderstorm outflow at step 230 to 242 (2 hours)
        is_regional_front = 230 <= step <= 242
        front_temp_drop = -6.5 if is_regional_front else 0.0
        front_pres_rise = +4.2 if is_regional_front else 0.0
        front_hum_rise  = +25.0 if is_regional_front else 0.0

        for st in DEFAULT_STATIONS:
            sid = st["id"]
            offset = station_offsets.get(sid, 0.0)

            # Natural microscopic sensor noise
            noise_t = np.random.normal(0, 0.15)
            noise_p = np.random.normal(0, 0.10)
            noise_h = np.random.normal(0, 0.40)

            temp = diurnal_t + offset + noise_t + front_temp_drop
            pres = diurnal_p + noise_p + front_pres_rise
            hum  = np.clip(diurnal_h + noise_h + front_hum_rise, 10.0, 99.0)

            # Injected Anomaly Scenarios:
            # 1. Single spike on A01
            if sid == "A01" and step == 50:
                temp += 16.5  # Sudden spike to > 40°C

            # 2. Frozen sensor on A03 for 24 steps
            if sid == "A03" and 90 <= step <= 114:
                temp = 23.40
                pres = 1011.80

            # 3. Slow upward drift on A04
            if sid == "A04" and step >= 140:
                drift_amount = (step - 140) * 0.08
                temp += drift_amount

            # 4. Dew point violation on A05 at step 190
            if sid == "A05" and step == 190:
                # Inject artificially corrupted high humidity + perturbation
                hum = 105.0  # Out of bounds and triggers dew point
                temp = 28.0

            records.append({
                "timestamp": t_str,
                "station_id": sid,
                "temperature": round(float(temp), 2),
                "humidity": round(float(hum), 2),
                "pressure": round(float(pres), 2)
            })

    df = pd.DataFrame(records)
    # Sort chronologically so replayer feeds all stations time-synchronously
    df = df.sort_values(by=["timestamp", "station_id"]).reset_index(drop=True)
    df.to_csv(output_file, index=False)
    print(f"[Sample Data] Generated {len(df)} multi-station sensor records at {output_file}")
    return output_file


if __name__ == "__main__":
    generate_synthetic_stream()
