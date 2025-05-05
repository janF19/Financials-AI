import os
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from backend.processors.workflow import ValuationWorkflow
from backend.models.user import User
from backend.models.report import ReportCreate
from backend.auth.dependencies import get_current_user
from backend.database import supabase
from backend.config.settings import settings
from backend.utils.usage_limiter import check_and_increment_api_usage

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
        background_tasks.add_task(
            process_financial_task,
            str(temp_file_path),
            str(current_user.id),
            report_id
        )
        
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


def process_financial_task(file_path: str, user_id: str, report_id: str):
    """
    Background task to process financial PDF and update report status.
    """
    workflow_result = None # Initialize
    try:
        # Execute workflow
        workflow = ValuationWorkflow()
        workflow_result = workflow.execute(file_path, user_id=user_id, report_id=report_id) # Store result
        
        # Check workflow status before updating DB
        if workflow_result and workflow_result.get("status") == "success":
            update_data = {
                "status": "processed",
                "report_url": workflow_result.get("report_url", "") # Use get for safety
            }
            supabase.table("reports").update(update_data).eq("id", report_id).execute()
            logger.info(f"Successfully processed report {report_id} for user {user_id}")
        else:
            # Workflow failed, update status and log error
            error_msg = workflow_result.get("error_message", "Unknown processing error") if workflow_result else "Workflow execution failed"
            error_category = workflow_result.get("error_category", "processing_error") if workflow_result else "unknown_error"
            logger.error(f"Workflow failed for report {report_id}, user {user_id}. Category: {error_category}, Message: {error_msg}")
            update_data = {
                "status": "failed",
                "error_message": f"{error_category}: {error_msg}"[:250] # Add error message, truncate if needed
            }
            supabase.table("reports").update(update_data).eq("id", report_id).execute()
        
        # Workflow's execute method should handle cleanup of its own temp files (including original)
        
    except Exception as e:
        # Catch exceptions during the task execution itself (outside workflow.execute)
        # or if workflow.execute raised an unexpected exception not caught internally
        logger.error(f"Critical error in background task for report {report_id}, user {user_id}: {e}", exc_info=True)
        try:
            update_data = {
                "status": "failed",
                "error_message": f"Background task error: {str(e)}"[:250] # Truncate if needed
            }
            supabase.table("reports").update(update_data).eq("id", report_id).execute()
        except Exception as db_error:
            logger.error(f"Failed to update report {report_id} status to failed after task error: {db_error}")
        
        # Attempt cleanup ONLY IF the workflow didn't run or failed early
        # The workflow.execute() is responsible for its own cleanup on success or handled failure.
        # If the exception happened *before* workflow.execute() finished, the file might still exist.
        if file_path and os.path.exists(file_path):
            try:
                # Check if workflow_result exists and indicates success before removing
                # This check is imperfect, relies on workflow cleaning up its input on success
                if not (workflow_result and workflow_result.get("status") == "success"):
                    os.remove(file_path)
                    logger.info(f"Cleaned up temp file {file_path} after task failure for report {report_id}")
            except OSError as cleanup_error:
                logger.error(f"Failed to clean up temp file {file_path} after task failure for report {report_id}: {cleanup_error}")