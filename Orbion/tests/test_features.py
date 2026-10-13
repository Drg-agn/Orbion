"""
Training and the live backend must compute identical features.
If this test fails, trained models will behave differently in production than in evaluation.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.ml.features import WINDOW, frame_features, frame_sequences, window_features, window_sequence, dew_point
from app.physics.dew_point import calculate_dew_point


def _series(n=120, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "temp": 20 + np.cumsum(rng.normal(0, 0.3, n)),
        "pressure": 1010 + np.cumsum(rng.normal(0, 0.1, n)),
        "humidity": np.clip(60 + np.cumsum(rng.normal(0, 1, n)), 5, 100),
    })
    df["dew_point"] = dew_point(df.temp, df.humidity)
    return df


def test_dew_point_matches_physics_engine():
    for t, h in [(25, 60), (-5, 90), (40, 15), (10, 100)]:
        assert abs(float(dew_point(t, h)) - calculate_dew_point(t, h)) < 1e-9


def test_training_and_serving_features_match():
    df = _series()
    batch = frame_features(df).to_numpy()
    records = df.rename(columns={}).to_dict("records")
    for end in range(WINDOW - 1, len(df)):
        live = window_features(records[end - WINDOW + 1:end + 1])[0]
        assert np.allclose(batch[end], live, atol=1e-6), f"row {end} differs"


def test_training_and_serving_sequences_match():
    df = _series()
    rows = np.arange(WINDOW - 1, len(df))
    batch = frame_sequences(df, rows)
    records = df.to_dict("records")
    for i, end in enumerate(rows):
        assert np.allclose(batch[i], window_sequence(records[end - WINDOW + 1:end + 1]), atol=1e-9)
