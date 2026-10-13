"""
Step 2b - supervised fault classifier (gradient boosting).

Trained on the training years WITH injected faults. The "normal" class is real
weather - including real fronts and storms - so the model learns
"what a broken sensor looks like" as opposed to "what unusual weather looks like".
This is the part that directly serves the project goal (fault vs genuine event).

Classes: none, spike, stuck, drift, bias, noise.
fault_prob = 1 - P(none); its alarm threshold is set on clean validation data.

  python ml/train_fault_classifier.py --fpr 0.002
"""
import argparse, json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import classification_report

from common import MODELS, load_split, per_station
from app.ml.features import FEATURE_NAMES, FEATURE_VERSION, frame_features

# Readings a model cannot be expected to call faulty yet (drift that has barely
# started, a stuck sensor that has only been flat for a few readings) are left
# out of training so they don't teach the model to fire on normal-looking data.
MIN_SIZE = {"temp": 0.8, "pressure": 0.8, "humidity": 4.0}
MIN_STUCK_STEPS = 6


def table(df):
    parts = []
    for _, g in per_station(df):
        f = frame_features(g)
        parts.append(pd.concat([f, g[["fault", "fault_var", "fault_size", "ep_pos"]]], axis=1))
    return pd.concat(parts, ignore_index=True).dropna(subset=FEATURE_NAMES)


def trainable(t):
    size_ok = t.fault_size >= t.fault_var.map(MIN_SIZE).fillna(0)
    ambiguous = ((t.fault == "drift") & ~size_ok) | ((t.fault == "stuck") & (t.ep_pos < MIN_STUCK_STEPS))
    return t[~ambiguous]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fpr", type=float, default=0.002)
    ap.add_argument("--normal-rows", type=int, default=150_000, help="cap on normal rows (faults all kept)")
    a = ap.parse_args()

    t = trainable(table(load_split("train_faults")))
    normal, faulty = t[t.fault == "none"], t[t.fault != "none"]
    if len(normal) > a.normal_rows:
        normal = normal.sample(a.normal_rows, random_state=0)
    t = pd.concat([normal, faulty])
    print("Training rows per class:\n" + t.fault.value_counts().to_string())

    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, max_leaf_nodes=31,
                                         class_weight="balanced", random_state=0)
    clf.fit(t[FEATURE_NAMES].to_numpy(), t["fault"].to_numpy())

    none_idx = list(clf.classes_).index("none")
    v = table(load_split("val"))
    p_clean = 1 - clf.predict_proba(v[FEATURE_NAMES].to_numpy())[:, none_idx]
    meta = {
        "feature_version": FEATURE_VERSION,
        "features": FEATURE_NAMES,
        "classes": list(clf.classes_),
        "center": float(np.median(p_clean)),
        "threshold": float(max(np.quantile(p_clean, 1 - a.fpr), 0.5)),
        "target_fpr": a.fpr,
    }
    vf = table(load_split("val_faults"))
    print(classification_report(vf.fault, clf.predict(vf[FEATURE_NAMES].to_numpy()), digits=3, zero_division=0))

    joblib.dump(clf, MODELS / "fault_classifier.pkl")
    (MODELS / "fault_classifier_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Saved -> {MODELS / 'fault_classifier.pkl'}  (threshold {meta['threshold']:.3f})")


if __name__ == "__main__":
    main()
