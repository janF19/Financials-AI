import argparse
import json
import sys
import logging # New import
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# Configure logger for this module
logger = logging.getLogger(__name__)

def scrape_dotace(ico_code):
    """
    Scrapes the 'Částka uvolněná' for a given IČO from the specified website.
    """
    url = "https://red.fs.gov.cz/registr-dotaci/prijemci"
    
    # Setup WebDriver (Chrome in this example)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run in headless mode
    options.add_argument('--disable-gpu')  # Optional, recommended for headless
    options.add_argument('--no-sandbox')  # Optional, for running as root/in Docker
    options.add_argument('--disable-dev-shm-usage')  # Optional, overcome limited resource problems
    options.add_argument('log-level=3') # Suppress console logs from Chrome/ChromeDriver
    options.add_experimental_option('excludeSwitches', ['enable-logging']) # Suppress DevTools listening message

    driver = None # Initialize driver to None for the finally block
    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        logger.debug(f"WebDriver initialized for dotace.py for ICO: {ico_code}")
        driver.get(url)
        
        # Wait for the search input field to be present and interactable
        search_input_locator = (By.CSS_SELECTOR, 'input[name="search"].search-input')
        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(search_input_locator)
        )
        
        search_input = driver.find_element(*search_input_locator)
        search_input.clear() # Clear the input field first
        search_input.send_keys(ico_code)
        search_input.send_keys(Keys.ENTER)
        
        # First check if "no results" message appears
        try:
            no_results_locator = (By.XPATH, "//div[contains(text(), 'Nebyly nalezeny žádné záznamy')]")
            WebDriverWait(driver, 7).until(
                EC.visibility_of_element_located(no_results_locator)
            )
            # If we found the "no results" message, return with null value
            logger.info(f"No subsidy data found for ICO {ico_code} on red.fs.gov.cz (Nebyly nalezeny žádné záznamy).")
            return {"uvolnena": None}
        except TimeoutException:
            # No "no results" message found, continue with normal flow
            pass
        
        # Wait for the results to load.
        # XPath for the amount: targets the span containing the value,
        # by first finding its preceding sibling span with the text 'Částka uvolněná'.
        amount_locator = (By.XPATH, "//span[text()='Částka uvolněná']/following-sibling::span[contains(@class, 'text-lg') and contains(@class, 'font-bold') and contains(@class, 'font-headers')]")
        
        try:
            WebDriverWait(driver, 20).until(
                EC.visibility_of_element_located(amount_locator)
            )
            
            amount_element = driver.find_element(*amount_locator)
            amount_text = amount_element.text
            
            # Clean the amount text (e.g., "154&nbsp;152&nbsp;897,03&nbsp;Kč")
            # Selenium's .text usually converts &nbsp; to a regular space or \xa0
            cleaned_amount_text = amount_text.replace("Kč", "").strip()
            cleaned_amount_text = cleaned_amount_text.replace("\xa0", "")  # Non-breaking space
            cleaned_amount_text = cleaned_amount_text.replace(" ", "")    # Regular space
            cleaned_amount_text = cleaned_amount_text.replace(",", ".")
            
            try:
                uvolnena_value = float(cleaned_amount_text)
            except ValueError:
                logger.error(f"Could not convert amount '{cleaned_amount_text}' (from original '{amount_text}') to float for ICO {ico_code}.", exc_info=True)
                return {"uvolnena": None}
                
            logger.info(f"Successfully scraped 'Částka uvolněná': {uvolnena_value} for ICO {ico_code}.")
            return {"uvolnena": uvolnena_value}
        except TimeoutException:
            # If we can't find the amount element, return with null value
            logger.info(f"No 'Částka uvolněná' data found for ICO {ico_code} after search (amount element not visible).")
            return {"uvolnena": None}
        except StaleElementReferenceException:
            # If the element becomes stale, it likely means the page changed (e.g., to "no results")
            logger.warning(f"Data element became stale for ICO {ico_code} in dotace.py, likely indicating no data or page changed.", exc_info=True)
            return {"uvolnena": None}
        
    except TimeoutException:
        logger.error(f"Timed out waiting for page elements for ICO {ico_code} in dotace.py. The ICO might not exist, no data found, or the page structure changed.", exc_info=True)
        # You can add driver.save_screenshot('debug_timeout.png') here for debugging
        return {"uvolnena": None}
    except NoSuchElementException:
        logger.error(f"Could not find expected page elements for ICO {ico_code} in dotace.py. The ICO might not exist, no data found, or the page structure changed.", exc_info=True)
        # You can add driver.save_screenshot('debug_noelement.png') here for debugging
        return {"uvolnena": None}
    except Exception as e:
        logger.error(f"An unexpected error occurred for ICO {ico_code} in dotace.py: {e}", exc_info=True)
        # You can add driver.save_screenshot('debug_exception.png') here for debugging
        return {"uvolnena": None}
    finally:
        if driver:
            driver.quit()
            logger.debug(f"WebDriver quit for dotace.py for ICO: {ico_code}")

if __name__ == "__main__":
    # Basic logging configuration for standalone script execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    parser = argparse.ArgumentParser(description="Scrape 'Částka uvolněná' for a given IČO from red.fs.gov.cz.")
    parser.add_argument("ico", help="The IČO code to search for.")
    
    args = parser.parse_args()
    
    result = scrape_dotace(args.ico)
    
    if result and result.get("uvolnena") is not None:
        # Output JSON to stdout
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result and result.get("uvolnena") is None:
        logger.info(f"No subsidy data found for ICO {args.ico}, result: {result}")
        # Output JSON with null to stdout to indicate "no data found" explicitly
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # Error messages are logged within the scrape_dotace function
        logger.error(f"Scraping failed or returned unexpected result for ICO {args.ico}. Result: {result}")
        # Output an error structure to stdout for consistency if needed by a calling script
        print(json.dumps({"error": f"Scraping failed for ICO {args.ico}", "uvolnena": None}, ensure_ascii=False, indent=2))
        sys.exit(1) # Exit with an error code if scraping failed
