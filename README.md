# SkyGuard AI (Orbion) 🌦️
### Real-Time Anomaly Detection & Sensor Fault vs. Weather Event Classification for Automatic Weather Stations

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React Vite](https://img.shields.io/badge/React-18%20%2B%20Vite-61dafb.svg)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38bdf8.svg)](https://tailwindcss.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite%20(Zero--Setup)-003b57.svg)](https://sqlite.org/)

---

## 🌟 Executive Summary

Automatic Weather Stations (AWS) continuously record surface **air temperature ($T$)**, **barometric pressure ($P$)**, and **relative humidity ($RH$)**. However, sensor malfunctions (electrical spikes, stuck sensors, calibration drift, and physical bounds breaches) corrupt telemetry. Standard threshold algorithms naively flag real meteorological phenomena (thunderstorm cold pools, cold fronts, gravity waves) as faults, throwing away vital climate and hazard-warning data.

**SkyGuard AI (Orbion)** bridges this gap by deploying a multi-tier intelligence pipeline:
1. **Physics Validation Layer**: Enforces the Magnus-Tetens dew point constraint ($T_d \le T$), Earth extreme ranges, and rate-of-change boundaries.
2. **Spatial Mesh Validation Layer**: Evaluates 100km neighbor-station coherence via inverse-distance spatial medians.
3. **Temporal Machine Learning Interface**: Extracts 14 rolling features for Isolation Forest and LSTM Autoencoder anomaly scoring.
4. **Fault vs. Event Classification Engine**: Discerns multi-variable co-movement and spatial consistency to rescue genuine weather events from being mislabeled as sensor errors.

---

## 🏗️ Architecture

```
                  ┌─────────────────────────────────────┐
                  │ Synthetic / Historical Data Stream  │
                  │       (10-Minute AWS Replay)        │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
        ┌────────────────────────────────────────────────────────┐
        │                 Orchestration Pipeline                 │
        │                                                        │
        │   ┌──────────────────┐   ┌─────────────────────────┐   │
        │   │  Physics Engine  │   │  Spatial Mesh Validator │   │
        │   │  • Dew Point     │   │  • Neighbor Median      │   │
        │   │  • Hard Limits   │   │  • Variance Check       │   │
        │   │  • Frozen Sensor │   │  • Isolated vs Regional │   │
        │   └────────┬─────────┘   └────────────┬────────────┘   │
        │            │                          │                │
        │            └────────────┐     ┌───────┘                │
        │                         ▼     ▼                        │
        │             ┌─────────────────────────────┐            │
        │             │  Fault vs Event Classifier  │            │
        │             │    (Paper Algorithm 1)      │            │
        │             └──────────────┬──────────────┘            │
        └────────────────────────────┼───────────────────────────┘
                                     ▼
                      ┌─────────────────────────────┐
                      │    FastAPI + SQLite DB      │
                      │  • REST API: /stations, ... │
                      │  • WebSocket: /stream       │
                      └──────────────┬──────────────┘
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │    React + Vite Dashboard   │
                      │  • Live Recharts Telemetry  │
                      │  • Explainable Alert Feed   │
                      │  • 100km Station Spatial Map│
                      └─────────────────────────────┘
```

---

## ⚡ Quick Start (Windows PowerShell)

### 1. Start Backend (Terminal 1)
```powershell
cd backend
python -m pip install -r requirements.txt
python run.py
```
Backend will be available at:
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **WebSocket Telemetry Stream**: `ws://localhost:8000/stream`

### 2. Start Frontend (Terminal 2)
```powershell
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.
*Note: Vite includes Hot Module Replacement (HMR). You only run `npm run dev` once; changes auto-refresh in real time.*

---

## 🤖 Guide for ML Teammate

Your teammate can drop their trained ML models directly into `backend/models/`:
1. **Isolation Forest**: Save model as `backend/models/isolation_forest.pkl`.
2. **LSTM Autoencoder**: Save model as `backend/models/lstm_autoencoder.pt` (PyTorch) or `lstm_autoencoder.onnx`.

Everything else is pre-wired in `backend/app/ml/model_interface.py`:
- Sliding window feature extraction (14 features: scaled $T, P, RH$, 10-min deltas, 6-hr rolling means & standard deviations, Magnus dew point $T_d$ and $\Delta T_d$).
- Automatic fallback to robust statistical Z-scores until model files are saved.
- **Zero modification needed** to the rest of the backend or frontend!

---

## 🔬 Meteorological Rules Summary

- **Dew Point Rule**: Magnus approximation:
  $$\gamma(T, RH) = \ln\left(\frac{RH}{100}\right) + \frac{17.62 \cdot T}{243.12 + T}$$
  $$T_d = \frac{243.12 \cdot \gamma}{17.62 - \gamma}$$
  In Earth's atmosphere, $T_d > T$ is physical nonsense. Flagged as **Critical Sensor Fault**.
- **Absolute Range**: Temperature $[-40^\circ\text{C}, 55^\circ\text{C}]$, Pressure $[850, 1100]\text{ hPa}$, Humidity $[0, 100]\%$.
- **Step Limits**: Maximum $3^\circ\text{C}/10\text{min}$, $2\text{ hPa}/10\text{min}$, $15\%/10\text{min}$.
- **Frozen Sensor**: Variance $< 10^{-5}$ across 18 readings (3 hours) signifies stuck/flatlined sensor.
- **Co-movement Weather Event**: Simultaneous step changes across $\ge 2$ variables ($|\Delta T| \ge 2^\circ\text{C}$, $|\Delta P| \ge 1.5\text{ hPa}$) supported by regional neighbor consistency. Rescued as **Genuine Weather Event**.
