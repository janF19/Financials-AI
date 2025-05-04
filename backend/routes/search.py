from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Dict, Any
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
from backend.searching.scraping_methods import get_companies_from_ico, get_companies_from_name_company, get_companies_from_name_person
import logging
from backend.models.search_models import CompanyInfo, CompanySearchByPersonResponse, CompanySearchByNameResponse
import json
from backend.searching.scraping_scripts.ico_file_scraper import get_latest_financial_document
from fastapi import BackgroundTasks
from fastapi.responses import JSONResponse
from pathlib import Path
import uuid
from pathlib import Path
import os
from backend.processors.workflow import ValuationWorkflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])

@router.get("/person", response_model=CompanySearchByPersonResponse)
async def get_companies_by_person(
    first_name: str = Query(..., description="First name with support for Czech characters (e.g., Bohumír)"),
    last_name: str = Query(..., description="Last name with support for Czech characters (e.g., Čejkovský)"),
    current_user: User = Depends(get_current_user)
):
    """Get list of companies for a given person name.
    
    Returns company information including establishment date, registration details,
    address, and other available data from justice records.
    info like established act. like justice, perhaps 
    in future fetch current info using serp rag atd. AI
    
    Makes scraping call which might take a long time.
    
    Supports Czech special characters (ě, š, č, ř, ž, ý, á, í, etc.) in names.
    """    
    
    logger.info(f"Search endpoint called with {first_name} {last_name}")
    
    try:
        # Get the raw result from the scraper
        raw_result = get_companies_from_name_person(first_name, last_name)
        
        # Log the raw result
        # logger.info(f"Raw result: {raw_result}")
        
        # Debug the entire result structure
        logger.info(f"Raw result structure: {type(raw_result)}")
        
        # Check if the result is a dictionary with the expected structure
        if not isinstance(raw_result, dict):
            logger.error(f"Result is not a dictionary: {raw_result}")
            return CompanySearchByPersonResponse()
            
        # Extract the data field which contains the companies
        if "data" not in raw_result:
            logger.error(f"Result does not contain 'data' field: {raw_result}")
            return CompanySearchByPersonResponse()
            
        companies_data = raw_result["data"]
        count = raw_result.get("count", len(companies_data) if isinstance(companies_data, dict) else 0)
        
        # Create a dictionary of CompanyInfo models
        parsed_companies = {}
        
        if isinstance(companies_data, dict):
            for ico, company_data in companies_data.items():
                try:
                    # Create CompanyInfo model from the company data
                    company_model = CompanyInfo.model_validate(company_data)
                    parsed_companies[ico] = company_model
                except Exception as e:
                    logger.error(f"Error parsing company data for ICO {ico}: {str(e)}")
                    # Skip this company if there's an error
                    continue
        
        # Return the CompanySearchResponse model
        return CompanySearchByPersonResponse(
            companies=parsed_companies,
            count=count
        )
        
    except Exception as e:
        logger.error(f"Error in get_companies_by_person: {str(e)}", exc_info=True)
        return CompanySearchByPersonResponse()
    

