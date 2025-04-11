
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import auth, financials, dashboard, reports, health
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

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )