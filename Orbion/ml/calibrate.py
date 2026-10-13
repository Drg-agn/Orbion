"""
Re-set alarm thresholds for YOUR stations without retraining.

Models trained on Jena learn Jena's noise level. A different station (different
sensors, climate, noise) shifts every score, so a threshold set on Jena gives too
many or too few alarms elsewhere. Give this script a stretch of CLEAN data from
the stations you will run on (backend CSV format), and it rewrites each model's
center/threshold so the false-alarm rate there matches --fpr.

  python ml/calibrate.py --csv backend/data/processed/clean_stations.csv --fpr 0.002
"""
import argparse, json
import numpy as np
import pandas as pd

from common import MODELS, per_station
from app.ml.features import WINDOW, frame_features, frame_sequences, dew_point


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--fpr", type=float, default=0.002)
    a = ap.parse_args()

    df = pd.read_csv(a.csv, parse_dates=["timestamp"]).rename(columns={"temperature": "temp"})
    df["dew_point"] = dew_point(df.temp, df.humidity)
    feats, seqs = [], []
    for _, g in per_station(df):
        if len(g) < WINDOW:
            continue
        f = frame_features(g)
        keep = f.notna().all(axis=1).to_numpy()
        feats.append(f[keep].to_numpy())
        seqs.append(frame_sequences(g, np.flatnonzero(keep)))
    X, S = np.concatenate(feats), np.concatenate(seqs)
    print(f"Calibrating on {len(X):,} clean windows")

    def update(name, raw):
        path = MODELS / f"{name}_meta.json"
        meta = json.loads(path.read_text())
        meta.update(center=float(np.median(raw)), threshold=float(np.quantile(raw, 1 - a.fpr)),
                    target_fpr=a.fpr, calibrated_on=a.csv)
        path.write_text(json.dumps(meta, indent=2))
        print(f"  {name}: threshold -> {meta['threshold']:.5f}")

    import joblib
    if (MODELS / "isolation_forest.pkl").exists():
        update("isolation_forest", -joblib.load(MODELS / "isolation_forest.pkl").score_samples(X))
    if (MODELS / "fault_classifier.pkl").exists():
        clf = joblib.load(MODELS / "fault_classifier.pkl")
        update("fault_classifier", 1 - clf.predict_proba(X)[:, list(clf.classes_).index("none")])
    if (MODELS / "lstm_autoencoder.onnx").exists():
        import onnxruntime as ort
        sess = ort.InferenceSession(str(MODELS / "lstm_autoencoder.onnx"), providers=["CPUExecutionProvider"])
        scale = np.array(json.loads((MODELS / "lstm_autoencoder_meta.json").read_text())["channel_scale"])
        Xs = (S / scale).astype(np.float32)
        err = np.concatenate([((sess.run(None, {"window": Xs[i:i + 4096]})[0] - Xs[i:i + 4096]) ** 2).mean(axis=(1, 2))
                              for i in range(0, len(Xs), 4096)])
        update("lstm_autoencoder", err)


if __name__ == "__main__":
    main()
