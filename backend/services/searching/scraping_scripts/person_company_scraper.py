# -*- coding: utf-8 -*-
import logging
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from dateutil.parser import parse as dateutil_parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os

# --- Constants ---
BASE_URL = "https://or.justice.cz/ias/ui/"
SEARCH_PAGE_URL = urljoin(BASE_URL, "rejstrik-$osoba")  # Initial search page
SELENIUM_TIMEOUT = 20  # Seconds to wait for elements
DEFAULT_CHROMEDRIVER_PATH = None  # Remove hardcoded path to allow automatic detection

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])  # Output logs to console

# --- Helper Functions ---
def _parse_czech_date(date_str):
    """Parses Czech date format (e.g., 'DD. měsíce YYYY' or 'DD.MM.YYYY') safely."""
    if not date_str:
        return None
    
    # Dictionary to map Czech month names to numbers
    czech_months = {
        'ledna': 1, 'února': 2, 'března': 3, 'dubna': 4, 'května': 5, 'června': 6,
        'července': 7, 'srpna': 8, 'září': 9, 'října': 10, 'listopadu': 11, 'prosince': 12
    }
    
    try:
        # Check for Czech verbal date format: "DD. měsíce YYYY"
        czech_pattern = r'(\d+)\.\s+(\w+)\s+(\d{4})'
        match = re.match(czech_pattern, date_str)
        if match:
            day, month_name, year = match.groups()
            month = czech_months.get(month_name.lower())
            if month:
                return datetime(int(year), month, int(day)).date()
        
        # Attempt standard parsing as fallback
        return dateutil_parse(date_str, dayfirst=True).date()
    except (ValueError, KeyError):
        logging.warning(f"Could not parse date string: {date_str}")
        return None

def _strip_whitespace(text):
    """Removes excessive whitespace and normalizes text."""
    if not text:
        return ""
    # Replace any sequence of whitespace with a single space
    return re.sub(r'\s+', ' ', text).strip()

def _clean_ico(ico_text):
    """Cleans ICO numbers by removing any spacing."""
    if not ico_text:
        return ""
    # Remove all non-digits
    return re.sub(r'[^\d]', '', ico_text)

