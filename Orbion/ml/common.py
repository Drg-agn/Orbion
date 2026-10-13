"""Paths and small helpers shared by the training scripts."""
import sys
from pathlib import Path

ML_DIR = Path(__file__).resolve().parent
ROOT = ML_DIR.parent
BACKEND = ROOT / "backend"
DATA = ML_DIR / "data"
MODELS = BACKEND / "models"          # backend loads models from here
REPORTS = ML_DIR / "reports"
for d in (DATA, MODELS, REPORTS):
    d.mkdir(parents=True, exist_ok=True)

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import pandas as pd  # noqa: E402


def load_split(name: str) -> pd.DataFrame:
    """Load ml/data/<name>.csv.gz produced by prepare_data.py."""
    path = DATA / f"{name}.csv.gz"
    if not path.exists():
        raise SystemExit(f"{path} not found. Run: python ml/prepare_data.py")
    return pd.read_csv(path, parse_dates=["timestamp"])


def per_station(df: pd.DataFrame):
    """Yield (station_id, station_df) in time order, index reset."""
    for sid, g in df.groupby("station_id", sort=True):
        yield sid, g.sort_values("timestamp").reset_index(drop=True)
