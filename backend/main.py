import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
import time # For startup time
import logging # Add this import
import sys # Import sys for sys.stdout

from backend.routes import auth, financials, dashboard, reports, health, search, chat, info
from backend.config.settings import settings



# You can also set specific levels for noisy third-party loggers if needed
logging.getLogger("uvicorn.access").setLevel(logging.INFO) # Example: make uvicorn access logs less verbose
logging.getLogger("selenium.webdriver.remote.remote_connection").setLevel(logging.WARNING)
logging.getLogger("webdriver_manager").setLevel(logging.WARNING)

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
app.include_router(info.router)

#Instrumentator().instrument(app).expose(app) # Keep commented out for now

@app.on_event("startup")
async def startup_event():
    """
    Store startup time in app state for uptime calculation.
    """
    app.state.start_time = time.time()
    # The logging.info call below will now use the configuration set by basicConfig
    logging.info("Application startup complete. Uptime clock started.")


@app.get("/health", tags=["Main Health Check"])
async def main_health_check():
    """
    Basic health check for the application.
    """
    logging.info("Main health check endpoint WAS CALLED. This is an application log.") # MODIFIED: Test log
    return {"status": "healthy"}

if __name__ == "__main__":
    # When running directly with uvicorn.run(), the basicConfig above should take effect.
    # Uvicorn also has its own log_config parameter, but basicConfig often suffices for application logs.
    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        #port=settings.API_PORT,
        port=8001,        
        reload=settings.DEBUG,
        # log_level="info", # You can also set uvicorn's log level here
    )