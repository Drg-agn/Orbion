"""
Machine Learning Model Interface.

Loads whatever trained models exist in backend/models/ and scores each sliding window.
Train them with the scripts in /ml (see ml/README.md). Files it looks for:

  isolation_forest.pkl         sklearn Pipeline (StandardScaler -> IsolationForest)
  isolation_forest_meta.json   calibrated threshold + feature version
  lstm_autoencoder.onnx        LSTM autoencoder exported to ONNX
  lstm_autoencoder_meta.json   channel scales + calibrated threshold
  fault_classifier.pkl         gradient-boosting fault classifier (none/spike/stuck/drift/bias/noise)
  fault_classifier_meta.json   class list + calibrated threshold

Scores from each model are put on one common scale:
  0.0 = typical of clean training data, 0.5 = exactly at the alarm threshold, 1.0 = far beyond.
If no models are present, a rolling Z-score fallback keeps the backend running.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import numpy as np

from app.ml.features import (
    FEATURE_VERSION, WINDOW, MIN_WINDOW, window_features, window_sequence,
)


def _to_unit(raw: float, center: float, threshold: float) -> float:
    """Map a raw anomaly score so center -> 0, threshold -> 0.5, 2x past threshold -> 1."""
    span = max(threshold - center, 1e-9)
    return float(np.clip(0.5 * (raw - center) / span, 0.0, 1.0))


class MLModelInterface:
    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = model_dir or (Path(__file__).resolve().parent.parent.parent / "models")
        self.isolation_forest = None
        self.if_meta: Dict[str, Any] = {}
        self.ae_session = None
        self.ae_meta: Dict[str, Any] = {}
        self.classifier = None
        self.clf_meta: Dict[str, Any] = {}
        self.models_loaded = False
        self.load_models()

    # ------------------------------------------------------------------ loading
    def _read_meta(self, name: str) -> Dict[str, Any]:
        path = self.model_dir / name
        return json.loads(path.read_text()) if path.exists() else {}

    def load_models(self) -> None:
        if_path = self.model_dir / "isolation_forest.pkl"
        if if_path.exists():
            meta = self._read_meta("isolation_forest_meta.json")
            if meta.get("feature_version") != FEATURE_VERSION:
                print(f"[ML] Skipping {if_path.name}: trained on feature version "
                      f"{meta.get('feature_version')}, backend uses {FEATURE_VERSION}. Retrain it.")
            else:
                try:
                    import joblib
                    self.isolation_forest = joblib.load(if_path)
                    self.if_meta = meta
                    print(f"[ML] Loaded Isolation Forest (threshold {meta['threshold']:.4f})")
                except Exception as e:
                    print(f"[ML] Could not load Isolation Forest: {e}")

        ae_path = self.model_dir / "lstm_autoencoder.onnx"
        if ae_path.exists():
            try:
                import onnxruntime as ort
                self.ae_session = ort.InferenceSession(str(ae_path), providers=["CPUExecutionProvider"])
                self.ae_meta = self._read_meta("lstm_autoencoder_meta.json")
                print(f"[ML] Loaded LSTM Autoencoder (threshold {self.ae_meta['threshold']:.5f})")
            except Exception as e:
                print(f"[ML] Could not load LSTM Autoencoder: {e}")

        clf_path = self.model_dir / "fault_classifier.pkl"
        if clf_path.exists():
            meta = self._read_meta("fault_classifier_meta.json")
            if meta.get("feature_version") == FEATURE_VERSION:
                try:
                    import joblib
                    self.classifier = joblib.load(clf_path)
                    self.clf_meta = meta
                    print(f"[ML] Loaded fault classifier (threshold {meta['threshold']:.3f})")
                except Exception as e:
                    print(f"[ML] Could not load fault classifier: {e}")
            else:
                print(f"[ML] Skipping {clf_path.name}: feature version mismatch. Retrain it.")

        self.models_loaded = any(m is not None for m in (self.isolation_forest, self.ae_session, self.classifier))

    # kept for backwards compatibility with older callers
    def extract_features(self, window_readings: List[Dict[str, float]]) -> np.ndarray:
        return window_features(window_readings)

    # ------------------------------------------------------------------ scoring
    def _score_if(self, window) -> Optional[Dict[str, float]]:
        if self.isolation_forest is None:
            return None
        raw = float(-self.isolation_forest.score_samples(window_features(window))[0])
        return {"raw": raw, "unit": _to_unit(raw, self.if_meta["center"], self.if_meta["threshold"])}

    def _score_ae(self, window) -> Optional[Dict[str, float]]:
        if self.ae_session is None or len(window) < WINDOW:
            return None
        seq = window_sequence(window) / np.array(self.ae_meta["channel_scale"])
        x = seq[None].astype(np.float32)
        recon = self.ae_session.run(None, {self.ae_session.get_inputs()[0].name: x})[0]
        err = float(np.mean((recon - x) ** 2))
        return {"raw": err, "unit": _to_unit(err, self.ae_meta["center"], self.ae_meta["threshold"])}

    def _score_clf(self, window) -> Optional[Dict[str, Any]]:
        if self.classifier is None:
            return None
        proba = self.classifier.predict_proba(window_features(window))[0]
        classes = list(self.classifier.classes_)
        none_idx = classes.index("none")
        p_fault = float(1 - proba[none_idx])
        others = [(p, c) for p, c in zip(proba, classes) if c != "none"]
        best_p, best_c = max(others)
        return {"raw": p_fault, "unit": _to_unit(p_fault, self.clf_meta["center"], self.clf_meta["threshold"]),
                "fault_type": best_c, "fault_type_prob": float(best_p)}

    def predict(self, window_readings: List[Dict[str, float]]) -> Dict[str, Any]:
        if len(window_readings) < MIN_WINDOW:
            return {"anomaly_score": 0.0, "is_anomaly": False,
                    "model_source": "insufficient_window", "reconstruction_error": 0.0}

        if_res = self._score_if(window_readings)
        ae_res = self._score_ae(window_readings)
        clf_res = self._score_clf(window_readings)

        if if_res or ae_res or clf_res:
            parts = {k: v for k, v in (("isolation_forest", if_res), ("lstm_autoencoder", ae_res),
                                       ("fault_classifier", clf_res)) if v}
            score = max(v["unit"] for v in parts.values())
            return {
                "anomaly_score": round(score, 3),
                "is_anomaly": score >= 0.5,
                "model_source": "+".join(parts.keys()),
                "if_score": round(if_res["unit"], 3) if if_res else None,
                "ae_score": round(ae_res["unit"], 3) if ae_res else None,
                "reconstruction_error": round(ae_res["raw"], 5) if ae_res else 0.0,
                "fault_score": round(clf_res["unit"], 3) if clf_res else None,
                # most likely fault TYPE if this turns out to be a fault (spike/stuck/drift/bias/noise)
                "likely_fault_type": clf_res["fault_type"] if clf_res and clf_res["unit"] >= 0.5 else None,
            }

        # ---- statistical fallback (no trained models yet)
        cols = [[r[k] for r in window_readings] for k in ("temp", "pressure", "humidity")]
        max_z = max(abs(c[-1] - np.mean(c)) / (np.std(c) + 1e-5) for c in cols)
        return {
            "anomaly_score": round(float(np.clip((max_z - 1.5) / 3.0, 0.0, 1.0)), 3),
            "is_anomaly": bool(max_z > 3.0),
            "model_source": "statistical_baseline_stub",
            "max_z_score": round(float(max_z), 2),
            "reconstruction_error": 0.0,
        }
