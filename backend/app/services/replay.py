"""
Historical Data Replay Engine.
Simulates real-time telemetry streaming by feeding historical/synthetic records at accelerated speed.
"""
import asyncio
import pandas as pd
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional
from app.config import SAMPLE_CSV_PATH, REPLAY_INTERVAL_SECONDS
from app.services.detector import AnomalyDetector
from data.sample_data import generate_synthetic_stream


class ReplayEngine:
    def __init__(self, csv_path: Optional[str] = None):
        self.csv_path = Path(csv_path or SAMPLE_CSV_PATH)
        self.detector = AnomalyDetector()
        self.speed = REPLAY_INTERVAL_SECONDS
        self.is_running = True
        self.current_index = 0
        self.df: Optional[pd.DataFrame] = None
        self.last_packet: Optional[Dict[str, Any]] = None
        self._load_data()

    def _load_data(self) -> None:
        """Loads data from CSV or generates synthetic data if missing."""
        if not self.csv_path.exists():
            print(f"[Replay Engine] CSV not found at {self.csv_path}. Generating default sample data...")
            generate_synthetic_stream(self.csv_path)

        self.df = pd.read_csv(self.csv_path)
        print(f"[Replay Engine] Loaded {len(self.df)} records from {self.csv_path}")

    def set_speed(self, seconds_per_tick: float) -> None:
        """Adjusts the playback speed (interval in seconds between ticks)."""
        self.speed = max(0.05, min(5.0, seconds_per_tick))

    def pause(self) -> None:
        self.is_running = False

    def resume(self) -> None:
        self.is_running = True

    def reset(self) -> None:
        self.current_index = 0
        self.is_running = True

    async def stream_generator(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Asynchronous generator that yields one processed reading at each tick,
        feeding the AnomalyDetector and outputting real-time payloads.
        """
        if self.df is None or len(self.df) == 0:
            self._load_data()

        total_rows = len(self.df) if self.df is not None else 0

        if total_rows == 0:
            print(f"[Replay Engine] CSV '{self.csv_path}' has 0 rows. Yielding empty state notice.")
            while True:
                yield {
                    "type": "control",
                    "status": "empty_dataset",
                    "message": "Dataset contains 0 records."
                }
                await asyncio.sleep(2.0)

        while True:
            if not self.is_running:
                await asyncio.sleep(0.5)
                continue

            if self.current_index >= total_rows:
                # Loop around for continuous demo streaming
                self.current_index = 0

            row = self.df.iloc[self.current_index]
            self.current_index += 1

            result = self.detector.process_reading(
                station_id=str(row["station_id"]),
                timestamp=str(row["timestamp"]),
                temp=float(row["temperature"]),
                humidity=float(row["humidity"]),
                pressure=float(row["pressure"])
            )

            # Enrich with stream progress metadata
            payload = {
                "type": "telemetry",
                "progress": {
                    "current": self.current_index,
                    "total": total_rows,
                    "percent": round((self.current_index / total_rows) * 100, 1)
                },
                "data": result
            }

            self.last_packet = payload
            yield payload
            await asyncio.sleep(self.speed)
