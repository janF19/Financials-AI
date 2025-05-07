import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add explicit import for PyJWT to ensure it's available for Supabase
import jwt as pyjwt

from backend.database import supabase
from backend.config.settings import settings
from backend.models.report import ReportCreate
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()


def save_report(user_id: str, report_path: Path, original_file_name: str, report_id: str = None, is_v2: bool = False) -> str:
    """
    Save a report to storage and create a database record.
    
    Args:
        user_id: The ID of the user who owns the report
        report_path: The path to the report file
        original_file_name: The original filename of the report
        report_id: Optional existing report ID to update instead of creating new
        is_v2: Boolean indicating if this is a V2 report (for potential differentiation)
    
    Returns:
        The URL to the stored report in Supabase storage
    """
    try:
        # Generate a unique filename with timestamp and user ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_prefix = "v2_" if is_v2 else ""
        report_filename = f"{user_id}_{timestamp}_{version_prefix}{Path(report_path).name}"
        
        # Example: Differentiate storage path for V2 reports if needed
        # storage_folder = f"{user_id}/v2_reports" if is_v2 else f"{user_id}"
        # storage_path = f"{storage_folder}/{report_filename}"
        # For now, keeping the same top-level user folder:
        storage_path = f"{user_id}/{report_filename}"
        
        logger.info(f"Attempting to save report. User: {user_id}, Path: {report_path}, Original: {original_file_name}, ReportID: {report_id}, IsV2: {is_v2}")
        
        # Upload to Supabase Storage
        with open(report_path, "rb") as file:
                response = supabase.storage.from_(settings.STORAGE_BUCKET).upload(storage_path, file)
                logger.info(f"Uploaded report to Supabase Storage: {response}. Path: {storage_path}")
        
        # Get public URL
        report_url = supabase.storage.from_(settings.STORAGE_BUCKET).get_public_url(storage_path)
        logger.info(f"Report public URL: {report_url}")
        
        # If we have an existing report ID, just update it instead of creating a new record
        if report_id:
            update_data = {
                "report_url": report_url,
                "status": "processed",
                # Optionally, update a version field in the DB if you add one
                # "report_version": "2.0" if is_v2 else "1.0" 
            }
            supabase.table("reports").update(update_data).eq("id", report_id).execute()
            logger.info(f"Updated existing report record: {report_id}")
        else:
            # Create record in reports table
            report_data_dict = {
                "user_id": user_id,
                "file_name": original_file_name, # This is the original uploaded PDF/doc name
                "report_url": report_url,
                "original_file_path": original_file_name, # Consider if this should be the path of the input file to the workflow
                "status": "processed",
                # Optionally, add a version field
                # "report_version": "2.0" if is_v2 else "1.0"
            }
            
            # Convert UUID to string for Supabase if user_id is UUID
            if isinstance(report_data_dict["user_id"], uuid.UUID):
                report_data_dict["user_id"] = str(report_data_dict["user_id"])
            
            # Use ReportCreate model if you want validation, then dump to dict
            # For simplicity here, constructing dict directly
            # report_model_data = ReportCreate(**report_data_dict)
            # supabase.table("reports").insert(report_model_data.model_dump()).execute()
            
            supabase.table("reports").insert(report_data_dict).execute()
            logger.info(f"Created database record for report: {report_url}")
            
        return report_url
    except Exception as e:
        logger.error(f"Failed to save report to Supabase : {str(e)}")
        raise


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