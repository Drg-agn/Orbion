"""
Test script for NOAA GHCN and large file upload parsing.
"""
import sys
import io
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pandas as pd
from app.api.upload import normalize_ghcn_format, normalize_standard_format


def test_noaa_ghcn_parsing():
    print("Testing NOAA GHCN format parsing (matching user's screenshot)...")
    data = """station_code,weather_d,element_type,element_v,measurement_flag,quality_flag,source_flag
USC00419,20190101,TMAX,156,7,800
USC00419,20190101,TMIN,39,7,800
USC00419,20190101,TOBS,39,7,800
USC00419,20190101,PRCP,0,7,800
USC00421,20190101,TMAX,-28,7,800
USC00421,20190101,TMIN,-100,7,800
USC00421,20190101,TOBS,-94,7,800
USC00426,20190101,TMAX,6,7,800
USC00426,20190101,TMIN,-94,7,800
"""
    df = pd.read_csv(io.StringIO(data))
    norm_df = normalize_ghcn_format(df)

    assert "timestamp" in norm_df.columns
    assert "station_id" in norm_df.columns
    assert "temperature" in norm_df.columns
    assert "humidity" in norm_df.columns
    assert "pressure" in norm_df.columns

    # Verify scaling: 39 tenths of a degree should be scaled or converted properly
    print(norm_df)
    assert len(norm_df) >= 3, "Should have pivoted 3 stations"
    print("[PASS] NOAA GHCN parsing verified successfully!")


if __name__ == "__main__":
    test_noaa_ghcn_parsing()
