from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from backend.models.user import User
from backend.models.report import ReportSummary, ReportResponse
from backend.auth.dependencies import get_current_user
from backend.database import supabase

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/", response_model=Dict[str, Any])
async def get_dashboard_data(current_user: User = Depends(get_current_user)):
    """
    Get dashboard data for the current user.
    """
    # Get total reports count
    count_response = supabase.table("reports").select("*", count="exact").eq("user_id", str(current_user.id)).execute()
    total_reports = count_response.count
    
    # Get recent reports (last 5)
    recent_reports_response = supabase.table("reports").select("*").eq("user_id", str(current_user.id)).order("created_at", desc=True).limit(5).execute()
    recent_reports = [ReportResponse(**report) for report in recent_reports_response.data]
    
    # Get reports by status
    processed_count = supabase.table("reports").select("*", count="exact").eq("user_id", str(current_user.id)).eq("status", "processed").execute().count
    pending_count = supabase.table("reports").select("*", count="exact").eq("user_id", str(current_user.id)).eq("status", "pending").execute().count
    failed_count = supabase.table("reports").select("*", count="exact").eq("user_id", str(current_user.id)).eq("status", "failed").execute().count
    
    return {
        "total_reports": total_reports,
        "recent_reports": recent_reports,
        "reports_by_status": {
            "processed": processed_count,
            "pending": pending_count,
            "failed": failed_count
        }
    }


@router.get("/reports-summary", response_model=ReportSummary)
async def get_reports_summary(current_user: User = Depends(get_current_user)):
    """
    Get a summary of reports for the current user.
    """
    # Get total reports count
    count_response = supabase.table("reports").select("*", count="exact").eq("user_id", str(current_user.id)).execute()
    total_reports = count_response.count
    
    # Get recent reports (last 5)
    recent_reports_response = supabase.table("reports").select("*").eq("user_id", str(current_user.id)).order("created_at", desc=True).limit(5).execute()
    recent_reports = [ReportResponse(**report) for report in recent_reports_response.data]
    
    return ReportSummary(
        total_reports=total_reports,
        recent_reports=recent_reports
    )