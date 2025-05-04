# -*- coding: utf-8 -*-
import requests
import argparse
import logging
import time
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime
from dateutil.parser import parse as dateutil_parse
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- Constants ---
BASE_URL = "https://or.justice.cz/ias/ui/"
SEARCH_PAGE_URL = urljoin(BASE_URL, "rejstrik-$firma") # NEW: Initial search page for companies (firma)
DEFAULT_OUTPUT_DIR = Path("./downloaded_financials_ico") # Changed default dir slightly
MAX_RETRIES = 3 # Retries for direct requests (like PDF download)
RETRY_DELAY_SECONDS = 2
SELENIUM_TIMEOUT = 20 # Seconds to wait for elements

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()]) # Output logs to console

#surpress logging in debug mode of charset issue when it tries to guess country format of binary = pdf file which is nonsense only txt file could be detected
logging.getLogger('chardet.charsetprober').setLevel(logging.WARNING)
# --- Helper Functions ---
def _parse_czech_date(date_str):
    """Parses Czech date format (e.g., DD.MM.YYYY) safely."""
    if not date_str:
        return None
    try:
        # Attempt standard parsing first
        return dateutil_parse(date_str, dayfirst=True).date()
    except ValueError:
        logging.warning(f"Could not parse date string: {date_str}")
        return None

# --- Scraper Class ---
class CzechIcoScraper: # Renamed class
    """
    Scrapes financial documents ('účetní závěrka') from or.justice.cz
    for a given company IČO using Selenium for browser interaction.
    """
    def __init__(self, output_dir=DEFAULT_OUTPUT_DIR, force_download=False, webdriver_path=None):
        self.output_dir = Path(output_dir)
        self.force_download = force_download
        self.base_url = BASE_URL
        self.webdriver_path = webdriver_path # Optional path to chromedriver/geckodriver

        # Initialize the download session *before* initializing the driver
        # so the driver can access its headers (e.g., User-Agent)
        self.download_session = requests.Session()
        self.download_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        # Now initialize the driver
        self.driver = self._init_driver()

        # Logging after initialization
        logging.info(f"Output directory set to: {self.output_dir}")
        logging.info(f"Force download: {self.force_download}")

    def _init_driver(self):
        """Initializes the Selenium WebDriver."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')  # Use the new headless mode
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920x1080')
        options.add_argument('--no-sandbox') # Often needed in containerized environments
        options.add_argument('--disable-dev-shm-usage') # Often needed in containerized environments
        options.add_argument(f"user-agent={self.download_session.headers['User-Agent']}")

        try:
            if self.webdriver_path:
                 from selenium.webdriver.chrome.service import Service as ChromeService
                 service = ChromeService(executable_path=self.webdriver_path)
                 driver = webdriver.Chrome(service=service, options=options)
                 logging.info(f"Started ChromeDriver using path: {self.webdriver_path}")
            else:
                 # Assume webdriver is in PATH
                 from selenium.webdriver.chrome.service import Service as ChromeService # Import here too
                 # Try default service first
                 try:
                     driver = webdriver.Chrome(options=options)
                     logging.info("Started ChromeDriver assuming it's in PATH.")
                 except Exception as path_e:
                     logging.warning(f"Could not start ChromeDriver from PATH ({path_e}). Ensure it's installed and in PATH, or provide --webdriver-path.")
                     # As a fallback, try common relative paths (less reliable)
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
                          raise path_e # Re-raise original error if no fallback works

            return driver
        except Exception as e:
            logging.error(f"Failed to initialize Selenium WebDriver: {e}")
            logging.error("Ensure you have the correct WebDriver (e.g., chromedriver) installed.")
            logging.error("Download from: https://chromedriver.chromium.org/downloads (match your Chrome version).")
            logging.error("Either add it to your system's PATH, place it in the script's directory, or provide the path via --webdriver-path argument.")
            raise

    def _make_request(self, url, method='GET', data=None, params=None, allow_redirects=True):
         """Makes a direct HTTP request (used primarily for PDF download)."""
         for attempt in range(MAX_RETRIES):
             try:
                 response = self.download_session.request(method, url, data=data, params=params, timeout=30, allow_redirects=allow_redirects)
                 response.raise_for_status()
                 if "Systémová chyba" in response.text:
                      logging.error(f"Potential server-side error detected in response from {url}. Content snippet: {response.text[:500]}")
                      raise requests.exceptions.RequestException("Server indicated an error in the response content.")
                 # Note: Removed 'Neplatný požadavek' check here as it's less relevant for direct downloads
                 logging.info(f"Successfully fetched (direct request) {response.url} (Status: {response.status_code})")
                 return response
             except requests.exceptions.Timeout:
                 logging.warning(f"Timeout occurred for {url}. Retrying ({attempt + 1}/{MAX_RETRIES})...")
             except requests.exceptions.HTTPError as e:
                  if e.response.status_code == 429:
                      logging.warning(f"Rate limit hit (429) for {url}. Retrying ({attempt + 1}/{MAX_RETRIES}) after delay...")
                  elif e.response.status_code >= 500:
                      logging.warning(f"Server error ({e.response.status_code}) for {url}. Retrying ({attempt + 1}/{MAX_RETRIES})...")
                  else:
                      logging.error(f"HTTP Error for {url}: {e}")
                      return None
             except requests.exceptions.RequestException as e:
                 logging.warning(f"Request failed for {url}: {e}. Retrying ({attempt + 1}/{MAX_RETRIES})...")

             if attempt < MAX_RETRIES - 1:
                 delay = RETRY_DELAY_SECONDS * (2 ** attempt)
                 logging.info(f"Waiting {delay} seconds before next retry.")
                 time.sleep(delay)
             else:
                 logging.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts.")
                 return None

    def find_subjekt_id_by_ico(self, ico):
        """Searches for the company by IČO using Selenium and extracts the subjekt ID."""
        logging.info(f"Navigating to company search page: {SEARCH_PAGE_URL}")
        if not self.driver: return None # Driver failed to init
        try:
            self.driver.get(SEARCH_PAGE_URL)
            wait = WebDriverWait(self.driver, SELENIUM_TIMEOUT)

            logging.debug(f"Waiting for IČO input field (id=id3)...")
            # The IČO input field on rejstrik-$firma has id="id3"
            ico_input = wait.until(EC.presence_of_element_located((By.ID, "id3")))
            logging.debug("IČO input field found.")

            ico_input.clear()
            ico_input.send_keys(ico)
            logging.debug(f"Entered IČO: {ico}")

            logging.debug("Looking for search button...")
            # The search button xpath is the same
            search_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'button') and .//span[contains(@class, 'i-search')]]")))
            logging.debug("Search button found, clicking...")
            search_button.click()

            logging.debug("Waiting for search results details or 'nenalezen' message...")
            # Wait for either the results table or the 'not found' div
            results_element = wait.until(EC.presence_of_element_located((By.XPATH, "//table[contains(@class, 'result-details')] | //div[contains(text(), 'Výpis nenalezen')] | //div[contains(text(), 'Subjekt nenalezen')] | //h2[contains(., 'Počet nalezených subjektů')] ")))
            # The h2 appears if multiple results are somehow returned, treat this as an unexpected case for ICO search

            # Check if "Výpis nenalezen" or "Subjekt nenalezen" appeared
            try:
                # Check multiple possible 'not found' texts
                not_found_element = self.driver.find_element(By.XPATH, "//div[contains(text(), 'Výpis nenalezen')] | //div[contains(text(), 'Subjekt nenalezen')]")
                if not_found_element:
                    logging.info(f"No results found for IČO {ico} ('{not_found_element.text}' message displayed).")
                    return None
            except NoSuchElementException:
                 # This is expected if results *were* found
                 logging.debug("Search results page/details loaded successfully.")
                 pass # Continue to parse results

            # Check if the ambiguous 'Počet nalezených subjektů' header appeared - should not happen for unique ICO
            try:
                multi_results_header = self.driver.find_element(By.XPATH, "//h2[contains(., 'Počet nalezených subjektů')]")
                if multi_results_header:
                     logging.warning(f"Multiple results found for IČO {ico}, which is unexpected. Trying to parse the first result's 'Sbírka listin' link anyway.")
                     # Proceed with parsing, hoping the first result is correct
            except NoSuchElementException:
                # Expected path if single result details are shown directly
                pass

            # --- Parse the results page source using BeautifulSoup ---
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'lxml')
            subjekt_id = None
            current_url = self.driver.current_url # Base for relative links

            # Look for the 'Sbírka listin' link within the results area
            # It might be directly in a 'result-links' ul like in person search, or within the 'result-details' table area
            sbirka_link_tag = None

            # Try finding it within a potential result list first (if multiple results shown unexpectedly)
            result_links_ul = soup.find('ul', class_='result-links')
            if result_links_ul:
                sbirka_link_tag = result_links_ul.find('a', string='Sbírka listin', href=True)
                logging.debug("Found 'Sbírka listin' link within 'ul.result-links'.")

            # If not found there, try finding it anywhere on the page (more robust for single direct result)
            if not sbirka_link_tag:
                logging.debug("Did not find link in 'ul.result-links', searching globally for 'Sbírka listin' link.")
                # This selector finds an 'a' tag whose href contains 'vypis-sl-firma'
                # and whose text content *is exactly* 'Sbírka listin'
                # We might need to be more flexible if the text isn't exact match
                # sbirka_link_tag = soup.find('a', href=lambda href: href and 'vypis-sl-firma' in href, string='Sbírka listin')

                # More flexible search: Find any 'a' tag with 'Sbírka listin' text
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    if link.get_text(strip=True) == 'Sbírka listin' and 'vypis-sl-firma' in link.get('href', ''):
                        sbirka_link_tag = link
                        logging.debug("Found 'Sbírka listin' link via broader search.")
                        break # Take the first match

            if sbirka_link_tag:
                href = sbirka_link_tag.get('href')
                absolute_href = urljoin(current_url, href) # Make sure it's absolute
                parsed_href = urlparse(absolute_href)
                query_params = parse_qs(parsed_href.query)
                subjekt_id = query_params.get('subjektId', [None])[0]
                if subjekt_id:
                    logging.info(f"Extracted subjektId: {subjekt_id} for IČO {ico}")
                    return subjekt_id
                else:
                    logging.error(f"Found 'Sbírka listin' link for IČO {ico} but could not extract subjektId from href: {href}")
                    return None
            else:
                logging.error(f"Could not find 'Sbírka listin' link on the results page for IČO {ico}.")
                # Save source for debugging this case
                try:
                    debug_filename = f"debug_ico_search_no_link_{ico}.html"
                    with open(debug_filename, "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                    logging.info(f"Saved page source to {debug_filename}")
                except Exception as dump_e:
                    logging.error(f"Could not save debug page source: {dump_e}")
                return None

        except TimeoutException:
            logging.error(f"Timeout waiting for element during IČO search for {ico}.")
            logging.debug(f"Last URL: {self.driver.current_url}")
            # Save source for debugging
            try:
                debug_filename = f"debug_ico_search_timeout_{ico}.html"
                with open(debug_filename, "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                logging.info(f"Saved page source to {debug_filename}")
            except Exception as dump_e:
                 logging.error(f"Could not save debug page source: {dump_e}")
            return None
        except NoSuchElementException as e:
            logging.error(f"Could not find an expected element during IČO search for {ico}: {e}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred during IČO search for {ico}: {e}", exc_info=True)
            return None

    def find_latest_financial_doc_link(self, subjekt_id):
        """Finds the link to the detail page of the latest 'účetní závěrka' using Selenium."""
        logging.info(f"Navigating to Sbírka listin page for subjektId: {subjekt_id}")
        if not self.driver: return None, None # Driver failed to init
        # Construct the company version of the Sbírka listin URL
        sbirka_url = urljoin(self.base_url, f"vypis-sl-firma?subjektId={subjekt_id}")
        logging.info(f"Using Sbírka listin URL: {sbirka_url}") # Log the constructed URL

        try:
            self.driver.get(sbirka_url)
            wait = WebDriverWait(self.driver, SELENIUM_TIMEOUT)

            logging.debug("Waiting for document table to load...")
            # The table structure should be the same for companies and individuals
            wait.until(EC.presence_of_element_located((By.XPATH, "//table[.//th[contains(text(), 'Číslo listiny')] and .//th[contains(text(), 'Typ listiny')]] | //div[contains(text(),'Sbírka listin neobsahuje žádné dokumenty')] ")))
            # Added check for empty collection message
            logging.debug("Document table or 'empty' message found.")

            # Check if the empty message is present
            try:
                empty_msg = self.driver.find_element(By.XPATH, "//div[contains(text(),'Sbírka listin neobsahuje žádné dokumenty')]")
                if empty_msg:
                     logging.info(f"Sbírka listin is empty for subjektId: {subjekt_id}. No documents to process.")
                     return None, None
            except NoSuchElementException:
                 logging.debug("Document table seems populated (no 'empty' message detected).")
                 pass # Proceed to parse table

            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'lxml')
            potential_docs = []
            current_url = self.driver.current_url # URL of the Sbírka listin page

            # --- Find the main table containing the documents ---
            doc_table = None
            tables = soup.find_all('table')
            logging.debug(f"Found {len(tables)} tables on Sbírka listin page.")
            for table in tables:
                headers = table.find_all('th')
                header_texts = [th.get_text(strip=True) for th in headers]
                if 'Číslo listiny' in header_texts and 'Typ listiny' in header_texts:
                     doc_table = table
                     logging.debug("Found potential document table based on headers.")
                     break

            if not doc_table:
                 logging.warning(f"Could not find the document table on Sbírka listin page for {subjekt_id} using headers. Falling back to finding all <tr>.")
                 # Try finding the specific table structure seen before
                 doc_table = soup.find('table', class_='vysledky') # Assuming it might have this class
                 if not doc_table:
                     logging.error(f"Could not find document table for {subjekt_id}. Cannot proceed.")
                     return None, None
                 else:
                     logging.debug("Found table using fallback class 'vysledky'.")

            tbody = doc_table.find('tbody')
            rows = tbody.find_all('tr') if tbody else doc_table.find_all('tr')

            logging.debug(f"Processing {len(rows)} rows for documents.")

            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 4:
                    # logging.debug(f"Skipping row, not enough cells (<4): {row.get_text(strip=True)[:50]}")
                    continue

                # Link is typically in the first cell
                doc_link_tag = cells[0].find('a', href=lambda href: href and 'vypis-sl-detail' in href)
                # Type is in the second cell
                type_cell_text = cells[1].get_text(strip=True)
                # Publication date ('Došlo na soud') seems to be the 4th column (index 3)
                if len(cells) > 3:
                    publication_date_str = cells[3].get_text(strip=True)
                    publication_date = _parse_czech_date(publication_date_str)
                else:
                    publication_date_str = None
                    publication_date = None
                    logging.debug("Row has less than 4 cells, cannot get publication date.")


                # Check for 'účetní závěrka' and extract year
                if 'účetní závěrka' in type_cell_text and '[' in type_cell_text and ']' in type_cell_text:
                    try:
                        # Find the specific text 'účetní závěrka' to anchor the year search
                        year_part = type_cell_text[type_cell_text.find('účetní závěrka'):]
                        start_index = year_part.find('[')
                        end_index = year_part.find(']')
                        if start_index != -1 and end_index != -1 and end_index > start_index:
                            year_str = year_part[start_index + 1 : end_index]
                            year = int(year_str)
                            if doc_link_tag and doc_link_tag.get('href'):
                                detail_link = urljoin(current_url, doc_link_tag['href']) # Resolve relative URL
                                potential_docs.append({
                                    'year': year, 'link': detail_link,
                                    'publication_date': publication_date if publication_date else datetime.min.date(), # Handle missing date
                                    'row_text': row.get_text(separator=' ', strip=True)[:100] # For debugging
                                })
                                logging.debug(f"Found potential doc: Year {year}, Link {detail_link}, Date {publication_date_str}")
                            else:
                                logging.debug(f"Found 'účetní závěrka' year {year} but no detail link in row.")
                        else:
                            logging.warning(f"Could not find valid brackets '[]' for year extraction in: {type_cell_text}")
                    except (ValueError, IndexError):
                        logging.warning(f"Could not parse year from type cell text: {type_cell_text}")

            if not potential_docs:
                logging.info(f"No 'účetní závěrka' documents found for subjektId: {subjekt_id}")
                return None, None

            # Find the latest year among the found documents
            latest_year = max(doc['year'] for doc in potential_docs)
            logging.debug(f"Latest year found: {latest_year}")

            # Filter for documents from the latest year
            latest_year_docs = [doc for doc in potential_docs if doc['year'] == latest_year]

            # Sort the latest year's documents by publication date (newest first)
            latest_year_docs.sort(key=lambda x: x['publication_date'], reverse=True)

            if not latest_year_docs:
                 # This shouldn't happen if potential_docs was not empty and latest_year was found
                 logging.error(f"Logic error: No docs after filtering for year {latest_year}.")
                 return None, None

            # Select the first document (which is the latest published of the latest year)
            chosen_doc = latest_year_docs[0]
            logging.info(f"Selected document: Year {chosen_doc['year']}, Date {chosen_doc['publication_date']}, Link: {chosen_doc['link']}")
            logging.debug(f"Selected based on row snippet: {chosen_doc['row_text']}")

            return chosen_doc['link'], chosen_doc['year']

        except TimeoutException:
            logging.error(f"Timeout waiting for element on Sbírka listin page for {subjekt_id} at {sbirka_url}.")
            return None, None
        except Exception as e:
            logging.error(f"An unexpected error occurred finding document link for {subjekt_id}: {e}", exc_info=True)
            return None, None

    def find_pdf_download_link(self, detail_page_url):
        """Finds the PDF download link on the document detail page using Selenium."""
        logging.info(f"Navigating to document detail page: {detail_page_url}")
        if not self.driver: return None, None # Driver failed to init
        try:
            self.driver.get(detail_page_url)
            wait = WebDriverWait(self.driver, SELENIUM_TIMEOUT)

            logging.debug("Waiting for download link element...")
            # The download link structure seems consistent
            download_link_element = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/ias/content/download?id=')]")))
            logging.debug("Download link element found.")

            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'lxml')
            # Find the specific link again in the soup, ensuring it matches the one found by Selenium
            link_href_selenium = download_link_element.get_attribute('href')
            download_link_tag = soup.find('a', href=lambda href: href and href == link_href_selenium)

            if not download_link_tag:
                 # If the exact href match fails, try the broader search again (should be rare)
                 logging.warning("Could not find exact link in BS matching Selenium href. Retrying broader BS search.")
                 download_link_tag = soup.find('a', href=lambda href: href and '/ias/content/download?id=' in href)


            if download_link_tag and download_link_tag.get('href'):
                 # Construct absolute URL for the download link
                 pdf_link = urljoin(self.base_url, download_link_tag['href']) # Use base_url
                 # Try to extract a meaningful filename from the link text or span
                 span_tags = download_link_tag.find_all('span')
                 pdf_filename_text = ""
                 if span_tags:
                     # Often the filename is in the first span
                     pdf_filename_text = span_tags[0].get_text(strip=True)
                 else:
                     # Fallback to the link's text
                     pdf_filename_text = download_link_tag.get_text(strip=True)

                 # If no text found, generate a fallback name based on download ID
                 if not pdf_filename_text:
                      parsed_link = urlparse(pdf_link)
                      query_params = parse_qs(parsed_link.query)
                      doc_id = query_params.get('id', ['unknown_id'])[0]
                      pdf_filename_text = f"document_{doc_id}.pdf"
                      logging.warning(f"Could not determine filename from link text, using generated name: {pdf_filename_text}")

                 # Clean up filename (remove size info like '(1.23 MB)')
                 pdf_filename = pdf_filename_text.split('(')[0].strip()
                 # Ensure it has a common document extension (PDF mainly, but allow archives)
                 if not pdf_filename.lower().endswith('.pdf'):
                      # Check for other common archive types seen in Sbírka listin
                      if not any(pdf_filename.lower().endswith(ext) for ext in ['.zip', '.rar', '.7z', '.doc', '.docx', '.rtf']):
                          logging.debug(f"Filename '{pdf_filename}' doesn't end with a common document/archive extension. Appending '.pdf' as default.")
                          pdf_filename += '.pdf'
                      else:
                           logging.info(f"Filename '{pdf_filename}' has a non-PDF but plausible extension.")

                 logging.info(f"Found document download link: {pdf_link} (Filename: {pdf_filename})")
                 return pdf_link, pdf_filename
            else:
                 logging.warning(f"Could not find PDF download link tag in BeautifulSoup after Selenium wait on page: {detail_page_url}")
                 return None, None

        except TimeoutException:
            logging.error(f"Timeout waiting for download link on detail page: {detail_page_url}")
            # Save source for debugging
            try:
                # Create a safe filename from the URL query
                safe_page_id = "".join(c if c.isalnum() else '_' for c in urlparse(detail_page_url).query)
                debug_filename = f"debug_pdf_link_timeout_{safe_page_id}.html"
                with open(debug_filename, "w", encoding="utf-8") as f:
                     f.write(self.driver.page_source)
                logging.info(f"Saved page source to {debug_filename}")
            except Exception as dump_e:
                 logging.error(f"Could not save debug page source: {dump_e}")
            return None, None
        except Exception as e:
            logging.error(f"An unexpected error occurred finding PDF download link on {detail_page_url}: {e}", exc_info=True)
            return None, None

    def download_pdf(self, pdf_url, target_folder_name, pdf_filename):
        """Downloads the PDF file using the requests session."""
        # This method uses self._make_request which uses self.download_session
        if not pdf_url or not pdf_filename or not target_folder_name:
             logging.error("Invalid PDF URL, filename, or target folder name provided for download.")
             return False

        # Sanitize folder and file names
        safe_folder_name = "".join(c if c.isalnum() or c in ['_', '-'] else '_' for c in str(target_folder_name))
        problematic_chars = r'\/:*?"<>|' # Characters invalid in Windows filenames
        safe_filename = "".join('_' if c in problematic_chars else c for c in pdf_filename)[:200] # Limit length

        target_dir = self.output_dir / safe_folder_name
        target_dir.mkdir(parents=True, exist_ok=True)
        filepath = target_dir / safe_filename

        # Check if file exists and force_download is False
        if filepath.exists() and not self.force_download:
            logging.info(f"File already exists and force_download is false. Skipping: {filepath}")
            # Return True because skipping isn't a failure in this context
            return True # Indicate skipped successfully

        logging.info(f"Downloading file using requests from {pdf_url} to {filepath}")
        try:
            pdf_response = self._make_request(pdf_url, allow_redirects=True) # Use the helper
            if not pdf_response:
                 logging.error(f"Failed to get response for {pdf_url}. Download aborted.")
                 return False # Error already logged by _make_request

            content_type = pdf_response.headers.get('Content-Type', '').lower()
            # Allow common PDF types and generic binary stream, also handle text/html for potential error pages
            if not any(ct in content_type for ct in ['application/pdf', 'application/octet-stream', 'binary/octet-stream', 'application/zip', 'application/x-zip-compressed']):
                # Check if it's an error page disguised as download
                if 'text/html' in content_type and ("Chyba" in pdf_response.text or "Error" in pdf_response.text or "nenalezen" in pdf_response.text):
                     logging.error(f"Received HTML error page instead of file for {pdf_url}. Content snippet: {pdf_response.text[:200]}")
                     return False
                logging.warning(f"Unexpected content type '{content_type}' for {pdf_url}. Attempting to save anyway.")

            if pdf_response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in pdf_response.iter_content(chunk_size=8192):
                        f.write(chunk)
                # Verify download success
                if filepath.exists() and filepath.stat().st_size > 0:
                    logging.info(f"Successfully downloaded {filepath} ({filepath.stat().st_size} bytes)")
                    return True # Indicate successful download
                else:
                    # Handle cases where file is empty after writing (e.g., disk full, permissions)
                    logging.error(f"Downloaded file is empty or missing after write: {filepath} (Size: {filepath.stat().st_size if filepath.exists() else 'N/A'})")
                    if filepath.exists():
                        try: filepath.unlink() # Clean up empty file
                        except OSError as e: logging.error(f"Could not delete empty/failed file: {e}")
                    return False # Indicate download failure
            else:
                # Should be caught by _make_request's raise_for_status, but log just in case
                logging.error(f"PDF download request failed with status {pdf_response.status_code} for {pdf_url}")
                return False # Indicate download failure
        except Exception as e:
            logging.error(f"Download or save failed for {pdf_url} to {filepath}: {e}", exc_info=True)
            # Clean up potentially incomplete file
            if filepath.exists():
                 try: filepath.unlink()
                 except OSError as e: logging.error(f"Could not delete incomplete file: {e}")
            return False # Indicate download failure

    def scrape(self, ico):
        """Main scraping workflow for a given company IČO."""
        if not self.driver:
             logging.error("WebDriver not initialized. Exiting.")
             return

        try:
            logging.info(f"--- Starting scrape for IČO: {ico} ---")
            subjekt_id = self.find_subjekt_id_by_ico(ico)

            if not subjekt_id:
                logging.info(f"Could not find a valid subjektId for IČO {ico}. Scraping cannot proceed.")
                # No need to return here, finally block will close driver
            else:
                # Use ICO as the folder name
                company_folder = str(ico) # Folder name is the ICO
                download_count = 0
                failed_count = 0
                skipped_count = 0        # Renamed for clarity
                already_exists_count = 0 # Renamed for clarity

                logging.info(f"--- Processing Subjekt ID: {subjekt_id} (found for IČO {ico}) ---")
                detail_link, year = self.find_latest_financial_doc_link(subjekt_id)

                if not detail_link or not year:
                    logging.warning(f"Could not find latest 'účetní závěrka' document link for subjektId: {subjekt_id}. Skipping.")
                    skipped_count += 1
                else:
                    pdf_link, pdf_filename = self.find_pdf_download_link(detail_link)

                    if not pdf_link or not pdf_filename:
                        logging.warning(f"Could not find PDF download link for subjektId: {subjekt_id} on page {detail_link}. Skipping.")
                        skipped_count += 1
                    else:
                        # Prepare filename/path for checking existence and downloading
                        safe_company_folder = "".join(c if c.isalnum() or c in ['_', '-'] else '_' for c in company_folder)
                        problematic_chars = r'\/:*?"<>|'
                        safe_filename = "".join('_' if c in problematic_chars else c for c in pdf_filename)[:200]
                        target_dir = self.output_dir / safe_company_folder
                        target_dir.mkdir(parents=True, exist_ok=True) # Ensure target dir exists
                        filepath = target_dir / safe_filename

                        if filepath.exists() and not self.force_download:
                            logging.info(f"File already exists and force_download is false. Skipping: {filepath}")
                            already_exists_count += 1
                            time.sleep(0.1)
                        else:
                            # Attempt download using the existing download_pdf method
                            success = self.download_pdf(pdf_link, company_folder, pdf_filename)
                            if success:
                                # If download_pdf returns True, it means downloaded OR skipped existing.
                                # We already handled the skip case above, so True here means downloaded.
                                download_count += 1
                            else:
                                failed_count += 1

                            # Be polite to the server (only if we actually downloaded)
                            if success:
                                time.sleep(1.0 + (os.urandom(1)[0] / 255.0)) # 1-2 second delay

                logging.info(f"--- Scraping finished for IČO: {ico} (Subjekt ID: {subjekt_id}) ---")
                logging.info(f"Summary: Downloads: {download_count}, Already Existed: {already_exists_count}, Doc/Link Not Found: {skipped_count}, Failed Downloads: {failed_count}")

        except Exception as e:
             logging.error(f"An error occurred during the scraping process for IČO {ico}: {e}", exc_info=True)
        finally:
            # Ensure the browser closes even if errors occur
            if hasattr(self, 'driver') and self.driver:
                logging.info("Closing WebDriver.")
                self.driver.quit()
                self.driver = None # Prevent trying to close again if error happens during close

def get_latest_financial_document(ico):
    """
    Scrapes and returns the latest financial document for a given ICO.
    
    Args:
        ico (str or int): Company identification number (IČO)
        
    Returns:
        tuple: (file_content, filename, year) where:
            - file_content is the binary content of the PDF file
            - filename is the original filename from the source
            - year is the year of the financial statement
            
        Returns (None, None, None) if no document is found or an error occurs.
    """
    logging.info(f"--- Starting to fetch latest financial document for IČO: {ico} ---")
    
    scraper_instance = None
    try:
        # Initialize scraper without saving files
        scraper_instance = CzechIcoScraper(
            output_dir="./temp_downloads",  # Temporary directory
            force_download=True
        )
        
        # Find the company's subject ID
        subjekt_id = scraper_instance.find_subjekt_id_by_ico(ico)
        if not subjekt_id:
            logging.info(f"Could not find a valid subjektId for IČO {ico}. Fetching cannot proceed.")
            return None, None, None
            
        # Find the latest financial document link
        detail_link, year = scraper_instance.find_latest_financial_doc_link(subjekt_id)
        if not detail_link or not year:
            logging.warning(f"Could not find latest 'účetní závěrka' document link for subjektId: {subjekt_id}.")
            return None, None, None
            
        # Find the PDF download link
        pdf_link, pdf_filename = scraper_instance.find_pdf_download_link(detail_link)
        if not pdf_link or not pdf_filename:
            logging.warning(f"Could not find PDF download link for subjektId: {subjekt_id} on page {detail_link}.")
            return None, None, None
            
        # Download the content directly without saving to file
        logging.info(f"Downloading file content from {pdf_link}")
        try:
            pdf_response = scraper_instance._make_request(pdf_link, allow_redirects=True)
            if not pdf_response:
                logging.error(f"Failed to get response for {pdf_link}. Download aborted.")
                return None, None, None
                
            content_type = pdf_response.headers.get('Content-Type', '').lower()
            # Check for error pages
            if 'text/html' in content_type and ("Chyba" in pdf_response.text or "Error" in pdf_response.text or "nenalezen" in pdf_response.text):
                logging.error(f"Received HTML error page instead of file for {pdf_link}.")
                return None, None, None
                
            if pdf_response.status_code == 200:
                file_content = pdf_response.content
                
                # Add validation to ensure it's a PDF
                if file_content[:4] != b'%PDF':
                    # Check if it's an HTML error page
                    if b'<html' in file_content.lower() or b'<!doctype html' in file_content.lower():
                        logging.error("Received HTML content instead of PDF. This might be an error page or login redirect.")
                        # Save the HTML content for debugging
                        with open("./temp_downloads/html_content.html", "wb") as f:
                            f.write(file_content)
                        logging.error(f"Saved HTML content to ./temp_downloads/html_content.html for debugging")
                        return None, None, None
                
                logging.info(f"Successfully downloaded content ({len(file_content)} bytes)")
                return file_content, pdf_filename, year
            else:
                logging.error(f"PDF download request failed with status {pdf_response.status_code} for {pdf_link}")
                return None, None, None
                
        except Exception as e:
            logging.error(f"Download failed for {pdf_link}: {e}", exc_info=True)
            return None, None, None
            
    except Exception as e:
        logging.error(f"An error occurred during the fetching process for IČO {ico}: {e}", exc_info=True)
        return None, None, None
    finally:
        # Ensure the browser closes even if errors occur
        if scraper_instance and hasattr(scraper_instance, 'driver') and scraper_instance.driver:
            logging.info("Closing WebDriver.")
            scraper_instance.driver.quit()
            
    return None, None, None

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Czech company financial documents by IČO using Selenium.") # Updated description
    parser.add_argument("-i", "--ico", required=True, help="Company identification number (IČO).") # Changed to --ico
    parser.add_argument("-o", "--output-dir", default=str(DEFAULT_OUTPUT_DIR), help=f"Directory to save downloaded PDFs (default: {DEFAULT_OUTPUT_DIR}).")
    parser.add_argument("--force", action='store_true', help="Force download even if file exists.")
    parser.add_argument("--debug", action='store_true', help="Enable debug logging.")
    parser.add_argument("--webdriver-path", help="Optional path to the WebDriver executable (e.g., chromedriver.exe)")


    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.info("Debug logging enabled.")

    scraper_instance = None
    try:
        # Pass webdriver_path during initialization
        scraper_instance = CzechIcoScraper(
            output_dir=args.output_dir,
            force_download=args.force,
            webdriver_path=args.webdriver_path
        )
        scraper_instance.scrape(args.ico) # Call scrape with ico
    except Exception as e:
        # Catch errors during init or scrape
        logging.critical(f"Script failed with critical error: {e}", exc_info=True)
    finally:
        # Ensure driver is closed if scrape failed mid-way and didn't reach its own finally block
        if scraper_instance and hasattr(scraper_instance, 'driver') and scraper_instance.driver:
             logging.warning("Closing WebDriver from main exception handler (scrape might have failed).")
             scraper_instance.driver.quit()


    logging.info("Script finished.")
