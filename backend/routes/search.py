from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, Any
import io
import requests
from typing import List, Optional, Dict
from uuid import UUID
from backend.config.settings import settings
from backend.models.user import User
from backend.models.report import ReportResponse
from backend.auth.dependencies import get_current_user
from backend.database import supabase
from pydantic import BaseModel
from backend.services.searching.scraping_methods import get_companies_from_ico, get_companies_from_name_company, get_companies_from_name_person
import logging
from backend.models.search_models import CompanyInfo, CompanySearchByPersonResponse, CompanySearchByNameResponse
import json
from backend.services.searching.scraping_scripts.ico_file_scraper import get_latest_financial_document
from fastapi import BackgroundTasks
from pathlib import Path
import uuid
import os
from backend.services.processors.workflow2 import ValuationWorkflow2
from backend.utils.usage_limiter import check_and_increment_api_usage
from backend.tasks import process_ico_valuation_task

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
    ico: int,
    current_user: User = Depends(get_current_user)
):
    """
    Triggers scraping for ICO, gets latest financials, saves them,
    and processes them via workflow. Checks API usage limits first.
    """
    logger.info(f"Received valuation request for ICO: {ico} from user {current_user.id}")

    # --- BEGIN RATE LIMIT CHECK ---
    try:
        check_and_increment_api_usage(current_user)
    except HTTPException as http_exc:
        raise http_exc
    # --- END RATE LIMIT CHECK ---

    temp_file_path = None # Initialize to None
    try:
        # Get the latest financial document
        logger.info(f"Attempting to fetch financial document for ICO: {ico}")
        file_content, filename, year = get_latest_financial_document(ico)

        if not file_content:
            logger.error(f"No financial document found for ICO: {ico}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No financial document found for this company")

        logger.info(f"Retrieved financial document for ICO: {ico}, filename: {filename}, year: {year}")

        # Basic PDF check (can be improved)
        if file_content[:4] != b'%PDF':
            logger.error(f"Downloaded file for ICO {ico} is not a valid PDF. Filename: {filename}")
            # Consider saving for debug?
            # debug_path = Path("backend/temp") / f"debug_{ico}_{uuid.uuid4()}.bin"
            # debug_path.parent.mkdir(parents=True, exist_ok=True)
            # with open(debug_path, "wb") as f:
            #     f.write(file_content)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Downloaded financial document is not a valid PDF.")

        # Create a unique filename
        unique_filename = f"{uuid.uuid4()}_{filename}"
        temp_storage_path = settings.TEMP_STORAGE_PATH # Use settings
        temp_file_path = Path(temp_storage_path) / unique_filename

        # Save file temporarily
        logger.info(f"Saving temporary file to: {temp_file_path}")
        temp_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_file_path, "wb") as buffer:
            buffer.write(file_content)

        # Create a pending report record
        report_id = str(uuid.uuid4())
        report_data = {
            "id": report_id,
            "user_id": str(current_user.id),
            "file_name": filename, # Use the original filename from scraping
            "report_url": "",
            "status": "pending",
            "original_file_path": str(temp_file_path),
            # "ico": str(ico) # <-- Simply comment out or delete this line
        }
        logger.info(f"Creating pending report record {report_id} (ICO {ico} not stored in DB)") # Optional: Modify log
        supabase.table("reports").insert(report_data).execute()

        # Process the file in the background
        logger.info(f"Adding Celery task process_ico_valuation_task for report {report_id}")
        process_ico_valuation_task.delay(
            str(temp_file_path),
            str(current_user.id),
            report_id
        )

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "processing",
                "report_id": report_id,
                "message": "Financial document retrieved and processing started. Check the dashboard for updates."
            }
        )

    except HTTPException as http_exc:
         # If an HTTPException occurred (404, 500, or 429 from check), clean up temp file if it was created
        if temp_file_path and temp_file_path.exists():
            try:
                os.remove(temp_file_path)
                logger.info(f"Cleaned up temp file {temp_file_path} after HTTPException.")
            except OSError as rm_error:
                logger.error(f"Error removing temp file {temp_file_path} after HTTPException: {rm_error}")
        # Re-raise the original HTTPException
        raise http_exc

    except Exception as e:
        logger.error(f"Error during ICO valuation setup for ICO {ico}, user {current_user.id}: {e}", exc_info=True)
         # Clean up temp file if created before the error
        if temp_file_path and temp_file_path.exists():
            try:
                os.remove(temp_file_path)
                logger.info(f"Cleaned up temp file {temp_file_path} after general exception.")
            except OSError as rm_error:
                logger.error(f"Error removing temp file {temp_file_path} after general exception: {rm_error}")
        # Don't create a report record here, as the process failed before the task was added.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while initiating valuation: {str(e)}")