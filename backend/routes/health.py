from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
import time
from datetime import datetime

from backend.database import supabase

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check(request: Request):
    """
    Check if the API is running properly.
    """
    # Basic server health check
    server_health = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": time.time() - request.app.state.start_time if hasattr(request.app.state, "start_time") else None,
    }
    
    # Database connection check
    db_health = {"status": "ok"}
    try:
        # Simple query to test the database connection
        supabase.table("users").select("count", count="exact").limit(1).execute()
    except Exception as e:
        db_health = {
            "status": "error",
            "message": str(e)
        }
    
    return {
        "server": server_health,
        "database": db_health,
    }


@router.get("/ping")
async def ping():
    """
    Simple ping endpoint to check if the API is responsive.
    """
    return {"ping": "pong"}