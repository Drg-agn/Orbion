"""
FastAPI Main Application.
Configures CORS, SQLite initialization on startup, background WebSocket telemetry streamer,
and mounts REST and WebSocket routers.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.api import stations_router, alerts_router, health_router
from app.api.upload import router as upload_router
from app.websocket.stream import router as ws_router, broadcast_stream


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes database tables on startup and launches streaming replay task."""
    print("[Orbion Backend] Initializing SQLite database...")
    init_db()

    # Launch background task for WebSocket telemetry broadcasting
    stream_task = asyncio.create_task(broadcast_stream())
    print("[Orbion Backend] Background telemetry stream task started.")

    yield

    # Teardown
    print("[Orbion Backend] Shutting down...")
    stream_task.cancel()
    try:
        await stream_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="SkyGuard AI (Orbion) API",
    description="Real-Time Anomaly Detection & Sensor Fault vs. Weather Event Classifier for Automatic Weather Stations",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for React + Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API Routers
app.include_router(health_router, prefix="/api")
app.include_router(stations_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(upload_router, prefix="/api")

# Mount WebSocket Router
app.include_router(ws_router)


@app.get("/")
def root():
    return {
        "system": "SkyGuard AI (Orbion)",
        "docs": "/docs",
        "health": "/api/health",
        "websocket": "ws://<host>:<port>/stream"
    }
