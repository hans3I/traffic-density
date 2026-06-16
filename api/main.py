from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import time

from backend_logs import backend_logs
from session_manager import SessionManager, SessionLimitExceededError

app = FastAPI(
    title="Traffic Light AI Backend",
    description="Backend API for real-time traffic light analysis using YOLOv8",
    version="1.0.0",
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize session manager
session_manager = SessionManager()
backend_logs.add("INFO", "TrafficAPI", "Backend API initialized")

# Request/Response models
class StartRequest(BaseModel):
    lanes: int
    max_green_time: int = 60

class ConfigureRequest(BaseModel):
    session_id: str
    max_green_time: int

class SpeedRequest(BaseModel):
    session_id: str
    speed: int

@app.middleware("http")
async def log_backend_request(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        backend_logs.add(
            "ERROR",
            "TrafficAPI",
            f"{request.method} {request.url.path} failed",
            details={"path": request.url.path, "method": request.method},
            exc=exc,
        )
        raise

    duration_ms = round((time.time() - start_time) * 1000, 1)
    if request.url.path != "/api/v1/logs" and (request.method != "GET" or response.status_code >= 400):
        level = "ERROR" if response.status_code >= 500 else "WARN" if response.status_code >= 400 else "INFO"
        backend_logs.add(
            level,
            "TrafficAPI",
            f"{request.method} {request.url.path} returned {response.status_code}",
            details={
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
    return response

@app.post("/api/v1/start")
async def start_analysis(request: StartRequest):
    """
    Start a new traffic analysis session.
    Downloads N images from BMD45, runs inference, and returns initial state.
    """
    try:
        if request.lanes < 1 or request.lanes > 4:
            raise HTTPException(status_code=400, detail="Lanes must be between 1 and 4")
        if request.max_green_time < 10 or request.max_green_time > 120:
            raise HTTPException(status_code=400, detail="Max green time must be between 10 and 120 seconds")

        backend_logs.add(
            "INFO",
            "TrafficAPI",
            "Starting traffic analysis session",
            details={"lanes": request.lanes, "max_green_time": request.max_green_time},
        )
        session = session_manager.create_session(
            lanes=request.lanes,
            max_green_time=request.max_green_time,
        )
        backend_logs.add(
            "INFO",
            "TrafficAPI",
            f"Traffic analysis session {session.session_id} started",
            details={"session_id": session.session_id, "lanes": request.lanes},
        )
        return session_manager.to_dict(session)
    except HTTPException:
        raise
    except SessionLimitExceededError as e:
        backend_logs.add(
            "WARN",
            "TrafficAPI",
            "Traffic analysis session rejected due to concurrency limit",
            details={"lanes": request.lanes, "max_green_time": request.max_green_time},
            exc=e,
        )
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        backend_logs.add(
            "ERROR",
            "TrafficAPI",
            "Failed to start traffic analysis session",
            details={"lanes": request.lanes, "max_green_time": request.max_green_time},
            exc=e,
        )
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {str(e)}")

@app.get("/api/v1/state/{session_id}")
async def get_state(session_id: str):
    """
    Get current state of a session.
    Returns lane data, densities, and remaining green time.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session_manager.to_dict(session)

@app.post("/api/v1/configure")
async def configure_session(request: ConfigureRequest):
    """
    Update session configuration (e.g., max green time).
    """
    session = session_manager.update_max_green_time(
        session_id=request.session_id,
        max_green_time=request.max_green_time,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session_manager.to_dict(session)

@app.post("/api/v1/speed")
async def update_speed(request: SpeedRequest):
    """
    Update the simulation speed multiplier.
    """
    if request.speed not in [1, 2, 3, 5]:
        raise HTTPException(status_code=400, detail="Speed must be 1, 2, 3, or 5")
    
    session = session_manager.update_speed(
        session_id=request.session_id,
        speed=request.speed,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    backend_logs.add(
        "INFO",
        "TrafficAPI",
        f"Session {request.session_id} speed changed to {request.speed}x",
        details={"session_id": request.session_id, "speed": request.speed},
    )
    return session_manager.to_dict(session)

@app.delete("/api/v1/stop/{session_id}")
async def stop_analysis(session_id: str):
    """Stop and delete a session."""
    session_manager.stop_session(session_id)
    backend_logs.add(
        "INFO",
        "TrafficAPI",
        f"Session {session_id} stopped",
        details={"session_id": session_id},
    )
    return {"message": "Session stopped"}

@app.get("/api/v1/logs")
async def get_logs(
    level: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 200,
    since_hours: Optional[int] = 24,
):
    """Return recent real backend log events captured by the API process."""
    return backend_logs.list(
        level=level,
        source=source,
        search=search,
        limit=limit,
        since_hours=since_hours,
    )

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "Traffic Light AI Backend is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
