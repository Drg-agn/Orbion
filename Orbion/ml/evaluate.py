"""
Step 4 - measure everything on the held-out test set (with injected faults).

Compares: old Z-score baseline vs Isolation Forest vs LSTM autoencoder vs the
supervised fault classifier vs all of them combined.
Prints a table and writes ml/reports/metrics.json - these are the numbers for the paper.

Metrics
  ROC-AUC            how well the score separates faulty from clean readings (threshold-free)
  precision/recall   per reading, at the calibrated threshold
  false alarms       share of clean readings flagged
  episode detection  share of fault episodes with at least one alarm, per fault type
  detection delay    median minutes from fault start to first alarm
  natural events     clean readings where >=2 variables jump together (fronts, storms).
                     ML WILL flag many of these - that is expected; the classification
                     layer is what must rescue them. Report this number honestly.

Extra diagnostics added in this version
  combined_ae_clf    max of LSTM autoencoder + classifier only (leaves out Isolation
                     Forest, which drags the plain "combined" score down)
  recall_by_fault    per-reading recall of the classifier for each fault type
  threshold_sweep    classifier precision / recall / false-alarm rate at several thresholds
"""
import json
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score

from common import MODELS, REPORTS, load_split, per_station
from app.ml.features import WINDOW, frame_features, frame_sequences


def unit(raw, meta):
    return np.clip(0.5 * (raw - meta["center"]) / max(meta["threshold"] - meta["center"], 1e-9), 0, 1)


def score_all(df):
    if_model = if_meta = ae = ae_meta = None
    if (MODELS / "isolation_forest.pkl").exists():
        import joblib
        if_model = joblib.load(MODELS / "isolation_forest.pkl")
        if_meta = json.loads((MODELS / "isolation_forest_meta.json").read_text())
    if (MODELS / "lstm_autoencoder.onnx").exists():
        import onnxruntime as ort
        ae = ort.InferenceSession(str(MODELS / "lstm_autoencoder.onnx"), providers=["CPUExecutionProvider"])
        ae_meta = json.loads((MODELS / "lstm_autoencoder_meta.json").read_text())

    clf = clf_meta = None
    if (MODELS / "fault_classifier.pkl").exists():
        import joblib
        clf = joblib.load(MODELS / "fault_classifier.pkl")
        clf_meta = json.loads((MODELS / "fault_classifier_meta.json").read_text())

    parts = []
    for _, g in per_station(df):
        if len(g) < WINDOW:
            continue
        f = frame_features(g)
        keep = f.notna().all(axis=1).to_numpy()
        r = g.loc[keep, ["timestamp", "fault", "fault_var", "episode_id"]].copy()
        recent = (g["fault"] != "none").astype(int).rolling(WINDOW, min_periods=1).max().astype(bool)
        r["recovering"] = (recent & (g["fault"] == "none"))[keep].to_numpy()
        r["d_temp"], r["d_pres"], r["d_hum"] = f.loc[keep, "d_temp"], f.loc[keep, "d_pres"], f.loc[keep, "d_hum"]
        z = f.loc[keep, ["z_temp", "z_pres", "z_hum"]].abs().max(axis=1).to_numpy()
        r["baseline"] = np.clip((z - 1.5) / 3.0, 0, 1)            # same rule as the old fallback
        r["baseline_alarm"] = z > 3.0
        if if_model is not None:
            r["if"] = unit(-if_model.score_samples(f.loc[keep].to_numpy()), if_meta)
        if clf is not None:
            proba = clf.predict_proba(f.loc[keep].to_numpy())
            none_idx = list(clf.classes_).index("none")
            r["clf"] = unit(1 - proba[:, none_idx], clf_meta)
            masked = proba.copy()
            masked[:, none_idx] = -1
            r["clf_type"] = clf.classes_[masked.argmax(axis=1)]
        if ae is not None:
            rows = np.flatnonzero(keep)
            X = (frame_sequences(g, rows) / np.array(ae_meta["channel_scale"])).astype(np.float32)
            err = np.concatenate([((ae.run(None, {"window": X[i:i + 4096]})[0] - X[i:i + 4096]) ** 2).mean(axis=(1, 2))
                                  for i in range(0, len(X), 4096)])
            r["ae"] = unit(err, ae_meta)
        parts.append(r)
    out = pd.concat(parts, ignore_index=True)

    # all available models combined
    models = [m for m in ("if", "ae", "clf") if m in out]
    if models:
        out["combined"] = out[models].max(axis=1)

    # LSTM autoencoder + classifier only (Isolation Forest left out)
    alt = [m for m in ("ae", "clf") if m in out]
    if alt:
        out["combined_ae_clf"] = out[alt].max(axis=1)

    return out


