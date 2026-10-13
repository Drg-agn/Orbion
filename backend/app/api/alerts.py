"""
Alerts API Endpoints.
"""
from fastapi import APIRouter, Query
from typing import List, Dict, Any, Optional
from app.database import get_recent_alerts, get_db_connection

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=List[Dict[str, Any]])
def list_alerts(
    limit: int = Query(50, ge=1, le=200),
    station_id: Optional[str] = Query(None, description="Filter by station ID"),
    classification: Optional[str] = Query(None, description="'sensor_fault' or 'weather_event'")
):
    """Fetches recent anomaly alerts with optional filtering."""
    alerts = get_recent_alerts(limit=limit, station_id=station_id)
    if classification:
        alerts = [a for a in alerts if a["classification"] == classification]
    return alerts


@router.get("/stats")
def get_alert_statistics():
    """Returns anomaly root-cause breakdown and classification counts."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Breakdown by rule triggered
    cursor.execute("""
        SELECT rule_triggered, COUNT(*) as count
        FROM alerts
        GROUP BY rule_triggered
        ORDER BY count DESC
    """)
    rules_breakdown = [{"rule": row["rule_triggered"], "count": row["count"]} for row in cursor.fetchall()]

    # Breakdown by suspect sensor
    cursor.execute("""
        SELECT suspect_sensor, COUNT(*) as count
        FROM alerts
        WHERE suspect_sensor IS NOT NULL AND suspect_sensor != 'none'
        GROUP BY suspect_sensor
    """)
    sensor_breakdown = [{"sensor": row["suspect_sensor"], "count": row["count"]} for row in cursor.fetchall()]

    # Classification breakdown
    cursor.execute("""
        SELECT classification, COUNT(*) as count
        FROM alerts
        GROUP BY classification
    """)
    classification_breakdown = [{"type": row["classification"], "count": row["count"]} for row in cursor.fetchall()]

    conn.close()
    return {
        "by_rule": rules_breakdown,
        "by_sensor": sensor_breakdown,
        "by_classification": classification_breakdown
    }
