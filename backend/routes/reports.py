from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import io
import requests
from typing import List, Optional
from uuid import UUID
from backend.config import settings
from backend.models.user import User
from backend.models.report import ReportResponse
from backend.auth.dependencies import get_current_user
from backend.database import supabase

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/", response_model=List[ReportResponse])
async def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    List all reports for the current user with pagination.
    """
    query = supabase.table("reports").select("*").eq("user_id", str(current_user.id))
    
    # Apply status filter if provided
    if status:
        query = query.eq("status", status)
    
    # Apply pagination
    query = query.order("created_at", desc=True).range(skip, skip + limit - 1)
    
    # Execute query
    response = query.execute()
    
    if not response.data:
        return []
    
    return [ReportResponse(**report) for report in response.data]


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
    # Get report data
    response = supabase.table("reports").select("*").eq("id", str(report_id)).eq("user_id", str(current_user.id)).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = response.data[0]
    
    if report["status"] != "processed":
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