# --- Scraper Class ---
class CzechCompanyScraper:
    """
    Scrapes company information from or.justice.cz for a given person using Selenium.
    Returns company details as a dictionary.
    """
    def __init__(self, webdriver_path=None):
        self.base_url = BASE_URL
        self.webdriver_path = webdriver_path if webdriver_path else DEFAULT_CHROMEDRIVER_PATH
        self.driver = None  # Initialize driver only when needed

    def _init_driver(self):
        """Initializes the Selenium WebDriver."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in background for API use
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920x1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

        try:
            if self.webdriver_path:
                 from selenium.webdriver.chrome.service import Service as ChromeService
                 service = ChromeService(executable_path=self.webdriver_path)
                 driver = webdriver.Chrome(service=service, options=options)
                 logging.info(f"Started ChromeDriver using path: {self.webdriver_path}")
            else:
                 # Assume webdriver is in PATH
                 from selenium.webdriver.chrome.service import Service as ChromeService
                 try:
                     driver = webdriver.Chrome(options=options)
                     logging.info("Started ChromeDriver assuming it's in PATH.")
                 except Exception as path_e:
                     logging.warning(f"Could not start ChromeDriver from PATH ({path_e}).")
                     # Try common relative paths as fallback
                     possible_paths = ['./chromedriver.exe', 'chromedriver.exe', './chromedriver', 'chromedriver']
                     found_path = None
                     for p_path in possible_paths:
                         if os.path.exists(p_path):
                             found_path = p_path
                             break
                     if found_path:
                         logging.info(f"Attempting to start ChromeDriver from relative path: {found_path}")
                         service = ChromeService(executable_path=found_path)
                         driver = webdriver.Chrome(service=service, options=options)
                     else:
                          raise path_e

            return driver
        except Exception as e:
            logging.error(f"Failed to initialize Selenium WebDriver: {e}")
            return None

    def search_person(self, first_name, last_name):
        """Performs the search for a person and returns the search results page source."""
        logging.info(f"Navigating to search page: {SEARCH_PAGE_URL}")
        if not self.driver:
            self.driver = self._init_driver()
            if not self.driver:
                return None  # Driver failed to init
        
        try:
            self.driver.get(SEARCH_PAGE_URL)
            wait = WebDriverWait(self.driver, SELENIUM_TIMEOUT)

            logging.debug("Waiting for input fields...")
            prijmeni_input = wait.until(EC.presence_of_element_located((By.ID, "id3")))
            jmeno_input = wait.until(EC.presence_of_element_located((By.ID, "id4")))
            logging.debug("Input fields found.")

            prijmeni_input.clear()
            prijmeni_input.send_keys(last_name)
            logging.debug(f"Entered lastname: {last_name}")

            jmeno_input.clear()
            jmeno_input.send_keys(first_name)
            logging.debug(f"Entered firstname: {first_name}")

            logging.debug("Looking for search button...")
            search_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'button') and .//span[contains(@class, 'i-search')]]")))
            logging.debug("Search button found, clicking...")
            search_button.click()

            logging.debug("Waiting for search results to load...")
            wait.until(EC.presence_of_element_located((By.XPATH, "//h2[contains(., 'Počet nalezených subjektů')] | //div[contains(text(), 'Výpis nenalezen')]")))
            
            # Check if "Výpis nenalezen" appeared instead of results
            try:
                not_found_element = self.driver.find_element(By.XPATH, "//div[contains(text(), 'Výpis nenalezen')]")
                if not_found_element:
                    logging.info(f"No results found for {first_name} {last_name} ('Výpis nenalezen' message displayed).")
                    return None
            except NoSuchElementException:
                # This is expected if results were found
                logging.info("Search results page loaded successfully.")
                
            # Wait a moment for the results to fully load
            time.sleep(1.5)
            
            return self.driver.page_source
            
        except TimeoutException:
            logging.error("Timeout waiting for element during search.")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred during search: {e}", exc_info=True)
            return None

    def parse_search_results(self, page_source):
        """Parses the search results page and extracts company information."""
        if not page_source:
            return {}
        
        soup = BeautifulSoup(page_source, 'lxml')
        companies_data = {}
        
        # Find all company result items
        result_items = soup.select('div.search-results ol li.result')
        logging.info(f"Found {len(result_items)} result items.")
        
        if not result_items:
            logging.warning("No result items found in the page source.")
            return {}
        
        for item in result_items:
            company_data = {}
            
            # Find the company information
            person_info_rows = item.select('tbody tr')
            
            # First check for person's information (name, birth date, address)
            person_details = {}
            company_ico = None
            
            for row in person_info_rows:
                # Get all th and td elements in this row
                headers = row.find_all('th')
                cells = row.find_all('td')
                
                if len(headers) == 0 or len(cells) == 0:
                    continue
                
                # Process data based on the row structure
                for i, header in enumerate(headers):
                    header_text = _strip_whitespace(header.get_text())
                    
                    if i < len(cells):
                        cell_text = _strip_whitespace(cells[i].get_text())
                        
                        # Extract Person's info
                        if header_text == "Jméno:":
                            person_details['full_name'] = cell_text
                        elif header_text == "Datum narození:":
                            person_details['birth_date'] = cell_text
                            # Also try to parse the date
                            parsed_date = _parse_czech_date(cell_text)
                            if parsed_date:
                                person_details['birth_date_iso'] = parsed_date.isoformat()
                        elif header_text == "Adresa:":
                            person_details['address'] = cell_text
                        elif header_text == "Angažmá:":
                            person_details['role'] = cell_text
                        
                        # Extract Company info
                        elif header_text == "Název subjektu:":
                            company_data['company_name'] = cell_text
                        elif header_text == "IČO:":
                            ico_clean = _clean_ico(cell_text)
                            if ico_clean:
                                company_data['ico'] = ico_clean
                                company_ico = ico_clean  # Save for dictionary key
                        elif header_text == "Spisová značka:":
                            company_data['file_reference'] = cell_text
                        elif header_text == "Den zápisu:":
                            company_data['registration_date'] = cell_text
                            # Also try to parse the date
                            parsed_date = _parse_czech_date(cell_text)
                            if parsed_date:
                                company_data['registration_date_iso'] = parsed_date.isoformat()
            
            # Add person details to company data if we have a valid ICO
            if company_ico and company_ico.strip():
                # Only add person details if they exist
                if person_details:
                    company_data['person'] = person_details
                
                # Validate that we have essential company data before adding
                if 'company_name' in company_data:
                    companies_data[company_ico] = company_data
                else:
                    logging.warning(f"Found company with ICO {company_ico} but missing name, skipping.")
            else:
                logging.debug("Skipping result item without valid ICO.")
        
        # Log summary of valid companies found
        logging.info(f"Successfully extracted data for {len(companies_data)} companies with valid ICO numbers.")
        
        return companies_data

    def close(self):
        """Close the WebDriver if it's open."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logging.error(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None

    def __del__(self):
        """Ensure driver is closed when object is garbage collected."""
        self.close()

# --- API Function ---
def scrape_companies_by_person(first_name, last_name):
    """
    API-friendly function to scrape companies associated with a person.
    
    Args:
        first_name (str): First name of the person
        last_name (str): Last name of the person
        
    Returns:
        dict: Dictionary with companies associated with the person
    """
    try:
        logging.info(f"Starting scrape for person: {first_name} {last_name}")
        
        scraper = CzechCompanyScraper()
        result = {"status": "success", "data": {}}
        
        try:
            # Search for the person
            search_results_html = scraper.search_person(first_name, last_name)
            
            if not search_results_html:
                result["status"] = "no_results"
                result["message"] = f"No results found for {first_name} {last_name}"
                return result
            
            # Parse the results page to extract company information
            companies_data = scraper.parse_search_results(search_results_html)
            
            if not companies_data:
                result["status"] = "no_companies"
                result["message"] = f"No company information found for {first_name} {last_name}"
                return result
            
            result["data"] = companies_data
            result["count"] = len(companies_data)
            
            return result
            
        finally:
            # Always close the browser
            scraper.close()
            
    except Exception as e:
        logging.error(f"Error in scrape_companies_by_person: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}",
            "data": {}
        }

# --- CLI Execution (keep for testing) ---
if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Scrape Czech company information for a person using Selenium.")
    parser.add_argument("-f", "--first-name", required=True, help="Person's first name (jmeno).")
    parser.add_argument("-l", "--last-name", required=True, help="Person's last name (prijmeni).")
    parser.add_argument("-o", "--output-file", help="JSON file to save the results (optional).")
    parser.add_argument("--debug", action='store_true', help="Enable debug logging.")
    parser.add_argument("--webdriver-path", default=DEFAULT_CHROMEDRIVER_PATH, help=f"Path to the ChromeDriver executable")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.info("Debug logging enabled.")

    # Use the API function for CLI as well
    result = scrape_companies_by_person(args.first_name, args.last_name)
    
    # Print results to console
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Optionally save to file
    if args.output_file and result["status"] in ["success", "no_results", "no_companies"]:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        logging.info(f"Results saved to {args.output_file}")
