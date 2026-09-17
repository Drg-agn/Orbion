"""
Stations API Endpoints.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from app.database import get_all_stations, get_station_by_id, get_recent_readings

router = APIRouter(prefix="/stations", tags=["Stations"])


@router.get("", response_model=List[Dict[str, Any]])
def list_stations():
    """Returns list of all automatic weather stations with live status and health score."""
    return get_all_stations()


@router.get("/{station_id}")
def get_station_detail(
    station_id: str,
    history_limit: int = Query(60, description="Number of recent readings to fetch")
):
    """Returns details for a specific station, along with its recent time-series telemetry."""
    station = get_station_by_id(station_id)
    if not station:
        raise HTTPException(status_code=404, detail=f"Station '{station_id}' not found.")

    readings = get_recent_readings(station_id, limit=history_limit)
    return {
        "station": station,
        "readings": readings
    }
