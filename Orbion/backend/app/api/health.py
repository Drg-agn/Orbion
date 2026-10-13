"""
Health & System Metrics API Endpoints.
"""
from fastapi import APIRouter
from app.database import get_metrics_summary, get_db_connection

router = APIRouter(tags=["Health & Metrics"])


@router.get("/health")
def health_check():
    """Liveness probe: verifies backend and SQLite connection health."""
    db_ok = False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        db_ok = cursor.fetchone()[0] == 1
        conn.close()
    except Exception as e:
        return {"status": "degraded", "database": "error", "detail": str(e)}

    return {
        "status": "healthy",
        "database": "connected" if db_ok else "unreachable",
        "service": "SkyGuard AI (Orbion) Meteorological Quality Assurance"
    }


@router.get("/metrics")
def get_dashboard_metrics():
    """Fetches high-level metrics for dashboard KPI cards."""
    return get_metrics_summary()
