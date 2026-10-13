"""
Machine Learning Model Interface & Feature Extraction.
This module defines the contract for ML models (Isolation Forest + LSTM Autoencoder).

NOTE FOR ML TEAMMATE:
--------------------
You can train and drop your trained models in the `backend/models/` directory:
  1. `isolation_forest.pkl` (Joblib or Pickle)
  2. `lstm_autoencoder.onnx` or `.pt` (PyTorch)

Simply load them in `load_models()` below. The interface handles feature extraction
and feeds sliding windows of 14 features matching Section III-C of the paper:
  - Scaled T, P, H
  - 10-minute deltas: ΔT, ΔP, ΔH
  - Rolling mean (6h window, w=36)
  - Rolling std  (6h window, w=36)
  - Dew point (Td) and its delta ΔTd

Until trained models are placed here, this class runs a built-in statistical
fallback (Rolling Robust Z-score / MAD) so the entire backend runs without errors!
"""
from typing import Dict, Any, List, Optional
import numpy as np
from pathlib import Path


class MLModelInterface:
    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = model_dir or (Path(__file__).resolve().parent.parent.parent / "models")
        self.isolation_forest = None
        self.lstm_autoencoder = None
        self.models_loaded = False
        self.load_models()

    def load_models(self) -> None:
        """
        Loads saved model weights if present in models directory.
        ML teammate: replace or extend this logic when saving models.
        """
        if_path = self.model_dir / "isolation_forest.pkl"
        ae_path = self.model_dir / "lstm_autoencoder.pt"

        if if_path.exists():
            try:
                import joblib
                self.isolation_forest = joblib.load(if_path)
                print(f"[ML Interface] Loaded Isolation Forest from {if_path}")
            except Exception as e:
                print(f"[ML Interface] Warning loading Isolation Forest: {e}")

        if ae_path.exists():
            try:
                # ML Teammate: import torch / onnxruntime here
                # self.lstm_autoencoder = torch.load(ae_path)
                print(f"[ML Interface] Found LSTM Autoencoder at {ae_path}")
            except Exception as e:
                print(f"[ML Interface] Warning loading LSTM Autoencoder: {e}")

        self.models_loaded = (self.isolation_forest is not None or self.lstm_autoencoder is not None)

    def extract_features(self, window_readings: List[Dict[str, float]]) -> np.ndarray:
        """
        Converts sliding window of readings (up to 36 readings = 6 hours) into 14 features.
        Readings format: [{"temp": float, "humidity": float, "pressure": float, "dew_point": float}, ...]
        """
        if not window_readings:
            return np.zeros((1, 14))

        temps = np.array([r["temp"] for r in window_readings])
        pressures = np.array([r["pressure"] for r in window_readings])
        humidities = np.array([r["humidity"] for r in window_readings])
        dew_points = np.array([r.get("dew_point", r["temp"]) for r in window_readings])

        latest_t = temps[-1]
        latest_p = pressures[-1]
        latest_h = humidities[-1]
        latest_td = dew_points[-1]

        delta_t = latest_t - temps[-2] if len(temps) > 1 else 0.0
        delta_p = latest_p - pressures[-2] if len(pressures) > 1 else 0.0
        delta_h = latest_h - humidities[-2] if len(humidities) > 1 else 0.0
        delta_td = latest_td - dew_points[-2] if len(dew_points) > 1 else 0.0

        mean_t = float(np.mean(temps))
        std_t = float(np.std(temps)) + 1e-6

        mean_p = float(np.mean(pressures))
        std_p = float(np.std(pressures)) + 1e-6

        mean_h = float(np.mean(humidities))
        std_h = float(np.std(humidities)) + 1e-6

        features = np.array([
            latest_t, latest_p, latest_h,
            delta_t, delta_p, delta_h,
            mean_t, std_t,
            mean_p, std_p,
            mean_h, std_h,
            latest_td, delta_td
        ]).reshape(1, -1)

        return features

    def predict(self, window_readings: List[Dict[str, float]]) -> Dict[str, Any]:
        """
        Runs inference on the current sliding window.
        Returns anomaly score in [0, 1] and boolean flag.
        """
        if len(window_readings) < 3:
            return {
                "anomaly_score": 0.0,
                "is_anomaly": False,
                "model_source": "insufficient_window",
                "reconstruction_error": 0.0
            }

        features = self.extract_features(window_readings)

        # 1. If trained models exist, use them
        if self.isolation_forest is not None:
            try:
                # Isolation Forest decision_function: lower means more anomalous
                score_raw = self.isolation_forest.decision_function(features)[0]
                # Normalize approx to [0, 1] where 1 is highest anomaly
                anomaly_score = float(np.clip(0.5 - score_raw, 0.0, 1.0))
                is_anomaly = anomaly_score > 0.33
                return {
                    "anomaly_score": round(anomaly_score, 3),
                    "is_anomaly": is_anomaly,
                    "model_source": "isolation_forest",
                    "reconstruction_error": 0.0
                }
            except Exception as e:
                print(f"[ML Interface] Prediction error on Isolation Forest: {e}")

        # 2. Statistical Robust Fallback (Z-score on 6-hour rolling window)
        temps = [r["temp"] for r in window_readings]
        pressures = [r["pressure"] for r in window_readings]
        humidities = [r["humidity"] for r in window_readings]

        z_t = abs(temps[-1] - np.mean(temps)) / (np.std(temps) + 1e-5)
        z_p = abs(pressures[-1] - np.mean(pressures)) / (np.std(pressures) + 1e-5)
        z_h = abs(humidities[-1] - np.mean(humidities)) / (np.std(humidities) + 1e-5)

        max_z = max(z_t, z_p, z_h)
        # Scaled to [0, 1]
        anomaly_score = float(np.clip((max_z - 1.5) / 3.0, 0.0, 1.0))
        is_anomaly = max_z > 3.0

        return {
            "anomaly_score": round(anomaly_score, 3),
            "is_anomaly": is_anomaly,
            "model_source": "statistical_baseline_stub",
            "max_z_score": round(float(max_z), 2)
        }
