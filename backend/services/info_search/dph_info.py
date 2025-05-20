import json
import sys
import time
from datetime import datetime
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_dph_info(ico):
    # Base URL
    search_url = "https://adisspr.mfcr.cz/dpr/DphReg"
    
    logger.info(f"Starting search for ICO: {ico}")
    
    # Set up Chrome options for headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    
    # options.add_argument('--headless')  # Uncomment to run in headless mode (no browser window)
    # options.add_argument('--no-sandbox') # Recommended for headless mode in certain environments
    # options.add_argument('--disable-dev-shm-usage') # Recommended for headless mode in certain environments
    chrome_options.add_argument('--log-level=3') # Suppress most informational logs from Chrome/ChromeDriver
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    # Initialize the driver
    driver = None
    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        logger.debug(f"WebDriver initialized for DPH info for ICO: {ico}")

        # Navigate to the search page
        logger.info(f"Navigating to {search_url}")
        driver.get(search_url)
        
        # Wait for the page to fully load
        # It's better to wait for a specific element, e.g., the input field itself.
        # The WebDriverWait below for input_field effectively covers this.
        
        # Wait for the input field to be available
        input_field_locator = (By.ID, "form:dt:0:inputDic")
        input_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(input_field_locator)
        )
        logger.debug(f"Input field located for DPH info for ICO: {ico}")
        
        # Enter the ICO
        input_field.clear()
        input_field.send_keys(ico)
        
        # Wait for the search button to become enabled/clickable
        search_button_locator = (By.ID, "form:hledej")
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(search_button_locator)
        )
        logger.debug(f"Search button located and clickable for DPH info for ICO: {ico}")
        
        # Find and click the search button (already located by WebDriverWait)
        # search_button = driver.find_element(By.ID, "form:hledej") # Not needed if using WebDriverWait's return
        
        # Use JavaScript to click the button
        driver.execute_script("arguments[0].click();", search_button)
        logger.info(f"Search button clicked for DPH info for ICO: {ico}")
        
        # Wait for page to load after search
        # Wait for a specific element that indicates results are loaded or "no results"
        # For example, wait for the "Údaje o subjektu DPH" text or a known results container.
        # This is tricky if the "no results" page is very different.
        # A simple check for a known element on either page type, or a slightly longer explicit wait if dynamic content is hard to pin down.
        # For now, we'll rely on the page_source check, but an explicit wait for a common wrapper element would be better.
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        logger.info("Page state complete after search for DPH info.")
        
        # Get page source
        page_source = driver.page_source
        
        # Parse the page with BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Initialize result dictionary
        result = {
            "nespolehlivy_platce": None,
            "registrace_od_data": None
        }
        
        # Look for specific text that indicates we're on a results page
        if "Údaje o subjektu DPH" in page_source:
            logger.info("Processing results page")
            
            # Find nespolehlivy platce
            nespolehlivy_label = soup.find(string="Nespolehlivý plátce:")
            if nespolehlivy_label:
                nespolehlivy_cell = nespolehlivy_label.find_parent("td").find_next_sibling("td")
                if nespolehlivy_cell:
                    result["nespolehlivy_platce"] = nespolehlivy_cell.text.strip()
                    logger.info(f"Nespolehlivý plátce: {result['nespolehlivy_platce']}")
            
            # Find registration date
            registrace_table = soup.find(string="Údaje o registraci k DPH")
            if registrace_table:
                # Navigate to the table with registration data
                table = registrace_table.find_parent("span").find_parent("td").find_parent("tr").find_parent("tbody").find_parent("table")
                if table:
                    # Find rows with data
                    data_rows = table.find_all("tr")
                    for row in data_rows:
                        if "Registrace platná od" in row.text:
                            continue
                        
                        # Look for the date cell
                        date_cells = row.find_all("td", {"class": "col2"})
                        if date_cells and len(date_cells) > 0:
                            date_span = date_cells[0].find("span", {"class": "data"})
                            if date_span:
                                date_str = date_span.text.strip()
                                if date_str:
                                    try:
                                        # Convert date to standard format
                                        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
                                        result["registrace_od_data"] = date_obj.strftime("%Y-%m-%d")
                                        logger.info(f"Registrace od data: {result['registrace_od_data']}")
                                        break
                                    except ValueError:
                                        result["registrace_od_data"] = date_str
                                        logger.warning(f"Could not parse date: {date_str}, using original string.")
                                        break
        else:
            logger.warning(f"Could not find 'Údaje o subjektu DPH' on the page for ICO: {ico}. The page might have changed or no results were found.")

        logger.info(f"Final result for ICO {ico}: {result}")
        
        return result
    except TimeoutException as te:
        logger.error(f"Timeout occurred while fetching DPH info for ICO {ico}: {str(te)}", exc_info=True)
        # Return default structure on timeout
        return {"nespolehlivy_platce": None, "registrace_od_data": None}
    except NoSuchElementException as nse:
        logger.error(f"NoSuchElement occurred while fetching DPH info for ICO {ico}: {str(nse)}", exc_info=True)
        # Return default structure
        return {"nespolehlivy_platce": None, "registrace_od_data": None}
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching DPH info for ICO {ico}: {str(e)}", exc_info=True)
        # Return default structure on other errors
        return {"nespolehlivy_platce": None, "registrace_od_data": None}
    finally:
        if driver:
            driver.quit()
            logger.debug(f"WebDriver quit for DPH info for ICO: {ico}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python dph_info.py <ICO>")
        sys.exit(1)
    
    ico = sys.argv[1]
    try:
        result = get_dph_info(ico)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}", exc_info=True)
        print(json.dumps({"error": str(e)}, ensure_ascii=False))

if __name__ == "__main__":
    main()

