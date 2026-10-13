# SkyGuard AI - ML training

Everything here runs on a laptop CPU. Trained files land in `backend/models/`,
and the backend picks them up on restart.

```bash
pip install -r ml/requirements-train.txt

python ml/prepare_data.py               # 1. download Jena Climate, clean, split, add labelled faults
python ml/train_isolation_forest.py     # 2. unsupervised: learns "normal" from clean data
python ml/train_fault_classifier.py     # 2b. supervised: learns what each fault type looks like
python ml/train_lstm_autoencoder.py     # 3. unsupervised: sequence model, exported to ONNX
python ml/evaluate.py                   # 4. numbers for the report -> ml/reports/metrics.json
python ml/calibrate.py --csv <clean data from your demo stations>   # 5. re-set thresholds for your stations
pytest tests/test_features.py           # training and backend must compute identical features
```

## Data
* **Jena Climate 2009-2016** (Max Planck Institute for Biogeochemistry): one station,
  10-minute T / p / RH / Tdew. Same interval and variables as SkyGuard. Used for training and the main results.
* **Your own data**: `python ml/prepare_data.py --csv file.csv` with columns
  `timestamp,station_id,temperature,humidity,pressure` (multi-station is fine).
  Change `--val-start` / `--test-start` to fit its date range.

## Splits (by time, never shuffled)
| file | years | faults | used for |
|---|---|---|---|
| train.csv.gz | 2009-2013 | none | Isolation Forest, autoencoder |
| train_faults.csv.gz | 2009-2013 | injected | fault classifier |
| val.csv.gz | 2014 | none | alarm thresholds |
| val_faults.csv.gz | 2014 | injected | classifier report |
| test.csv.gz | 2015-2016 | injected | final results only |

## Known limits (say these in the report)
* Fault labels are synthetic (injected). Real faults may look different.
* Jena is one station, so the spatial layer can't be tested on it.
* Slow drift at a single station is hard to separate from real climate change of
  the same size; the spatial layer is what should catch it.
* Thresholds are station-specific: run `calibrate.py` on clean data from the stations you demo.
