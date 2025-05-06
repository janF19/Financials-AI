from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from backend.models.user import User
from backend.models.report import ReportSummary, ReportResponse
from backend.auth.dependencies import get_current_user
from backend.database import supabase

router = APIRouter(prefix="/chat", tags=["chat"])


