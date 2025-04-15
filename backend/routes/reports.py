from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import io
import requests
from typing import List, Optional, Dict
from uuid import UUID
from backend.config import settings
from backend.models.user import User
from backend.models.report import ReportResponse
from backend.auth.dependencies import get_current_user
from backend.database import supabase
from pydantic import BaseModel
import logging

router = APIRouter(prefix="/reports", tags=["reports"])

logger = logging.getLogger(__name__)

# Create a new response model for the paginated reports
class PaginatedReportsResponse(BaseModel):
    reports: List[ReportResponse]
    total: int

@router.get("/", response_model=PaginatedReportsResponse)
async def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    List all reports for the current user with pagination.
    """
    try:
        query = supabase.table("reports").select("*").eq("user_id", str(current_user.id))
        
        # Apply status filter if provided
        if status:
            query = query.eq("status", status)
        
        # Get total count first
        count_query = supabase.table("reports").select("*", count="exact").eq("user_id", str(current_user.id))
        if status:
            count_query = count_query.eq("status", status)
        count_response = count_query.execute()
        total_count = count_response.count if hasattr(count_response, 'count') else 0
        
        # Apply pagination
        query = query.order("created_at", desc=True).range(skip, skip + limit - 1)
        
        # Execute query
        response = query.execute()
        
        reports = [ReportResponse(**report) for report in response.data] if response.data else []
        
        # Add debug logging to help diagnose issues
        print(f"Reports query: User ID: {current_user.id}, Status filter: {status}")
        print(f"Found {total_count} reports, returning {len(reports)}")
        
        # Return in the format expected by the frontend
        return {"reports": reports, "total": total_count}
    except Exception as e:
        print(f"Error fetching reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch reports: {str(e)}")


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific report.
    """
    response = supabase.table("reports").select("*").eq("id", str(report_id)).eq("user_id", str(current_user.id)).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return ReportResponse(**response.data[0])


@router.get("/{report_id}/download")
async def download_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Download a specific report.
    """
    logger.info(f"Download request received for report_id: {report_id}, user: {current_user.id}")
    
    # Get report data
    response = supabase.table("reports").select("*").eq("id", str(report_id)).eq("user_id", str(current_user.id)).execute()
    logger.info(f"Database response: {response}")
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = response.data[0]
    
    if report["status"] not in ["processed", "completed"]:
        raise HTTPException(status_code=400, detail=f"Report is not ready for download (status: {report['status']})")
    
    # Get report from storage
    try:
        # If using Supabase Storage
        storage_response = supabase.storage.from_(settings.STORAGE_BUCKET).download(report["report_url"])
        
        return StreamingResponse(
            io.BytesIO(storage_response),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={report['file_name']}_report.docx"}
        )
    except Exception as e:
        # If report_url is a complete URL
        try:
            response = requests.get(report["report_url"])
            response.raise_for_status()
            
            return StreamingResponse(
                io.BytesIO(response.content),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f"attachment; filename={report['file_name']}_report.docx"}
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to download report: {str(e)}")


@router.delete("/{report_id}")
async def delete_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific report.
    """
    # Check if report exists and belongs to user
    response = supabase.table("reports").select("*").eq("id", str(report_id)).eq("user_id", str(current_user.id)).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = response.data[0]
    
    # Delete from storage if it exists
    if report["status"] == "processed" and report["report_url"]:
        try:
            # Extract file path from URL if it's a full URL
            file_path = report["report_url"].split("/")[-1] if "/" in report["report_url"] else report["report_url"]
            supabase.storage.from_(settings.STORAGE_BUCKET).remove([file_path])
        except Exception:
            # Continue even if storage deletion fails
            pass
    
    # Delete record from database
    supabase.table("reports").delete().eq("id", str(report_id)).execute()
    
    return {"status": "success", "message": "Report deleted successfully"}