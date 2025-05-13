import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import json

# Add explicit import for PyJWT to ensure it's available for Supabase
import jwt as pyjwt

from backend.database import supabase
from backend.config.settings import settings
from backend.models.report import ReportCreate
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()


def save_report(user_id: str, temp_report_path: Path, original_filename: str, report_id: str, is_v2: bool = False, is_v3: bool = False):
    """
    Saves the generated report DOCX file to Supabase storage.

    Args:
        user_id: The ID of the user.
        temp_report_path: The local Path object of the generated DOCX file.
        original_filename: The original name of the uploaded source file (e.g., PDF).
        report_id: The unique ID for this report.
        is_v2: Flag indicating if this is a V2 workflow report.
        is_v3: Flag indicating if this is a V3 workflow report.

    Returns:
        The public URL of the uploaded report.

    Raises:
        Exception: If the upload fails.
    """
    try:
        # Determine storage path based on flags
        if is_v3:
            storage_folder = "reports_v3"
            report_filename = f"report_v3_{report_id}.docx"
            logger.info(f"Using V3 storage path: {storage_folder}")
        elif is_v2:
            storage_folder = "reports_v2"
            report_filename = f"report_v2_{report_id}.docx"
            logger.info(f"Using V2 storage path: {storage_folder}")
        else:
            # Default or V1 path
            storage_folder = "reports"
            report_filename = f"report_{report_id}.docx"
            logger.info(f"Using default/V1 storage path: {storage_folder}")

        storage_path = f"{user_id}/{storage_folder}/{report_filename}"
        metadata_path = f"{user_id}/{storage_folder}/metadata_{report_id}.json" # Example metadata path

        # Example: Uploading the file
        with open(temp_report_path, 'rb') as f:
            # Use upsert=True to overwrite if it somehow exists
            supabase.storage.from_(settings.SUPABASE_REPORTS_BUCKET).upload(
                path=storage_path,
                file=f,
                file_options={"content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "upsert": "true"}
            )
        logger.info(f"Successfully uploaded report to: {storage_path}")

        # Optionally save metadata (like original filename, version)
        metadata = {
            "original_filename": original_filename,
            "report_id": report_id,
            "user_id": user_id,
            "storage_path": storage_path,
            "workflow_version": "3.0" if is_v3 else ("2.0" if is_v2 else "1.0"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        try:
             # Convert metadata dict to bytes for upload
             metadata_bytes = json.dumps(metadata, indent=2).encode('utf-8')
             supabase.storage.from_(settings.SUPABASE_REPORTS_BUCKET).upload(
                 path=metadata_path,
                 file=metadata_bytes,
                 file_options={"content-type": "application/json", "upsert": "true"}
             )
             logger.info(f"Successfully uploaded metadata to: {metadata_path}")
        except Exception as meta_err:
             logger.warning(f"Failed to upload metadata file {metadata_path}: {meta_err}")


        # Get public URL
        res = supabase.storage.from_(settings.SUPABASE_REPORTS_BUCKET).get_public_url(storage_path)
        public_url = res # Adjust based on actual return value if needed

        logger.info(f"Report public URL: {public_url}")
        return public_url

    except Exception as e:
        logger.error(f"Failed to upload report {storage_path} to Supabase Storage: {e}", exc_info=True)
        raise Exception(f"Supabase Storage upload failed: {str(e)}") from e


def get_report(report_id: str, user_id: Optional[str] = None) -> dict:
    """
    Get report details from the database.
    
    Args:
        report_id: The ID of the report
        user_id: The ID of the user (for authorization)
    
    Returns:
        Report details as a dictionary
    """
    query = supabase.table("reports").select("*").eq("id", report_id)
    
    if user_id:
        query = query.eq("user_id", user_id)
        
    response = query.execute()
    
    if not response.data:
        return None
        
    return response.data[0]


def delete_report(report_id: str, user_id: Optional[str] = None) -> bool:
    """
    Delete a report from storage and database.
    
    Args:
        report_id: The ID of the report to delete
        user_id: The ID of the user (for authorization)
    
    Returns:
        Boolean indicating success or failure
    """
    # Get report details first
    report = get_report(report_id, user_id)
    if not report:
        return False
    
    try:
        # Extract the storage path from the URL
        file_url = report["report_url"]
        # The path in storage is typically after the bucket name in the URL
        storage_path = file_url.split(f"{settings.STORAGE_BUCKET}/")[1]
        
        # Delete from storage
        supabase.storage.from_(settings.STORAGE_BUCKET).remove([storage_path])
        
        # Delete from database
        query = supabase.table("reports").delete().eq("id", report_id)
        if user_id:
            query = query.eq("user_id", user_id)
        
        query.execute()
        return True
    except Exception as e:
        print(f"Error deleting report: {e}")
        return False


def cleanup_temp_file(file_path: Path):
    """Remove a temporary file after processing."""
    try:
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning up temporary file {file_path}: {str(e)}")