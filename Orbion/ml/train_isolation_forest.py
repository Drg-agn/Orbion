"""
Step 2 - train the Isolation Forest on CLEAN data only.

It never sees a fault during training; it learns what normal 6-hour windows look
like, and anything that doesn't fit gets a high score. The alarm threshold is
then set on clean validation data so the false-alarm rate is known in advance.

  python ml/train_isolation_forest.py --fpr 0.002
"""
import argparse, json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from common import MODELS, load_split, per_station
from app.ml.features import FEATURE_NAMES, FEATURE_VERSION, frame_features


def build_matrix(df: pd.DataFrame) -> pd.DataFrame:
    feats = [frame_features(g) for _, g in per_station(df)]
    return pd.concat(feats, ignore_index=True).dropna()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fpr", type=float, default=0.002,
                    help="target false-alarm rate on clean validation readings (0.002 = 1 in 500)")
    ap.add_argument("--max-rows", type=int, default=200_000)
    ap.add_argument("--trees", type=int, default=300)
    a = ap.parse_args()

    X = build_matrix(load_split("train"))
    if len(X) > a.max_rows:
        X = X.sample(a.max_rows, random_state=0)
    print(f"Training on {len(X):,} clean windows x {X.shape[1]} features")

    model = Pipeline([
        ("scale", StandardScaler()),
        ("iforest", IsolationForest(n_estimators=a.trees, max_samples=1024,
                                    contamination="auto", random_state=0, n_jobs=-1)),
    ])
    model.fit(X.to_numpy())

    Xv = build_matrix(load_split("val")).to_numpy()
    raw = -model.score_samples(Xv)
    meta = {
        "feature_version": FEATURE_VERSION,
        "features": FEATURE_NAMES,
        "center": float(np.median(raw)),
        "threshold": float(np.quantile(raw, 1 - a.fpr)),
        "target_fpr": a.fpr,
        "n_train": int(len(X)),
    }
    joblib.dump(model, MODELS / "isolation_forest.pkl")
    (MODELS / "isolation_forest_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Saved -> {MODELS / 'isolation_forest.pkl'}  (threshold {meta['threshold']:.4f})")


if __name__ == "__main__":
    main()
