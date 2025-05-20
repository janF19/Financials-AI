import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import logging

logger = logging.getLogger(__name__)

def get_company_name_by_ico(ico: str) -> dict[str, str] | None:
    """
    Translates a company IČO to its name by scraping the justice.cz website using Selenium.

    Args:
        ico: The company identification number (IČO) as a string.

    Returns:
        A dictionary with 'name' and 'ico' if found, otherwise None.
    """
    url = "https://or.justice.cz/ias/ui/rejstrik-$firma"

    chrome_options = Options()
    chrome_options.add_argument("--headless") # Run in headless mode (no browser UI)
    chrome_options.add_argument("--disable-gpu") # Recommended for headless
    chrome_options.add_argument("--window-size=1920,1080") # Specify window size for headless
    
    # Use webdriver-manager to automatically download and manage ChromeDriver
    driver = None # Initialize driver to None for the finally block
    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.set_page_load_timeout(60) # 60 seconds timeout for page load
        logger.debug(f"WebDriver initialized for ico_name lookup for ICO: {ico}")
        driver.get(url)

        # Locate the IČO input field and fill it
        ico_input_selector_id = "id3"
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, ico_input_selector_id))
        )
        ico_input_element = driver.find_element(By.ID, ico_input_selector_id)
        ico_input_element.send_keys(ico)
        logger.debug(f"Filled IČO {ico} into input field for ico_name.")

        # Locate and click the search button
        # The button has text " Vyhledat" (with a leading space in the span)
        # Assuming the button is within <p class="search-buttons">
        search_button_xpath = "//p[@class='search-buttons']//button[normalize-space(.//span)='Vyhledat']"
        # Alternative if the above is too specific or if there's only one such button:
        # search_button_xpath = "//button[normalize-space(.//span)='Vyhledat']"
        
        logger.debug(f"Waiting for search button with XPath: {search_button_xpath}")
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, search_button_xpath))
        )
        search_button = driver.find_element(By.XPATH, search_button_xpath)
        logger.debug("Search button found and clickable for ico_name.")
        search_button.click()
        # Alternative click method if the standard click fails:
        # driver.execute_script("arguments[0].click();", search_button)
        logger.debug(f"Clicked search button for IČO {ico} for ico_name.")

        # Wait for the results table to appear after the dynamic page update
        result_table_selector_class = "result-details"
        logger.debug(f"Waiting for result table with class '{result_table_selector_class}' for ico_name...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, result_table_selector_class))
        )
        logger.debug("Result table found for ico_name.")

        # Extract the company name
        # The company name is in <strong class="left">COMPANY_NAME</strong>
        # This is in a <td> next to a <th> containing "Název subjektu:"
        company_name_xpath = '//table[@class="result-details"]//th[normalize-space(text())="Název subjektu:"]/following-sibling::td/strong[@class="left"]'
        
        company_name_element = driver.find_element(By.XPATH, company_name_xpath)
        company_name = company_name_element.text
        return {"name": company_name.strip(), "ico": ico}

    except TimeoutException:
        logger.warning(f"Timeout (get_company_name_by_ico): Could not find company details for IČO {ico}. The IČO might be invalid or the page structure changed.")
        return None
    except NoSuchElementException:
        logger.warning(f"Element not found (get_company_name_by_ico): Could not find company details for IČO {ico}. The page structure might have changed.")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while processing IČO {ico} in get_company_name_by_ico: {e}", exc_info=True)
        return None
    finally:
        if driver:
            driver.quit()
            logger.debug(f"WebDriver quit for ico_name lookup for ICO: {ico}")

if __name__ == "__main__":
    # Example usage:
    # ISOTRA a.s. IČO: 47679191
    test_ico_valid = "47679191"
    company_details = get_company_name_by_ico(test_ico_valid)
    if company_details:
        print(f"IČO: {company_details['ico']}, Company Name: {company_details['name']}")
    else:
        print(f"Could not find company name for IČO: {test_ico_valid}")

    print("-" * 20)

    # # Test with a potentially invalid/non-existent IČO
    # test_ico_invalid = "12345670"
    # company_details_invalid = get_company_name_by_ico(test_ico_invalid)
    # if company_details_invalid:
    #     print(f"IČO: {company_details_invalid['ico']}, Company Name: {company_details_invalid['name']}")
    # else:
    #     print(f"Could not find company name for IČO: {test_ico_invalid}")
