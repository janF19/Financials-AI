import os
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from backend.models.user import User
from backend.models.report import ReportCreate
from backend.auth.dependencies import get_current_user
from backend.database import supabase
from backend.config.settings import settings
from backend.utils.usage_limiter import check_and_increment_api_usage
from backend.tasks import process_uploaded_financials_task

router = APIRouter(prefix="/financials", tags=["financials"])

logger = logging.getLogger(__name__)


@router.post("/process")
async def process_financials(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Process a PDF file and generate a financial report.
    Checks user's monthly API call limit before processing.
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted"
        )
    
    # --- BEGIN RATE LIMIT CHECK ---
    try:
        check_and_increment_api_usage(current_user.id)
        # If the above function returns, the user is within limits and count is incremented.
        # If limit is exceeded, it raises HTTPException 429.
    except HTTPException as http_exc:
        # Re-raise the exception (could be 429 or 500 from the helper)
        raise http_exc
    # --- END RATE LIMIT CHECK ---
    
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
        
        # Process the file in the background ONLY if limit check passed and DB record created
        process_uploaded_financials_task.delay(
            str(temp_file_path),
            str(current_user.id),
            report_id
        )
        logger.info(f"Celery task process_uploaded_financials_task queued for report {report_id}")
        
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "processing",
                "report_id": report_id,
                "message": "Your file is being processed. Check the dashboard for updates."
            }
        )
    
    except Exception as e:
        # Clean up the temp file if saving failed or DB insert failed *after* rate limit check
        if temp_file_path.exists():
            try:
                os.remove(temp_file_path)
            except OSError as rm_error:
                logger.error(f"Error removing temp file {temp_file_path} after failure: {rm_error}")
        # Note: We don't need to "refund" the API call count here, as the expensive task didn't run.
        # If the DB insert failed, the report record won't exist.
        logger.error(f"Error during file save or report creation for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to initiate processing: {str(e)}")