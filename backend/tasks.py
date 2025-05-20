import os
import logging
from typing import Optional
from backend.celery_app import celery_app
from backend.services.processors.workflow import ValuationWorkflow # For financials endpoint
from backend.services.processors.workflow2 import ValuationWorkflow2  # For search/valuate endpoint
from backend.database import supabase # Ensure supabase client is accessible

logger = logging.getLogger(__name__)

# Common logic for updating report status
def _update_report_status(report_id: str, status: str, error_message: Optional[str] = None, report_url: Optional[str] = None):
    update_data = {"status": status}
    if error_message:
        update_data["error_message"] = error_message[:250] # Truncate if needed
    if report_url:
        update_data["report_url"] = report_url
    
    try:
        supabase.table("reports").update(update_data).eq("id", report_id).execute()
        logger.info(f"Report {report_id} status updated to {status}.")
    except Exception as db_error:
        logger.error(f"Failed to update report {report_id} status to {status}: {db_error}")


@celery_app.task(name="process_uploaded_financials_pdf")
def process_uploaded_financials_task(file_path: str, user_id: str, report_id: str):
    """
    Celery task to process an uploaded financial PDF using ValuationWorkflow.
    """
    logger.info(f"Celery task process_uploaded_financials_task started for report {report_id}, user {user_id}, file {file_path}")
    workflow_result = None
    try:
        workflow = ValuationWorkflow2()
        workflow_result = workflow.execute(file_path, user_id=user_id, report_id=report_id)

        if workflow_result and workflow_result.get("status") == "success":
            _update_report_status(report_id, "processed", report_url=workflow_result.get("report_url", ""))
            logger.info(f"Successfully processed report {report_id} for user {user_id} via Celery (uploaded PDF).")
        else:
            error_msg = workflow_result.get("error_message", "Unknown processing error") if workflow_result else "Workflow execution failed"
            error_category = workflow_result.get("error_category", "processing_error") if workflow_result else "unknown_error"
            full_error = f"{error_category}: {error_msg}"
            _update_report_status(report_id, "failed", error_message=full_error)
            logger.error(f"Workflow failed for report {report_id} (uploaded PDF). Category: {error_category}, Message: {error_msg}")

        # workflow.execute should handle cleanup of its input file (file_path) on success or handled failure.

    except Exception as e:
        logger.error(f"Critical error in Celery task process_uploaded_financials_task for report {report_id}: {e}", exc_info=True)
        _update_report_status(report_id, "failed", error_message=f"Celery task error: {str(e)}")
        
        # Fallback cleanup if workflow.execute didn't run or crashed before its own cleanup
        # This file_path is the temporary file created by the calling route (e.g., /financials/upload)
        # and should be cleaned up by this task after processing.
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up input temp file {file_path} for report {report_id} (uploaded PDF) after task completion/failure.")
            except OSError as cleanup_error:
                logger.error(f"Failed to clean up input temp file {file_path} for report {report_id} (uploaded PDF): {cleanup_error}")


@celery_app.task(name="process_ico_sourced_valuation")
def process_ico_valuation_task(file_path: str, user_id: str, report_id: str):
    """
    Celery task to process an ICO-sourced financial PDF using ValuationWorkflow2.
    """
    logger.info(f"Celery task process_ico_valuation_task started for report {report_id}, user {user_id}, file {file_path}")
    workflow_result = None
    try:
        workflow = ValuationWorkflow2()
        workflow_result = workflow.execute(file_path, user_id=user_id, report_id=report_id)

        if workflow_result and workflow_result.get("status") == "success":
            _update_report_status(report_id, "processed", report_url=workflow_result.get("report_url", ""))
            logger.info(f"Successfully processed report {report_id} for user {user_id} via Celery (ICO sourced).")
        else:
            error_msg = workflow_result.get("error_message", "Unknown processing error") if workflow_result else "Workflow execution failed"
            error_category = workflow_result.get("error_category", "processing_error") if workflow_result else "unknown_error"
            full_error = f"{error_category}: {error_msg}"
            _update_report_status(report_id, "failed", error_message=full_error)
            logger.error(f"Workflow failed for report {report_id} (ICO sourced). Category: {error_category}, Message: {error_msg}")

        # workflow.execute should handle cleanup of its input file (file_path) on success or handled failure.

    except Exception as e:
        logger.error(f"Critical error in Celery task process_ico_valuation_task for report {report_id}: {e}", exc_info=True)
        _update_report_status(report_id, "failed", error_message=f"Celery task error: {str(e)}")
    finally: # Ensure cleanup happens whether success or failure of workflow
        # This file_path is the temporary file created by the /search/valuate route
        # and should be cleaned up by this task after processing.
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up input temp file {file_path} for report {report_id} (ICO sourced) after task completion/failure.")
            except OSError as cleanup_error:
                logger.error(f"Failed to clean up input temp file {file_path} for report {report_id} (ICO sourced): {cleanup_error}") 