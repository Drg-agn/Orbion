"""
Synthetic sensor-fault injection with labels.

Real AWS data almost never comes with fault labels, so the standard approach
(used in most AWS quality-control papers) is: take clean real data, insert
known faults, and check whether the system finds them.

Fault types (one sensor at a time - that is what makes them faults, not weather):
  spike  : one reading jumps and comes straight back (electrical glitch)
  stuck  : value frozen for 3-10 hours
  drift  : slow linear creep over 1-5 days (calibration drift)
  bias   : sudden constant offset for 6-24 hours (bad recalibration / connector)
  noise  : reading becomes jittery for 3-12 hours (failing sensor / loose wire)
"""
import numpy as np
import pandas as pd

FAULT_TYPES = ["spike", "stuck", "drift", "bias", "noise"]
VARS = ["temp", "pressure", "humidity"]

# magnitude ranges per variable: (low, high)
SPIKE = {"temp": (5, 15), "pressure": (3, 8), "humidity": (15, 35)}
DRIFT = {"temp": (2, 5), "pressure": (2, 4), "humidity": (8, 15)}
BIAS = {"temp": (2.5, 6), "pressure": (2, 5), "humidity": (8, 20)}
NOISE = {"temp": (0.8, 2.0), "pressure": (0.6, 1.5), "humidity": (3, 8)}


def _length(kind, rng):
    return {"spike": 1, "stuck": rng.integers(18, 61), "drift": rng.integers(144, 721),
            "bias": rng.integers(36, 145), "noise": rng.integers(18, 73)}[kind]


def inject(df: pd.DataFrame, rng: np.random.Generator, gap: int = 400, start_id: int = 0) -> pd.DataFrame:
    """
    Insert non-overlapping fault episodes into ONE station's series (rows in time order).
    Adds columns: fault (type or 'none'), fault_var, episode_id (-1 = clean).
    About one episode per `gap` rows.
    """
    df = df.copy().reset_index(drop=True)
    df["fault"], df["fault_var"], df["episode_id"] = "none", "none", -1
    df["fault_size"], df["ep_pos"] = 0.0, -1   # how far the reading was pushed; step inside the episode
    n, pos, eid = len(df), int(rng.integers(50, gap)), start_id

    while pos < n - 50:
        kind = FAULT_TYPES[rng.integers(len(FAULT_TYPES))]
        var = VARS[rng.integers(len(VARS))]
        length = int(min(_length(kind, rng), n - pos - 1))
        sl = slice(pos, pos + length)
        col = df.columns.get_loc(var)
        sign = rng.choice([-1, 1])
        x = df.iloc[sl, col].to_numpy(float)
        orig = x.copy()

        if kind == "spike":
            x = x + sign * rng.uniform(*SPIKE[var])
        elif kind == "stuck":
            x = np.full(length, df.iat[pos - 1, col])
        elif kind == "drift":
            x = x + sign * np.linspace(0, rng.uniform(*DRIFT[var]), length)
        elif kind == "bias":
            x = x + sign * rng.uniform(*BIAS[var])
        elif kind == "noise":
            x = x + rng.normal(0, rng.uniform(*NOISE[var]), length)

        if var == "humidity":
            x = np.clip(x, 0, 100)
        df.iloc[sl, col] = np.round(x, 2)
        rows = df.index[sl]                      # .loc slices are inclusive, so use explicit rows
        df.loc[rows, "fault"], df.loc[rows, "fault_var"], df.loc[rows, "episode_id"] = kind, var, eid
        df.loc[rows, "fault_size"] = np.abs(np.round(x, 2) - orig)
        df.loc[rows, "ep_pos"] = np.arange(length)
        eid += 1
        pos += length + int(rng.integers(gap // 2, gap * 3 // 2))
    return df
