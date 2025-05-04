from typing import Dict, Any, List
import logging

# Import the scraping functions directly
from backend.searching.scraping_scripts.person_company_scraper import scrape_companies_by_person
from backend.searching.scraping_scripts.ico_company_scraper import scrape_company_by_ico
from backend.searching.scraping_scripts.name_company_scraper import scrape_companies_by_name

# Setup logging
logger = logging.getLogger(__name__)

def get_companies_from_ico(ico: int) -> Dict[str, Any]:
    """Get company information by ICO number
    
    Args:
        ico (int): ICO of company in Czech Republic
        
    Returns:
        Dict[str, Any]: Dictionary with company details including status and data
    """
    logger.info(f"Requesting company information for ICO: {ico}")
    # Convert ico to string if it's an integer
    ico_str = str(ico) if isinstance(ico, int) else ico
    return scrape_company_by_ico(ico_str)
    
def get_companies_from_name_person(first_name: str, last_name: str) -> Dict[str, Any]:
    """Get companies associated with a person
    
    Args:
        first_name (str): First name of the person
        last_name (str): Last name of the person
        
    Returns:
        Dict[str, Any]: Dictionary with structure:
            {
                "status": str,
                "message": str (optional),
                "count": int (optional),
                "data": {
                    "ico1": {company_details1},
                    "ico2": {company_details2},
                    ...
                }
            }
    """
    logger.info(f"Requesting companies for person: {first_name} {last_name}")
    return scrape_companies_by_person(first_name, last_name)
    
def get_companies_from_name_company(company_name: str) -> Dict[str, Any]:
    """Get companies matching a company name
    
    Args:
        company_name (str): Name of the company to search for
        
    Returns:
        Dict[str, Any]: Dictionary with structure:
            {
                "status": str,
                "message": str (optional),
                "count": int (optional),
                "data": {
                    "ico1": {company_details1},
                    "ico2": {company_details2},
                    ...
                }
            }
    """
    logger.info(f"Requesting companies with name: {company_name}")
    return scrape_companies_by_name(company_name)




