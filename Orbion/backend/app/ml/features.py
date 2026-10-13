"""
Shared feature extraction for SkyGuard AI.

ONE source of truth for features, used by:
  * the live backend (window_features / window_sequence, one window at a time)
  * the training scripts in /ml (frame_features / frame_sequences, a whole series at once)

If training and serving compute features differently, the models silently break.
tests/test_features.py checks that both paths give the same numbers.

Why relative features (v2) instead of raw T / P / RH levels:
  Raw levels make the model learn the *climate* of the training station
  (Jena, Germany sits near 990 hPa; Delhi-area stations near 1010 hPa), so a
  perfectly healthy station elsewhere would look "anomalous". Changes,
  deviations from the recent mean, and spread are far more transferable.
"""
from typing import Dict, List, Sequence
import numpy as np
import pandas as pd

FEATURE_VERSION = 2
WINDOW = 36          # 36 x 10 min = 6 hours
SHORT = 18           # 18 x 10 min = 3 hours (same span as the frozen-sensor rule)
MIN_WINDOW = 3
EPS = 1e-6

FEATURE_NAMES = [
    "d_temp", "d_pres", "d_hum", "d_dew",          # 10-minute changes
    "dev_temp", "dev_pres", "dev_hum",             # latest minus 6 h mean
    "std_temp", "std_pres", "std_hum",             # 6 h spread (near 0 = stuck sensor)
    "dew_depression",                              # T - Td (0 means saturated)
    "z_temp", "z_pres", "z_hum",                   # deviation / spread
    "prev_d_temp", "prev_d_pres", "prev_d_hum",    # previous 10-min change (spike = jump then reverse)
    "std3h_temp", "std3h_pres", "std3h_hum",       # 3 h spread (stuck sensors go flat)
]

SEQ_CHANNELS = ["temp", "pressure", "humidity", "dew_point"]

B_CONST = 17.62
C_CONST = 243.12


def dew_point(temp, humidity):
    """Vectorised Magnus dew point, matching app.physics.dew_point.calculate_dew_point."""
    t = np.asarray(temp, dtype=float)
    rh = np.clip(np.asarray(humidity, dtype=float), 0.1, 100.0)
    gamma = np.log(rh / 100.0) + (B_CONST * t) / (C_CONST + t)
    return np.round((C_CONST * gamma) / (B_CONST - gamma), 2)


# ---------------------------------------------------------------- serving side
def window_features(window: List[Dict[str, float]]) -> np.ndarray:
    """Features for the LATEST reading in a window (oldest first). Shape (1, n_features)."""
    t = np.array([r["temp"] for r in window], dtype=float)
    p = np.array([r["pressure"] for r in window], dtype=float)
    h = np.array([r["humidity"] for r in window], dtype=float)
    td = np.array([r.get("dew_point", np.nan) for r in window], dtype=float)
    if np.isnan(td).any():
        td = dew_point(t, h)

    def delta(a):
        return a[-1] - a[-2] if len(a) > 1 else 0.0

    feats = []
    feats += [delta(t), delta(p), delta(h), delta(td)]
    devs = [a[-1] - a.mean() for a in (t, p, h)]
    stds = [a.std() for a in (t, p, h)]
    feats += devs + stds
    feats.append(t[-1] - td[-1])
    feats += [d / (s + EPS) for d, s in zip(devs, stds)]
    feats += [a[-2] - a[-3] if len(a) > 2 else 0.0 for a in (t, p, h)]
    feats += [a[-SHORT:].std() for a in (t, p, h)]
    return np.array(feats, dtype=float).reshape(1, -1)


def window_sequence(window: List[Dict[str, float]]) -> np.ndarray:
    """(36, 4) array for the autoencoder: each channel minus its window mean (unscaled)."""
    arr = np.array([[r["temp"], r["pressure"], r["humidity"],
                     r.get("dew_point", np.nan)] for r in window[-WINDOW:]], dtype=float)
    if np.isnan(arr[:, 3]).any():
        arr[:, 3] = dew_point(arr[:, 0], arr[:, 2])
    return arr - arr.mean(axis=0, keepdims=True)


# ---------------------------------------------------------------- training side
def frame_features(df: pd.DataFrame, min_periods: int = WINDOW) -> pd.DataFrame:
    """
    Same features for every row of ONE station's series.
    df needs columns temp, pressure, humidity (sorted in time, regular 10-min steps).
    Rows without a full window come back as NaN.
    """
    out = pd.DataFrame(index=df.index)
    t, p, h = df["temp"].astype(float), df["pressure"].astype(float), df["humidity"].astype(float)
    td = df["dew_point"] if "dew_point" in df else pd.Series(dew_point(t, h), index=df.index)

    out["d_temp"], out["d_pres"], out["d_hum"], out["d_dew"] = t.diff(), p.diff(), h.diff(), td.diff()
    for name, s in (("temp", t), ("pres", p), ("hum", h)):
        roll = s.rolling(WINDOW, min_periods=min_periods)
        out[f"dev_{name}"] = s - roll.mean()
        out[f"std_{name}"] = roll.std(ddof=0)
    out["dew_depression"] = t - td
    for name in ("temp", "pres", "hum"):
        out[f"z_{name}"] = out[f"dev_{name}"] / (out[f"std_{name}"] + EPS)
    for name, s in (("temp", t), ("pres", p), ("hum", h)):
        out[f"prev_d_{name}"] = s.diff().shift(1)
        out[f"std3h_{name}"] = s.rolling(SHORT, min_periods=1).std(ddof=0)
    return out[FEATURE_NAMES]


def frame_sequences(df: pd.DataFrame, end_rows: Sequence[int]) -> np.ndarray:
    """(n, 36, 4) windows ending at the given integer row positions (each >= 35)."""
    t, h = df["temp"].to_numpy(float), df["humidity"].to_numpy(float)
    td = df["dew_point"].to_numpy(float) if "dew_point" in df else dew_point(t, h)
    arr = np.stack([t, df["pressure"].to_numpy(float), h, td], axis=1)
    idx = np.asarray(end_rows)[:, None] + np.arange(-WINDOW + 1, 1)[None, :]
    seqs = arr[idx]
    return seqs - seqs.mean(axis=1, keepdims=True)
