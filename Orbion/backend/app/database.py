"""
SQLite Database interface using Python standard library sqlite3.
Handles initialization of stations, readings, alerts, and metrics tables.
"""
import sqlite3
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.config import DATABASE_URL, DEFAULT_STATIONS

DB_PATH = Path(DATABASE_URL)


def get_db_connection() -> sqlite3.Connection:
    """Creates a sqlite3 connection with Row factory for dict-like access."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes database schema and populates default stations if not present."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Stations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            elevation REAL NOT NULL,
            health_score REAL DEFAULT 100.0,
            status TEXT DEFAULT 'healthy', -- 'healthy', 'warning', 'critical', 'offline'
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Readings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            temperature REAL NOT NULL,
            dew_point REAL NOT NULL,
            humidity REAL NOT NULL,
            pressure REAL NOT NULL,
            FOREIGN KEY (station_id) REFERENCES stations(id)
        );
    """)

    # 3. Alerts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            classification TEXT NOT NULL, -- 'sensor_fault', 'weather_event'
            severity TEXT NOT NULL,        -- 'critical', 'warning', 'info'
            confidence REAL NOT NULL,
            suspect_sensor TEXT,           -- 'temperature', 'humidity', 'pressure', 'all'
            reason TEXT NOT NULL,
            rule_triggered TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (station_id) REFERENCES stations(id)
        );
    """)

    # 4. Metrics table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            total_readings INTEGER DEFAULT 0,
            total_faults INTEGER DEFAULT 0,
            total_events INTEGER DEFAULT 0,
            avg_health_score REAL DEFAULT 100.0
        );
    """)

    # Create index for query performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_station ON readings(station_id, timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_station ON alerts(station_id, timestamp);")

    # Insert default stations if not present
    cursor.execute("SELECT COUNT(*) FROM stations;")
    count = cursor.fetchone()[0]
    if count == 0:
        for st in DEFAULT_STATIONS:
            cursor.execute("""
                INSERT INTO stations (id, name, latitude, longitude, elevation, health_score, status)
                VALUES (?, ?, ?, ?, ?, 100.0, 'healthy')
            """, (st["id"], st["name"], st["lat"], st["lon"], st["elevation"]))

    conn.commit()
    conn.close()


def insert_reading(station_id: str, timestamp: str, temp: float, dew_point: float, humidity: float, pressure: float) -> int:
    """Inserts a single sensor reading."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO readings (station_id, timestamp, temperature, dew_point, humidity, pressure)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (station_id, timestamp, temp, dew_point, humidity, pressure))
    reading_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return reading_id


def insert_alert(station_id: str, timestamp: str, classification: str, severity: str,
                 confidence: float, suspect_sensor: str, reason: str, rule: str) -> int:
    """Inserts an anomaly or event alert."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alerts (station_id, timestamp, classification, severity, confidence, suspect_sensor, reason, rule_triggered)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (station_id, timestamp, classification, severity, confidence, suspect_sensor, reason, rule))
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return alert_id


def update_station_health(station_id: str, health_score: float, status: str) -> None:
    """Updates the live health score and operational status of a station."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE stations
        SET health_score = ?, status = ?, last_seen = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (health_score, status, station_id))
    conn.commit()
    conn.close()


def get_all_stations() -> List[Dict[str, Any]]:
    """Returns list of all stations with current health and status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stations ORDER BY id ASC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_station_by_id(station_id: str) -> Optional[Dict[str, Any]]:
    """Fetches details for a single station."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stations WHERE id = ?", (station_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_recent_alerts(limit: int = 50, station_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches latest alerts, optionally filtered by station."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if station_id:
        cursor.execute("""
            SELECT * FROM alerts
            WHERE station_id = ?
            ORDER BY id DESC LIMIT ?
        """, (station_id, limit))
    else:
        cursor.execute("""
            SELECT * FROM alerts
            ORDER BY id DESC LIMIT ?
        """, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_recent_readings(station_id: str, limit: int = 60) -> List[Dict[str, Any]]:
    """Fetches recent historical readings for time-series charts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM readings
        WHERE station_id = ?
        ORDER BY id DESC LIMIT ?
    """, (station_id, limit))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return list(reversed(rows))


def get_metrics_summary() -> Dict[str, Any]:
    """Computes aggregated dashboard metrics."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*), AVG(health_score) FROM stations")
    total_stations, avg_health = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM stations WHERE health_score >= 80")
    healthy_stations = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alerts WHERE is_active = 1")
    active_alerts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alerts WHERE classification = 'sensor_fault'")
    total_faults = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alerts WHERE classification = 'weather_event'")
    total_events = cursor.fetchone()[0]

    conn.close()
    return {
        "total_stations": total_stations or 0,
        "healthy_stations": healthy_stations or 0,
        "avg_health_score": round(avg_health or 100.0, 1),
        "active_alerts": active_alerts or 0,
        "total_faults": total_faults or 0,
        "total_events": total_events or 0,
    }