def summarize(r, col, alarm):
    y = (r["fault"] != "none").to_numpy()
    res = {
        "roc_auc": round(float(roc_auc_score(y, r[col])), 4),
        "precision": round(float(precision_score(y, alarm, zero_division=0)), 4),
        "recall": round(float(recall_score(y, alarm)), 4),
        "f1": round(float(f1_score(y, alarm)), 4),
        "false_alarm_rate": round(float(alarm[~y].mean()), 5),
    }
    ep = r[r.episode_id >= 0].assign(alarm=alarm[r.episode_id.to_numpy() >= 0])
    per_type, delays = {}, []
    for kind, g in ep.groupby("fault"):
        hits = g.groupby("episode_id")["alarm"].any()
        per_type[kind] = round(float(hits.mean()), 3)
    for _, g in ep.groupby("episode_id"):
        idx = np.flatnonzero(g["alarm"].to_numpy())
        if len(idx):
            delays.append(idx[0] * 10)
    res["episode_detection"] = per_type
    res["median_delay_min"] = float(np.median(delays)) if delays else None

    clean = r["fault"] == "none"
    moved = ((r.d_temp.abs() >= 2).astype(int) + (r.d_pres.abs() >= 1.5) + (r.d_hum.abs() >= 8)) >= 2
    nat = (clean & moved).to_numpy()
    res["natural_events"] = int(nat.sum())
    res["natural_events_flagged"] = round(float(alarm[nat].mean()), 3) if nat.any() else None
    return res


def recall_by_fault(r, col, threshold=0.5):
    """Per-reading recall of one score column, split by fault type."""
    faulty = r[r["fault"] != "none"]
    return {
        kind: round(float((g[col] >= threshold).mean()), 3)
        for kind, g in faulty.groupby("fault")
    }


def threshold_sweep(r, col, thresholds=(0.15, 0.2, 0.3, 0.4, 0.5)):
    """Precision / recall / false-alarm rate of one score column at several thresholds."""
    y = (r["fault"] != "none").to_numpy()
    out = []
    for t in thresholds:
        a = (r[col] >= t).to_numpy()
        out.append({
            "threshold": t,
            "precision": round(float(precision_score(y, a, zero_division=0)), 3),
            "recall": round(float(recall_score(y, a)), 3),
            "false_alarm_rate": round(float(a[~y].mean()), 4),
        })
    return out


def main():
    r = score_all(load_split("test"))
    r = r[~r["recovering"]].reset_index(drop=True)
    report = {"baseline_zscore": summarize(r, "baseline", r["baseline_alarm"].to_numpy())}
    for col, name in (("if", "isolation_forest"), ("ae", "lstm_autoencoder"),
                      ("clf", "fault_classifier"), ("combined", "combined"),
                      ("combined_ae_clf", "combined_ae_clf")):
        if col in r:
            report[name] = summarize(r, col, (r[col] >= 0.5).to_numpy())

    if "clf" in r:   # which fault type did the classifier name, for faults it caught?
        hit = (r.fault != "none") & (r.clf >= 0.5)
        cm = pd.crosstab(r.loc[hit, "fault"], r.loc[hit, "clf_type"])
        print("Fault type: true (rows) vs predicted (columns), caught faults only\n" + cm.to_string() + "\n")
        report["fault_type_accuracy"] = round(float((r.loc[hit, "fault"] == r.loc[hit, "clf_type"]).mean()), 4)

    rows = []
    for name, m in report.items():
        if not isinstance(m, dict):
            continue
        rows.append({"model": name, **{k: v for k, v in m.items() if k != "episode_detection"},
                     **{f"det_{k}": v for k, v in m["episode_detection"].items()}})
    table = pd.DataFrame(rows).set_index("model").T
    print(table.to_string())

    # ---- extra diagnostics (kept separate so they don't mix into the model table) ----
    extra = {}
    if "clf" in r:
        extra["classifier_recall_by_fault"] = recall_by_fault(r, "clf", 0.5)
        extra["classifier_threshold_sweep"] = threshold_sweep(r, "clf")

        print("\nPer-reading recall by fault type (classifier, threshold 0.5):")
        for kind, val in extra["classifier_recall_by_fault"].items():
            print(f"  {kind:<8} {val}")

        print("\nThreshold sweep (classifier):")
        print(pd.DataFrame(extra["classifier_threshold_sweep"]).to_string(index=False))

    if "ae" in r:
        extra["lstm_recall_by_fault"] = recall_by_fault(r, "ae", 0.5)
        print("\nPer-reading recall by fault type (LSTM autoencoder, threshold 0.5):")
        for kind, val in extra["lstm_recall_by_fault"].items():
            print(f"  {kind:<8} {val}")

    (REPORTS / "metrics.json").write_text(json.dumps({**report, **extra}, indent=2))
    table.to_csv(REPORTS / "metrics_table.csv")
    print(f"\nSaved -> {REPORTS / 'metrics.json'}")


if __name__ == "__main__":
    main()