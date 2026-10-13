"""
Step 1 - download, clean, split, and add labelled faults.

Default dataset: Jena Climate (Max Planck Institute for Biogeochemistry),
one station, 10-minute readings 2009-2016, with T, p, rh and Tdew -
the same interval and variables SkyGuard uses.

  python ml/prepare_data.py                    # Jena (downloads ~13 MB)
  python ml/prepare_data.py --csv my.csv       # your own data in backend format:
                                               # timestamp,station_id,temperature,humidity,pressure

Outputs in ml/data/:
  train.csv.gz         clean       -> unsupervised models learn "normal" from this only
  train_faults.csv.gz  with faults -> supervised fault classifier trains on this
  val.csv.gz           clean       -> sets the alarm threshold
  val_faults.csv.gz    with faults -> optional tuning
  test.csv.gz          with faults -> final numbers for the report / paper
"""
import argparse, io, zipfile
import numpy as np
import pandas as pd

from common import DATA
from inject_faults import inject
from app.ml.features import dew_point

JENA_URL = "https://storage.googleapis.com/tensorflow/tf-keras-datasets/jena_climate_2009_2016.csv.zip"
BOUNDS = {"temp": (-40, 55), "pressure": (850, 1100), "humidity": (0, 100)}
MAX_GAP = 6          # fill gaps up to 1 hour by interpolation; longer gaps split the series
MIN_SEGMENT = 144    # drop pieces shorter than 1 day


def load_jena() -> pd.DataFrame:
    raw_path = DATA / "jena_climate_2009_2016.csv"
    if not raw_path.exists():
        import requests
        print("Downloading Jena Climate dataset ...")
        r = requests.get(JENA_URL, timeout=120)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            raw_path.write_bytes(z.read("jena_climate_2009_2016.csv"))
    df = pd.read_csv(raw_path)
    df = df.rename(columns={"Date Time": "timestamp", "T (degC)": "temp",
                            "p (mbar)": "pressure", "rh (%)": "humidity"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%d.%m.%Y %H:%M:%S")
    df["station_id"] = "JENA"
    return df[["timestamp", "station_id", "temp", "pressure", "humidity"]]


def load_backend_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["timestamp"])
    return df.rename(columns={"temperature": "temp"})[["timestamp", "station_id", "temp", "pressure", "humidity"]]


def clean_station(g: pd.DataFrame, sid: str) -> pd.DataFrame:
    g = g.drop_duplicates("timestamp").set_index("timestamp").sort_index()
    for c, (lo, hi) in BOUNDS.items():
        g.loc[(g[c] < lo) | (g[c] > hi), c] = np.nan
    g = g[["temp", "pressure", "humidity"]].resample("10min").mean()
    g = g.interpolate(limit=MAX_GAP, limit_area="inside")
    ok = g.notna().all(axis=1)
    seg = (ok != ok.shift()).cumsum()
    pieces = []
    for k, piece in g[ok].groupby(seg[ok]):
        if len(piece) >= MIN_SEGMENT:
            piece = piece.reset_index()
            piece["station_id"] = f"{sid}_s{k}"   # each unbroken piece is its own series
            pieces.append(piece)
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()


def add_faults(df: pd.DataFrame, seed: int, gap: int = 400) -> pd.DataFrame:
    rng, out, next_id = np.random.default_rng(seed), [], 0
    for sid, g in df.groupby("station_id"):
        g = inject(g.sort_values("timestamp"), rng, gap=gap, start_id=next_id)
        next_id = g["episode_id"].max() + 1 if (g["episode_id"] >= 0).any() else next_id
        out.append(g)
    return pd.concat(out, ignore_index=True)


def finish(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["dew_point"] = dew_point(df["temp"], df["humidity"])  # station computes Td from (possibly faulty) T and RH
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="backend-format CSV instead of Jena")
    ap.add_argument("--val-start", default="2014-01-01")
    ap.add_argument("--test-start", default="2015-01-01")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    raw = load_backend_csv(a.csv) if a.csv else load_jena()
    cleaned = pd.concat([clean_station(g, sid) for sid, g in raw.groupby("station_id")], ignore_index=True)
    print(f"Clean rows: {len(cleaned):,} in {cleaned['station_id'].nunique()} unbroken series")

    ts = cleaned["timestamp"]
    splits = {
        "train": cleaned[ts < a.val_start],
        "val": cleaned[(ts >= a.val_start) & (ts < a.test_start)],
        "test": cleaned[ts >= a.test_start],
    }
    for name, part in splits.items():
        if part.empty:
            raise SystemExit(f"'{name}' split is empty - adjust --val-start / --test-start for your data")

    finish(splits["train"]).assign(fault="none", fault_var="none", episode_id=-1, fault_size=0.0, ep_pos=-1).to_csv(DATA / "train.csv.gz", index=False)
    # denser faults in the training copy = more examples for the classifier
    finish(add_faults(splits["train"], a.seed + 7, gap=150)).to_csv(DATA / "train_faults.csv.gz", index=False)
    finish(splits["val"]).assign(fault="none", fault_var="none", episode_id=-1, fault_size=0.0, ep_pos=-1).to_csv(DATA / "val.csv.gz", index=False)
    finish(add_faults(splits["val"], a.seed)).to_csv(DATA / "val_faults.csv.gz", index=False)
    test = finish(add_faults(splits["test"], a.seed + 1))
    test.to_csv(DATA / "test.csv.gz", index=False)

    n_ep = test.loc[test.episode_id >= 0, "episode_id"].nunique()
    print(f"train {len(splits['train']):,} | val {len(splits['val']):,} | test {len(test):,} rows, {n_ep} fault episodes")
    print(test.loc[test.episode_id >= 0].groupby("fault")["episode_id"].nunique().to_string())


if __name__ == "__main__":
    main()
