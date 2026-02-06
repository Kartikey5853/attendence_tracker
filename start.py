"""
Quick start script: Runs both backend (FastAPI) and frontend (static file server) together.
"""
import subprocess
import sys
import os
import time
import webbrowser

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

if __name__ == "__main__":
    print("=" * 50)
    print("  ATTENDANCE TRACKER - TKRCET")
    print("=" * 50)
    print()

    # Start backend
    print("[1/2] Starting FastAPI backend on http://localhost:8000 ...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=BACKEND_DIR,
    )

    # Start frontend static server
    print("[2/2] Starting frontend on http://localhost:3000 ...")
    frontend = subprocess.Popen(
        [sys.executable, "-m", "http.server", "3000"],
        cwd=FRONTEND_DIR,
    )

    time.sleep(2)
    print()
    print("✅ Both servers are running!")
    print("   Frontend : http://localhost:3000")
    print("   Backend  : http://localhost:8000")
    print("   API Docs : http://localhost:8000/docs")
    print()
    print("Press Ctrl+C to stop both servers.")

    webbrowser.open("http://localhost:3000")

    try:
        backend.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        backend.terminate()
        frontend.terminate()
