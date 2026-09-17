"""
Application Configuration and Constants for SkyGuard AI (Orbion).
Includes meteorological bounds, tolerances, and database paths.
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

# Database & Data Paths
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = DATA_DIR / "raw"
UPLOAD_DIR = DATA_DIR / "uploads"

# Ensure runtime directories exist
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DB_PATH = PROCESSED_DIR / "orbion.db"
DEFAULT_SAMPLE_CSV = PROCESSED_DIR / "simulated_stations.csv"

DATABASE_URL = os.getenv("DATABASE_PATH", str(DEFAULT_DB_PATH))
SAMPLE_CSV_PATH = os.getenv("REPLAY_FILE", str(DEFAULT_SAMPLE_CSV))

# Server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1")

# WebSocket Replay Configuration
REPLAY_INTERVAL_SECONDS = float(os.getenv("REPLAY_SPEED_SECONDS", "0.6"))

# =====================================================================
# METEOROLOGICAL PHYSICAL LIMITS & RULES CONFIGURATION
# =====================================================================
# Physical Bounds (Earth Extremes & Station Operational Range)
TEMP_MIN = -40.0       # °C
TEMP_MAX = 55.0        # °C
PRESSURE_MIN = 850.0   # hPa (approx high altitude / extreme low)
PRESSURE_MAX = 1100.0  # hPa (extreme high pressure)
HUMIDITY_MIN = 0.0     # %
HUMIDITY_MAX = 100.0   # %

# Dew Point Tolerance
# In nature, Dew Point (Td) can never exceed Air Temperature (T).
# Tolerance allows 0.5°C margin for sensor calibration / calculation rounding.
DEW_POINT_TOLERANCE = 0.5  # °C

# Maximum Rate of Change (Step Checks: 10-min & 1-hour limits)
MAX_TEMP_CHANGE_PER_10MIN = 3.0    # °C
MAX_TEMP_CHANGE_PER_HOUR = 6.0     # °C
MAX_PRESSURE_CHANGE_PER_10MIN = 2.0  # hPa
MAX_PRESSURE_CHANGE_PER_HOUR = 4.0   # hPa
MAX_HUMIDITY_CHANGE_PER_10MIN = 15.0 # %

# Stuck / Frozen Sensor Checks
# If variance is below epsilon over window_size readings, sensor is considered frozen.
FROZEN_WINDOW_SIZE = 18    # 18 readings of 10 min = 3 hours
FROZEN_VARIANCE_EPS = 1e-5

# Spatial Neighbor Consistency
# If a station deviates from median of nearby stations by more than threshold
SPATIAL_TEMP_DEV_THRESHOLD = 5.0      # °C
SPATIAL_PRESSURE_DEV_THRESHOLD = 4.0  # hPa
SPATIAL_HUMIDITY_DEV_THRESHOLD = 20.0 # %
SPATIAL_Z_THRESHOLD = 3.5

# Station Metadata (Cluster of 6 stations for spatial coherence)
DEFAULT_STATIONS = [
    {"id": "A01", "name": "Station North Ridge", "lat": 28.6448, "lon": 77.2167, "elevation": 216.0},
    {"id": "A02", "name": "Station East Valley",  "lat": 28.6139, "lon": 77.2090, "elevation": 211.0},
    {"id": "A03", "name": "Station Central Basin", "lat": 28.6280, "lon": 77.2280, "elevation": 214.0},
    {"id": "A04", "name": "Station West Foothills","lat": 28.6510, "lon": 77.1900, "elevation": 225.0},
    {"id": "A05", "name": "Station South Plain",  "lat": 28.5800, "lon": 77.2300, "elevation": 208.0},
    {"id": "A06", "name": "Station Lakeview",     "lat": 28.6700, "lon": 77.2400, "elevation": 210.0},
]
