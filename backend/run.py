"""
Uvicorn Server Launcher.
Run with:
  python run.py
or from project root:
  python backend/run.py
"""
import sys
from pathlib import Path
import uvicorn

# Ensure the backend directory is in sys.path so 'app' imports work directly
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import HOST, PORT, DEBUG

if __name__ == "__main__":
    print(f"==================================================")
    print(f"  SkyGuard AI (Orbion) Meteorological Server")
    print(f"  Listening on: http://{HOST}:{PORT}")
    print(f"  API Docs:     http://localhost:{PORT}/docs")
    print(f"  WebSocket:    ws://localhost:{PORT}/stream")
    print(f"==================================================")
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=DEBUG)
