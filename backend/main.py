import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
import time # For startup time

from backend.routes import auth, financials, dashboard, reports, health, search, chat
from backend.config.settings import settings

app = FastAPI(
    title="Financial Valuation System API",
    description="API for processing financial PDFs and generating valuation reports",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
#this handeles specific group of endpoints like all endpoint from auth or financials
app.include_router(auth.router)
app.include_router(financials.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(health.router)
app.include_router(search.router)
app.include_router(chat.router)


Instrumentator().instrument(app).expose(app)

@app.on_event("startup")
async def startup_event():
    """
    Store startup time in app state for uptime calculation.
    This is used by your existing health check in backend/routes/health.py
    """
    app.state.start_time = time.time()
    # Instrument the app after all routes are added, including those from other modules
    # and after startup events if they modify app state used by instrumentator (not typical).
    # Expose metrics at /metrics
    

# Add a simple health endpoint at /health, as requested by the prompt
@app.get("/health", tags=["Main Health Check"])
async def main_health_check():
    """
    Basic health check for the application.
    """
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )