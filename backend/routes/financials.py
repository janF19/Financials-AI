import os
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from backend.processors.workflow import ValuationWorkflow
from backend.models.user import User
from backend.models.report import ReportCreate
from backend.auth.dependencies import get_current_user
from backend.database import supabase
from backend.config.settings import settings

router = APIRouter(prefix="/financials", tags=["financials"])

logger = logging.getLogger(__name__)


@router.post("/process")
async def process_financials(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Process a PDF file and generate a financial report.
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted"
        )
    
    # Create a unique filename
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_file_path = Path(settings.TEMP_STORAGE_PATH) / unique_filename
    
    try:
        # Save uploaded file temporarily
        temp_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_file_path, "wb") as buffer:
            contents = await file.read()
            buffer.write(contents)
        
        # Create a pending report record
        report_id = str(uuid.uuid4())
        report_data = {
            "id": report_id,
            "user_id": str(current_user.id),
            "file_name": file.filename,
            "report_url": "",  # Will be updated after processing
            "status": "pending",
            "original_file_path": str(temp_file_path)  # Add this to track the file
        }
        supabase.table("reports").insert(report_data).execute()
        
        # Process the file in the background
        #This schedules process_financial_task to run asynchronously after the endpoint returns a response to the user.
        background_tasks.add_task(
            process_financial_task,
            str(temp_file_path),
            str(current_user.id),
            report_id
        )
        
        # return {
        #     "status": "processing",
        #     "report_id": report_id,
        #     "message": "Your file is being processed. You'll be notified when it's ready."
        # }
        
        return JSONResponse(
            status_code=202,  # Accepted
            content={
                "status": "processing",
                "report_id": report_id,
                "message": "Your file is being processed. Check the dashboard for updates."
            }
        )
    
    except Exception as e:
        if temp_file_path.exists():
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=str(e))


def process_financial_task(file_path: str, user_id: str, report_id: str):
    """
    Background task to process financial PDF and update report status.
    """
    try:
        # Execute workflow
        workflow = ValuationWorkflow()
        result = workflow.execute(file_path, user_id=user_id, report_id=report_id)
        
        # Update report record with results
        update_data = {
            "status": "processed",
            "report_url": result["report_url"]
        }
        supabase.table("reports").update(update_data).eq("id", report_id).execute()
        
        # No need to clean up temp file here as workflow.execute already does it
        
    except Exception as e:
        # Update report with error status
        update_data = {
            "status": "failed",
            "error_message": str(e)
        }
        supabase.table("reports").update(update_data).eq("id", report_id).execute()
        
        # Clean up temp file if it still exists
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.error(f"Failed to process file: {str(e)}")