@router.get("/company", response_model=CompanySearchByNameResponse)
async def get_companies_by_company_name(
    company_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get list of companies matching a given company name.
    
    Returns company information including establishment date, registration details,
    address, and other available data from justice records.
    
    Makes scraping call which might take a long time.
    
    
    """    
    
    logger.info(f"Search endpoint called with company name: {company_name}")
    
    try:
        # Get the raw result from the scraper
        #raw result contains links and addresses ect. but since i dont need it is not used and instead we use ComapnyInfo model
        raw_result = get_companies_from_name_company(company_name)
        
        # Debug the entire result structure
        logger.info(f"Raw result structure: {type(raw_result)}")
        
        # Check if the result is a dictionary with the expected structure
        if not isinstance(raw_result, dict):
            logger.error(f"Result is not a dictionary: {raw_result}")
            return CompanySearchByNameResponse()
            
        # Extract the data field which contains the companies
        if "data" not in raw_result:
            logger.error(f"Result does not contain 'data' field: {raw_result}")
            return CompanySearchByNameResponse()
            
        companies_data = raw_result["data"]
        count = raw_result.get("count", len(companies_data) if isinstance(companies_data, dict) else 0)
        
        # Create a dictionary of CompanyInfo models
        parsed_companies = {}
        
        if isinstance(companies_data, dict):
            for ico, company_data in companies_data.items():
                try:
                    # Create CompanyInfo model from the company data
                    company_model = CompanyInfo.model_validate(company_data)
                    parsed_companies[ico] = company_model
                except Exception as e:
                    logger.error(f"Error parsing company data for ICO {ico}: {str(e)}")
                    # Skip this company if there's an error
                    continue
        
        # Return the CompanySearchByNameResponse model
        return CompanySearchByNameResponse(
            companies=parsed_companies,
            count=count
        )
        
    except Exception as e:
        logger.error(f"Error in get_companies_by_company_name: {str(e)}", exc_info=True)
        return CompanySearchByNameResponse()

@router.get("/ico", response_model=CompanyInfo)
async def get_company_by_ico(
    ico: int,
    current_user: User = Depends(get_current_user)
):
    """Get company details for a given company ICO (identification number).
    
    Returns detailed company information including establishment date, registration details,
    address, and other available data from justice records.
    
    Makes scraping call which might take a long time.
    """    
    
    logger.info(f"Search endpoint called with ICO: {ico}")
    
    try:
        # Get the raw result from the scraper
        raw_result = get_companies_from_ico(ico)
        
        # Debug the entire result structure
        logger.info(f"Raw result structure: {type(raw_result)}")
        
        # Check if the result is a dictionary with the expected structure
        if not isinstance(raw_result, dict):
            logger.error(f"Result is not a dictionary: {raw_result}")
            raise HTTPException(status_code=404, detail="Company not found")
            
        # Extract the data field which contains the company
        if "data" not in raw_result:
            logger.error(f"Result does not contain 'data' field: {raw_result}")
            raise HTTPException(status_code=404, detail="Company not found")
            
        companies_data = raw_result["data"]
        
        # Since we're searching by ICO, we should only have one company
        # But the data is still structured as a dictionary with ICO as key
        if not companies_data:
            logger.error("No company data found")
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Get the first (and should be only) company from the dictionary
        ico_str = str(ico)
        if ico_str in companies_data:
            company_data = companies_data[ico_str]
        else:
            # If the exact ICO isn't a key, just take the first company
            first_ico = next(iter(companies_data))
            company_data = companies_data[first_ico]
        
        # Create CompanyInfo model from the company data
        try:
            company_model = CompanyInfo.model_validate(company_data)
            return company_model
        except Exception as e:
            logger.error(f"Error parsing company data: {str(e)}")
            raise HTTPException(status_code=500, detail="Error processing company data")
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error in get_company_by_ico: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@router.post("/valuate")
async def valuate_company_by_ico(
    background_tasks: BackgroundTasks,
    ico: int, 
    current_user: User = Depends(get_current_user)
):
    """
    Triggers scraping of specific company based on ICO, gets latest financials,
    saves them to Supabase storage, and processes them to generate a valuation report.
    
    Returns a response with the report ID for tracking the process.
    """
    
    logger.info(f"Valuating company with ICO: {ico}")
    
    try:
        # Get the latest financial document
        file_content, filename, year = get_latest_financial_document(ico)
        
        if not file_content:
            logger.error(f"No financial document found for ICO: {ico}")
            raise HTTPException(status_code=404, detail="No financial document found for this company")
            
        logger.info(f"Retrieved financial document for ICO: {ico}, filename: {filename}, year: {year}")
        
        # Check if the file is actually a PDF
        if file_content[:4] != b'%PDF':
            # First few bytes of a PDF file should be "%PDF"
            logger.error(f"Downloaded file is not a valid PDF. First 20 bytes: {file_content[:20]}")
            
            # Save the content for debugging
            debug_path = Path("backend/temp") / f"debug_{ico}_{uuid.uuid4()}.txt"
            with open(debug_path, "wb") as f:
                f.write(file_content)
            
            # Check if it's an HTML error page
            if b'<html' in file_content.lower() or b'<!doctype html' in file_content.lower():
                logger.error("Received HTML content instead of PDF. This might be an error page or login redirect.")
                raise HTTPException(status_code=500, detail="The server returned an HTML page instead of a PDF document")
            
            raise HTTPException(status_code=500, detail="The downloaded file is not a valid PDF")
            
        # Create a unique filename
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Use os.getenv directly as a fallback
        temp_storage_path = os.getenv("TEMP_STORAGE_PATH", "backend/temp")
        temp_file_path = Path(temp_storage_path) / unique_filename
        
        # Save file temporarily
        temp_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Create a pending report record
        report_id = str(uuid.uuid4())
        report_data = {
            "id": report_id,
            "user_id": str(current_user.id),
            "file_name": filename,
            "report_url": "",  # Will be updated after processing
            "status": "pending",
            "original_file_path": str(temp_file_path)
            # Removed fields that might not exist in the database schema
        }
        supabase.table("reports").insert(report_data).execute()
        
        # Process the file in the background
        background_tasks.add_task(
            process_financial_task,
            str(temp_file_path),
            str(current_user.id),
            report_id
        )
        
        return JSONResponse(
            status_code=202,  # Accepted
            content={
                "status": "processing",
                "report_id": report_id,
                "message": "Financial document retrieved and being processed. Check the dashboard for updates in 10 seconds."
            }
        )
        
    except Exception as e:
        logger.error(f"Error in valuate_company_by_ico: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
        
   
    
    
    
    
    


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
            "status": "processed"
        }
        
        # Only add report_url if it exists in the result
        if result and "report_url" in result:
            update_data["report_url"] = result["report_url"]
            
        supabase.table("reports").update(update_data).eq("id", report_id).execute()
        
        # No need to clean up temp file here as workflow.execute already does it
        
    except Exception as e:
        # Update report with error status
        try:
            update_data = {
                "status": "failed"
                # Removed error_message field that might not exist
            }
            supabase.table("reports").update(update_data).eq("id", report_id).execute()
        except Exception as db_error:
            logger.error(f"Failed to update report status: {str(db_error)}")
        
        # Clean up temp file if it still exists
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up temp file: {str(cleanup_error)}")
                
        logger.error(f"Failed to process file: {str(e)}")