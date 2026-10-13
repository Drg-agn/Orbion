"""
WebSocket Telemetry Streaming Service.

Supports two streaming modes:
  1. Default Demo Stream: ws://host/stream (simulated_stations.csv replay)
  2. Uploaded Stream:     ws://host/stream?session_id=<id> (uploaded file replay)

Manages session engines and dispatches real-time telemetry packets to connected clients.
"""
import json
import asyncio
from typing import Dict, Set, Optional
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import numpy as np
from app.services.replay import ReplayEngine
from app.config import UPLOAD_DIR

router = APIRouter()

DEFAULT_SESSION = "__default__"


def to_json_serializable(obj):
    """Recursively converts NumPy booleans, floats, and ints to native Python JSON types."""
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: to_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_json_serializable(v) for v in obj]
    return obj


class SessionManager:
    def __init__(self):
        self.engines: Dict[str, ReplayEngine] = {}
        self.connections: Dict[str, Set[WebSocket]] = {}
        self.tasks: Dict[str, asyncio.Task] = {}

    def get_or_create_engine(self, session_id: str) -> ReplayEngine:
        if session_id not in self.engines:
            if session_id == DEFAULT_SESSION:
                engine = ReplayEngine()
            else:
                csv_path = UPLOAD_DIR / f"{session_id}.csv"
                if not csv_path.exists():
                    raise FileNotFoundError(f"No uploaded session found for ID '{session_id}'")
                engine = ReplayEngine(csv_path=str(csv_path))
            self.engines[session_id] = engine
            self.connections[session_id] = set()
        return self.engines[session_id]

    def ensure_task(self, session_id: str):
        task = self.tasks.get(session_id)
        if task is None or task.done():
            self.tasks[session_id] = asyncio.create_task(self._broadcast_loop(session_id))

    async def _broadcast_loop(self, session_id: str):
        engine = self.engines.get(session_id)
        if not engine:
            return
        try:
            async for packet in engine.stream_generator():
                await self.broadcast(session_id, packet)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[WebSocket Broadcast Loop Error] Session '{session_id}': {e}")

    async def broadcast(self, session_id: str, message: dict):
        conns = self.connections.get(session_id, set())
        if not conns:
            return
        try:
            payload_str = json.dumps(to_json_serializable(message))
        except Exception as e:
            print(f"[WebSocket JSON Serialization Error] {e}")
            return

        dead = []
        for ws in list(conns):
            try:
                await ws.send_text(payload_str)
            except Exception:
                dead.append(ws)
        for d in dead:
            conns.discard(d)

    def add_connection(self, session_id: str, websocket: WebSocket):
        self.connections.setdefault(session_id, set()).add(websocket)

    def remove_connection(self, session_id: str, websocket: WebSocket):
        conns = self.connections.get(session_id)
        if conns:
            conns.discard(websocket)
        # Cleanup uploaded sessions when all clients disconnect
        if session_id != DEFAULT_SESSION and conns is not None and len(conns) == 0:
            task = self.tasks.pop(session_id, None)
            if task and not task.done():
                task.cancel()
            self.engines.pop(session_id, None)
            self.connections.pop(session_id, None)


manager = SessionManager()


async def broadcast_stream():
    """Background startup loop maintaining default demo replay."""
    manager.get_or_create_engine(DEFAULT_SESSION)
    manager.ensure_task(DEFAULT_SESSION)
    while True:
        await asyncio.sleep(3600)


@router.websocket("/stream")
async def websocket_stream_endpoint(websocket: WebSocket, session_id: Optional[str] = None):
    sid = session_id if (session_id and session_id.strip()) else DEFAULT_SESSION

    try:
        engine = manager.get_or_create_engine(sid)
    except Exception as e:
        await websocket.close(code=4404, reason=f"Could not load session '{sid}': {e}")
        return

    await websocket.accept()
    manager.add_connection(sid, websocket)
    manager.ensure_task(sid)

    # Immediately send welcome handshake and latest reading if available
    try:
        await websocket.send_text(json.dumps({
            "type": "control",
            "status": "connected",
            "session_id": sid
        }))
        if engine.last_packet:
            await websocket.send_text(json.dumps(to_json_serializable(engine.last_packet)))
    except Exception:
        pass

    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                msg = json.loads(data_text)
                action = msg.get("action")
                if action == "pause":
                    engine.pause()
                    await websocket.send_json({"type": "control", "status": "paused"})
                elif action == "resume":
                    engine.resume()
                    await websocket.send_json({"type": "control", "status": "resumed"})
                elif action == "reset":
                    engine.reset()
                    await websocket.send_json({"type": "control", "status": "reset"})
                elif action == "speed":
                    speed_val = float(msg.get("value", 0.5))
                    engine.set_speed(speed_val)
                    await websocket.send_json({"type": "control", "status": f"speed set to {speed_val}s"})
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})
    except WebSocketDisconnect:
        manager.remove_connection(sid, websocket)
    except Exception as e:
        print(f"[WebSocket] Connection error on session {sid}: {e}")
        manager.remove_connection(sid, websocket)
