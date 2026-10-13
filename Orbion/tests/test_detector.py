"""
Verification unit test for SkyGuard AI Anomaly Detector.
Verifies Dew Point physics violation, rate-of-change, and fault vs event classification.
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import init_db
from app.services.detector import AnomalyDetector


def test_detector_pipeline():
    print("Testing database initialization...")
    init_db()

    detector = AnomalyDetector()

    # 1. Normal readings on Station A01
    res1 = detector.process_reading("A01", "2026-04-01 10:00:00", temp=22.0, humidity=50.0, pressure=1013.2)
    assert res1["physics"]["is_valid"] is True, "Normal reading should be physically valid"
    assert res1["alert"] is None, "Normal reading should not trigger alert"
    print("[PASS] Normal reading test passed.")

    # 2. Dew Point violation (RH=105%, Temp=10°C)
    res2 = detector.process_reading("A01", "2026-04-01 10:10:00", temp=10.0, humidity=105.0, pressure=1013.0)
    assert res2["alert"] is not None, "Physical violation should trigger an alert"
    assert res2["alert"]["classification"] == "sensor_fault", "Physical violation must be SENSOR FAULT"
    print(f"[PASS] Dew Point/Bounds test passed: {res2['alert']['reason']}")

    # 3. Sudden 20°C spike on A02 (while neighbors are normal)
    detector.process_reading("A02", "2026-04-01 10:00:00", temp=22.0, humidity=50.0, pressure=1013.0)
    res3 = detector.process_reading("A02", "2026-04-01 10:10:00", temp=42.0, humidity=50.0, pressure=1013.0)
    assert res3["alert"] is not None
    assert res3["alert"]["classification"] == "sensor_fault"
    print(f"[PASS] Spike test passed: {res3['alert']['reason']}")

    print("\nALL BACKEND ANOMALY DETECTION TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_detector_pipeline()
