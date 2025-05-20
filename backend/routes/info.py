from fastapi import APIRouter, Depends, HTTPException, Query, Request


from typing import List, Optional, Dict
from backend.config import settings
from backend.models.user import User
from backend.models.report import ReportResponse
from backend.auth.dependencies import get_current_user
from backend.database import supabase
from pydantic import BaseModel
import logging
from backend.services.info_search.main_workflow import collect_all_info_data
from backend.models.info_models import CompanyAllInfoResponse
import re
import time
from collections import defaultdict




router = APIRouter(prefix="/info", tags=["info"])

logger = logging.getLogger(__name__)

# --- BEGIN CUSTOM RATE LIMITER CONFIGURATION ---
# Store request timestamps: {ip_address: [timestamp1, timestamp2, ...]}
# For a production app, use Redis or a similar persistent store.
request_timestamps_ip = defaultdict(list)
RATE_LIMIT_MAX_REQUESTS = 10  # Max requests allowed
RATE_LIMIT_WINDOW_SECONDS = 60  # Time window in seconds
# --- END CUSTOM RATE LIMITER CONFIGURATION ---


@router.get("/{ico}", response_model=CompanyAllInfoResponse)
async def get_all_information(ico: str, request: Request, current_user: User = Depends(get_current_user)):
    """
    Get all available information about a company based on its ICO.
    This includes justice ministry records, DPH (VAT) status, subsidies, and web search analysis.
    The user must be authenticated, and API usage limits apply.
    """
    logger.info(f"User {current_user.id} requesting all information for ICO: {ico}")

    # --- BEGIN CUSTOM IP-BASED RATE LIMIT CHECK ---
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()

    # Filter out timestamps older than the window
    request_timestamps_ip[client_ip] = [
        ts for ts in request_timestamps_ip[client_ip] if ts > current_time - RATE_LIMIT_WINDOW_SECONDS
    ]

    if len(request_timestamps_ip[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        logger.warning(f"Rate limit exceeded for IP {client_ip} for ICO {ico}")
        raise HTTPException(
            status_code=429,  # Too Many Requests
            detail="Too many requests from this IP address. Please try again later."
        )
    
    request_timestamps_ip[client_ip].append(current_time)
    # --- END CUSTOM IP-BASED RATE LIMIT CHECK ---

    # Validate ICO: must be a string of 8 digits.
    # The `ico: str` type hint already ensures it's a string.
    if not (ico.isdigit() and len(ico) == 8):
        logger.error(f"Invalid ICO format received: {ico}")
        raise HTTPException(
            status_code=400, 
            detail="Invalid ICO format. ICO must be an 8-digit number."
        )
    
    logger.info(f"ICO {ico} validated. Proceeding to collect data for user {current_user.id}.")
    result = collect_all_info_data(ico)
    
    # collect_all_info_data is designed to return a structured dict,
    # even if parts of it are default/empty.
    # Pydantic will validate the structure against CompanyAllInfoResponse.
    # If result could be None or truly empty in a way that means "not found at all",
    # you might add a check here:
    
    

    logger.info(f"Successfully collected data for ICO: {ico}")
    return result

