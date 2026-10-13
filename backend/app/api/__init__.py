"""
REST API Routers Package.
"""
from app.api.stations import router as stations_router
from app.api.alerts import router as alerts_router
from app.api.health import router as health_router

__all__ = ["stations_router", "alerts_router", "health_router"]
