import json
import re
import logging

import requests
from bs4 import BeautifulSoup, NavigableString
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import google.generativeai as genai
import json
import os

# Configure logger for this module
logger = logging.getLogger(__name__)

def _get_default_justice_structure():
    """
    Returns the default empty structure for justice_info,
    consistent with Pydantic models where optional complex objects are None if empty.
    """
    return {
        "obchodni_firma": None,
        "sídlo": {"adresa_kompletni": None}, # Sídlo object is always present, its fields can be None
        "identifikacni_cislo": None,
        "pravni_forma": None,
        "datum_vzniku_a_zapisu": None,
        "spisova_znacka": None,
        "predmet_podnikani": [],
        "statutarni_organ_predstavenstvo": None, # Set to None if section is empty
        "dozorci_rada": None, # Set to None if section is empty
        "prokura": None, # Set to None if section is empty
        "jediny_akcionar": None, # Set to None if section is empty
        "akcie": [],
        "zakladni_kapital": None,
        "splaceno": None,
        "ostatni_skutecnosti": [],
    }

# 2. Function to load your text data
def get_justice_info_by_ico(ico: str) -> str | None:
    """
    Retrieves company information from or.justice.cz based on IČO.

    Args:
        ico: The company registration number (IČO).

    Returns:
        The HTML source code of the company's "Výpis platných" page,
        or None if an error occurs or the information cannot be found.
    """
    base_url = "https://or.justice.cz/ias/ui/rejstrik-$firma"
    
    # Configure Chrome options (e.g., for headless browsing)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Uncomment to run in headless mode (no browser window)
    options.add_argument('--no-sandbox') # Recommended for headless mode in certain environments
    options.add_argument('--disable-dev-shm-usage') # Recommended for headless mode in certain environments
    options.add_argument('--log-level=3') # Suppress most informational logs from Chrome/ChromeDriver
    # Suppress DevTools listening message if not needed for debugging
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    driver = None  # Initialize driver to None for the finally block

    try:
        # Consider using webdriver_manager for robust ChromeDriver handling
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        logger.debug(f"WebDriver initialized for justice.cz for ICO: {ico}")
        
        # 1. Navigate to the initial URL
        driver.get(base_url)

        # 2. Wait for IČO input field, clear it, and enter IČO
        ico_input_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "id3"))
        )
        ico_input_field.clear()
        ico_input_field.send_keys(ico)

        # 3. Find and click the search button
        # The search button is <button ...><span class=" i-16 i-search"> Vyhledat</span></button>
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[normalize-space()='Vyhledat']]"))
        )
        search_button.click()

        # 4. Wait for the search results to appear and find the "Výpis platných" link
        # The link is <a href="...">Výpis platných</a> within <div class="search-results">
        vypis_platnych_link_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class='search-results']//a[text()='Výpis platných']"))
        )
        
        # 5. Get the href attribute (URL) of the "Výpis platných" link
        vypis_platnych_url = vypis_platnych_link_element.get_attribute("href")
        if not vypis_platnych_url:
            logger.warning(f"Could not find the URL for 'Výpis platných' for IČO {ico}.")
            return None

        # 6. Navigate to the new URL
        driver.get(vypis_platnych_url)

        # Optional: Wait for a specific element on the final page to ensure it's fully loaded.
        # For example, you could wait for a known table or header.
        # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "some-element-on-final-page")))

        # 7. Get the page source of the final page
        final_page_source = driver.page_source
        return final_page_source

    except TimeoutException:
        logger.error(f"A timeout occurred while trying to scrape data for IČO {ico} from justice.cz. The IČO might be invalid or no results were found.", exc_info=True)
        return None
    except NoSuchElementException:
        logger.error(f"A required element was not found on the page for IČO {ico} on justice.cz.", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while processing IČO {ico} on justice.cz: {e}", exc_info=True)
        return None
    finally:
        if driver:
            driver.quit()
            logger.debug(f"WebDriver quit for justice.cz for ICO: {ico}")
            


def _parse_int_or_none(text_content: str):
    """Safely parses a string to an int, returning None on failure."""
    if text_content:
        try:
            return int(text_content.strip())
        except ValueError:
            return None
    return None

def _parse_member_details(role_text: str, member_value_container: BeautifulSoup):
    """
    Parses the details of a statutory/supervisory board member or prokurist.
    The member_value_container is the <div> cell that directly contains the member's info.
    """
    if not member_value_container:
        return None

    member_data = {
        "role": role_text.strip(': '),
        "jmeno_prijmeni": None,
        "datum_narozeni": None,
        "adresa": None,
        "den_vzniku_funkce": None,
        "den_vzniku_clenstvi": None
    }

    # The details are usually within a top-level <span> or <div> inside the value container
    details_wrapper = member_value_container.find(['span', 'div'], recursive=False)
    if not details_wrapper: # If still nothing, use the container itself
        details_wrapper = member_value_container

    # Details are often in a series of <div> elements under the wrapper
    # Or sometimes directly as text nodes and spans
    
    # Attempt to find name and birth date (often together)
    name_birth_elements = []
    address_elements = []
    funkce_date_elements = []
    clenstvi_date_elements = []

    # Heuristic parsing based on observed structure
    # Children can be <div>s or <span>s or text nodes
    current_block_divs = details_wrapper.find_all('div', recursive=False)
    if not current_block_divs: # If no divs, maybe it's a flat structure of spans
        current_block_divs = [details_wrapper] # Treat the wrapper as the block

    for block_div_idx, block_div in enumerate(current_block_divs):
        texts = [s.strip() for s in block_div.get_text(separator='|').split('|') if s.strip()]
        full_block_text = " ".join(texts)

        if not member_data["jmeno_prijmeni"] and any(kw in t.lower() for kw in ["dat. nar.", "nar."] for t in texts):
            name_parts = []
            for t_idx, t in enumerate(texts):
                if "dat. nar." in t.lower() or "nar." in t.lower():
                    member_data["datum_narozeni"] = texts[t_idx + 1] if t_idx + 1 < len(texts) else None
                    # Clean up datum_narozeni if it got extra parts
                    if member_data["datum_narozeni"] and "," in member_data["datum_narozeni"]:
                        member_data["datum_narozeni"] = member_data["datum_narozeni"].split(",")[0].strip()
                    break
                name_parts.append(t)
            member_data["jmeno_prijmeni"] = " ".join(name_parts).replace(",","").strip()
        
        elif not member_data["adresa"] and block_div_idx > 0 and not any(kw in full_block_text for kw in ["Den vzniku funkce", "Den vzniku členství"]):
             # Assume address if it's not name/birth and not a date line, and often after the first block
            address_text_candidate = block_div.get_text(separator=" ", strip=True)
            # Filter out if it looks like a date line by mistake
            if not ("Den vzniku funkce" in address_text_candidate or "Den vzniku členství" in address_text_candidate):
                 member_data["adresa"] = address_text_candidate

        if "Den vzniku funkce:" in full_block_text:
            member_data["den_vzniku_funkce"] = full_block_text.replace("Den vzniku funkce:", "").strip()
        if "Den vzniku členství:" in full_block_text:
            member_data["den_vzniku_clenstvi"] = full_block_text.replace("Den vzniku členství:", "").strip()

    # Fallback for name if not found with birth date
    if not member_data["jmeno_prijmeni"] and current_block_divs:
        first_block_texts = [s.strip() for s in current_block_divs[0].get_text(separator='|').split('|') if s.strip()]
        if first_block_texts:
            # Assume the first significant text before any "dat. nar." is the name
            potential_name = []
            for t in first_block_texts:
                if "dat. nar." in t.lower(): break
                potential_name.append(t)
            if potential_name:
                member_data["jmeno_prijmeni"] = " ".join(potential_name).replace(",","").strip()
    
    # Clean up None values if they are empty strings
    for key, value in member_data.items():
        if isinstance(value, str) and not value.strip():
            member_data[key] = None
            
    return member_data

def scrape_justice_data(html_content: str):
    """
    Parses HTML content from justice.cz to extract company information.
    Returns a list containing one dictionary with the scraped data.
    The dictionary structure matches _get_default_justice_structure() for empty/error states.
    """
    # Initialize data structure - this should be the "expanded" version initially
    data = {
        "obchodni_firma": None,
        "sídlo": {"adresa_kompletni": None},
        "identifikacni_cislo": None,
        "pravni_forma": None,
        "datum_vzniku_a_zapisu": None,
        "spisova_znacka": None,
        "predmet_podnikani": [],
        "statutarni_organ_predstavenstvo": { # Initialize expanded
            "clenove": [], "pocet_clenu": None, "zpusob_jednani": None
        },
        "dozorci_rada": { # Initialize expanded
            "clenove": [], "pocet_clenu": None
        },
        "prokura": { # Initialize expanded
            "prokuriste": [], "zpusob_podepisovani": None
        },
        "jediny_akcionar": { # Initialize expanded
            "nazev": None, "ic": None, "adresa": None
        },
        "akcie": [],
        "zakladni_kapital": None,
        "splaceno": None,
        "ostatni_skutecnosti": [],
    }
    current_section_context = None

    soup = BeautifulSoup(html_content, 'html.parser')
    content_area = soup.find("div", class_="section-c vypis-c")
    if not content_area:
        logger.warning("Main content area 'div.section-c.vypis-c' not found in HTML.")
        return [data] # Return initial data structure with mostly None values

    all_panels = content_area.find_all("div", class_="aunp-udajPanel")
    
    for panel in all_panels:
        label_text = ""
        value_container = None # The BeautifulSoup tag of the value cell/area
        
        # Attempt to find the main table within the panel
        panel_div_table = panel.find("div", class_="div-table", recursive=False)

        if panel_div_table:
            first_row = panel_div_table.find("div", class_="div-row", recursive=False)
            if first_row:
                cells = first_row.find_all("div", class_="div-cell", recursive=False)
                if cells: # Ensure cells were found
                    first_cell_classes = cells[0].get("class", [])
                    
                    # Path 1: Standard label cell (e.g., class "w45mm" in first cell, not colspan)
                    if "w45mm" in first_cell_classes and not cells[0].get("colspan"):
                        label_hlavicka_div = cells[0].find("div", class_="vr-hlavicka")
                        if label_hlavicka_div:
                            label_text = label_hlavicka_div.get_text(separator=" ", strip=True)
                        if len(cells) > 1:
                            value_container = cells[1] # Value is in the second cell
                    
                    # Path 2: Label cell spans multiple columns (colspan="2")
                    elif cells[0].get("colspan") == "2":
                        label_hlavicka_div = cells[0].find("div", class_="vr-hlavicka")
                        if label_hlavicka_div:
                            label_text = label_hlavicka_div.get_text(separator=" ", strip=True)
                        
                        # If this colspan=2 label is for a member role (heuristic: ends with ':'),
                        # the actual member data is often in the *next row* of the *same panel's table*.
                        # _parse_member_details expects value_container to be that data cell.
                        if label_text.strip().endswith(':'): # Heuristic for member-like roles
                            all_rows_in_this_table = panel_div_table.find_all("div", class_="div-row", recursive=False)
                            if len(all_rows_in_this_table) > 1: # If there's a second row in this panel's table
                                member_data_row_cells = all_rows_in_this_table[1].find_all("div", class_="div-cell", recursive=False)
                                # Member data is typically in the second cell of this data row
                                if len(member_data_row_cells) > 1:
                                    value_container = member_data_row_cells[1]
                                elif len(member_data_row_cells) == 1: # Or if data is in a single cell in the next row
                                    value_container = member_data_row_cells[0]
                        # For other colspan=2 headers (e.g., section titles), value_container remains None by default here.
                        # generic_value_text (calculated below) will be "" if value_container is None.
                        # If the text of cells[0] itself is needed as a value for a colspan=2 header,
                        # that would require specific handling later based on clean_label,
                        # potentially using label_text as the source if generic_value_text is empty.
        
        # Calculate generic_value_text based on the determined value_container
        generic_value_text = value_container.get_text(separator=" ", strip=True) if value_container else ""
        clean_label = label_text.lower().strip(':').strip()

        # --- Direct field extraction ---
        if clean_label == "datum vzniku a zápisu":
            data["datum_vzniku_a_zapisu"] = generic_value_text
            current_section_context = None
        elif clean_label == "spisová značka":
            data["spisova_znacka"] = generic_value_text
            current_section_context = None
        elif clean_label == "obchodní firma":
            data["obchodni_firma"] = generic_value_text
            current_section_context = None
        elif clean_label == "sídlo":
            if value_container: # Sídlo has a specific span structure
                sidlo_span = value_container.find("span") # find the first span
                if sidlo_span:
                     # Get text from all children of this span, including nested ones
                    data["sídlo"]["adresa_kompletni"] = sidlo_span.get_text(separator=" ", strip=True)
                else: # Fallback
                    data["sídlo"]["adresa_kompletni"] = generic_value_text
            current_section_context = None
        elif clean_label == "identifikační číslo":
            if value_container:
                # Remove internal spans used for spacing if any, then join parts
                id_text = "".join(value_container.find_all(string=True, recursive=True)).replace(" ", "").strip()
                data["identifikacni_cislo"] = id_text
            else:
                data["identifikacni_cislo"] = generic_value_text.replace(" ", "")
            current_section_context = None
        elif clean_label == "právní forma":
            data["pravni_forma"] = generic_value_text
            current_section_context = None

        # --- Section Starters ---
        elif clean_label == "předmět podnikání":
            current_section_context = "predmet_podnikani"
            # Value might be on the same line as the header or in subsequent panels
            if generic_value_text: 
                data["predmet_podnikani"].append(generic_value_text)
        elif clean_label == "statutární orgán - představenstvo":
            current_section_context = "statutarni_organ_predstavenstvo"
            # data["statutarni_organ_predstavenstvo"] is already initialized
        elif clean_label == "dozorčí rada":
            current_section_context = "dozorci_rada"
        elif clean_label == "prokura":
            current_section_context = "prokura"
        elif clean_label == "jediný akcionář":
            current_section_context = "jediny_akcionar"
            # Data for J.A. is usually in the next panel with an empty label
            # If there's text here, it might be part of the name.
            if generic_value_text and not data["jediny_akcionar"]["nazev"]:
                data["jediny_akcionar"]["nazev"] = generic_value_text 
        elif clean_label == "akcie":
            current_section_context = "akcie"
            if generic_value_text: # First share description might be here
                data["akcie"].append({"popis_akcie": generic_value_text, "podminky_prevodu": None})
        elif clean_label == "základní kapitál":
            current_section_context = None # This section is self-contained
            if value_container:
                all_divs_in_value = value_container.find_all("div", recursive=False)
                if all_divs_in_value:
                    data["zakladni_kapital"] = all_divs_in_value[0].get_text(separator=" ", strip=True)
                    if len(all_divs_in_value) > 1:
                        splaceno_text_full = all_divs_in_value[1].get_text(separator=" ", strip=True)
                        if "splaceno:" in splaceno_text_full.lower():
                            data["splaceno"] = splaceno_text_full.lower().replace("splaceno:", "").strip()
                        elif '%' in splaceno_text_full : # Heuristic if "Splaceno:" is missing
                             data["splaceno"] = splaceno_text_full.strip()
                else: # Fallback if no inner divs
                    text_content = value_container.get_text(separator=" ", strip=True)
                    if "splaceno:" in text_content.lower():
                        parts = re.split(r'splaceno:', text_content, flags=re.IGNORECASE)
                        data["zakladni_kapital"] = parts[0].strip()
                        if len(parts) > 1: data["splaceno"] = parts[1].strip()
                    else:
                        data["zakladni_kapital"] = text_content
            else:
                 data["zakladni_kapital"] = generic_value_text # Might contain splaceno

        elif clean_label == "ostatní skutečnosti":
            current_section_context = "ostatni_skutecnosti"
            if generic_value_text:
                data["ostatni_skutecnosti"].append(generic_value_text)
        
        # --- Handling items within a context (continuation or sub-items) ---
        elif current_section_context:
            # This 'elif' means clean_label is not a main section starter.
            # It could be an empty label (continuation) or a sub-label (member role, Počet členů).

            if current_section_context == "predmet_podnikani":
                if not clean_label and generic_value_text: # Continuation item
                    data["predmet_podnikani"].append(generic_value_text)
            
            elif current_section_context == "statutarni_organ_predstavenstvo":
                member_roles = ["předseda představenstva", "místopředseda představenstva", "člen představenstva"]
                if clean_label in member_roles:
                    member_details = _parse_member_details(label_text, value_container)
                    if member_details: data["statutarni_organ_predstavenstvo"]["clenove"].append(member_details)
                elif clean_label == "počet členů":
                    data["statutarni_organ_predstavenstvo"]["pocet_clenu"] = _parse_int_or_none(generic_value_text)
                elif clean_label == "způsob jednání":
                    data["statutarni_organ_predstavenstvo"]["zpusob_jednani"] = generic_value_text
            
            elif current_section_context == "dozorci_rada":
                member_roles = ["předseda dozorčí rady", "místopředseda dozorčí rady", "člen dozorčí rady"]
                if clean_label in member_roles:
                    member_details = _parse_member_details(label_text, value_container)
                    if member_details: data["dozorci_rada"]["clenove"].append(member_details)
                elif clean_label == "počet členů":
                    data["dozorci_rada"]["pocet_clenu"] = _parse_int_or_none(generic_value_text)

            elif current_section_context == "prokura":
                # Prokurists are often labeled "prokurista:"
                if clean_label == "prokurista":
                    prokurist_raw_details = _parse_member_details(label_text, value_container)
                    if prokurist_raw_details:
                        data["prokura"]["prokuriste"].append({
                            "jmeno_prijmeni": prokurist_raw_details.get("jmeno_prijmeni"),
                            "datum_narozeni": prokurist_raw_details.get("datum_narozeni"),
                            "adresa": prokurist_raw_details.get("adresa")
                        })
                elif clean_label == "způsob podepisování" or clean_label == "způsob jednání prokuristů":
                    data["prokura"]["zpusob_podepisovani"] = generic_value_text
            
            elif current_section_context == "jediny_akcionar":
                if not clean_label and value_container: # Data is in the panel with empty label
                    nazev_text = None
                    ic_text = None
                    adresa_text = None
                    
                    # Heuristic parsing for J.A. details
                    # Example: <span>NAME</span>, IČ: <a>IC_NUM</a> <div>ADDRESS</div>
                    # Or just <span>NAME</span>
                    
                    all_strings = [s.strip() for s in value_container.get_text(separator='|').split('|') if s.strip()]
                    full_text_blob = " ".join(all_strings)

                    # Try to find IČ
                    ic_match = re.search(r"IČ:\s*([\d\s]+)", full_text_blob, re.IGNORECASE)
                    if ic_match:
                        ic_text = ic_match.group(1).replace(" ", "")
                        # Name is usually before IČ
                        nazev_text = full_text_blob.split(ic_match.group(0))[0].strip(',').strip()
                    else: # No IČ found, assume the first part is name
                        if all_strings:
                             nazev_text = all_strings[0].strip(',').strip()


                    # Address is often in a separate div or the last part
                    address_div = value_container.find("div", recursive=True) # Find any div for address
                    if address_div:
                        adresa_text = address_div.get_text(separator=" ", strip=True)
                        # If name was part of address_div's text, try to remove it
                        if nazev_text and adresa_text and adresa_text.startswith(nazev_text):
                            adresa_text = adresa_text[len(nazev_text):].strip(',').strip()
                    elif not ic_text and len(all_strings) > 1: # If no IC and multiple strings, last might be address
                        # This is very speculative
                        potential_address = " ".join(all_strings[1:])
                        if len(potential_address) > 10 : # Arbitrary length to guess it's an address
                             adresa_text = potential_address


                    data["jediny_akcionar"]["nazev"] = nazev_text if nazev_text else data["jediny_akcionar"]["nazev"]
                    data["jediny_akcionar"]["ic"] = ic_text
                    data["jediny_akcionar"]["adresa"] = adresa_text
                    # current_section_context = None # J.A. is usually one item, but could have other related facts. Let main labels reset.

            elif current_section_context == "akcie":
                if not clean_label and value_container: # Continuation item for shares
                    popis_akcie_text = ""
                    podminky_prevodu_text = None

                    share_divs = value_container.find_all("div", recursive=False)
                    if share_divs:
                        # First div is usually the share description
                        popis_akcie_text = ' '.join(share_divs[0].find_all(string=True, recursive=True)).strip()
                        # Second div (if exists) is often transfer conditions
                        if len(share_divs) > 1:
                            podminky_prevodu_text = ' '.join(share_divs[1].find_all(string=True, recursive=True)).strip()
                            if not podminky_prevodu_text: podminky_prevodu_text = None
                    elif generic_value_text: # Fallback if no inner divs
                         popis_akcie_text = generic_value_text
                    
                    if popis_akcie_text:
                        data["akcie"].append({"popis_akcie": popis_akcie_text, "podminky_prevodu": podminky_prevodu_text})

            elif current_section_context == "ostatni_skutecnosti":
                if not clean_label and generic_value_text: # Continuation item
                    data["ostatni_skutecnosti"].append(generic_value_text)
        # else:
            # This panel didn't match any known label or active context.
            # Could be an unexpected structure or an ended section.
            # current_section_context = None # Cautiously reset if label is not empty.

    # Final clean-up for lists that might have empty strings if logic was imperfect
    data["predmet_podnikani"] = [item for item in data["predmet_podnikani"] if item and item.strip()]
    data["ostatni_skutecnosti"] = [item for item in data["ostatni_skutecnosti"] if item and item.strip()]
    data["akcie"] = [item for item in data["akcie"] if item.get("popis_akcie","").strip()]
    
    # Clean up empty member/prokurist lists if they were initialized but nothing added
    if not data["statutarni_organ_predstavenstvo"]["clenove"] and \
       not data["statutarni_organ_predstavenstvo"]["pocet_clenu"] and \
       not data["statutarni_organ_predstavenstvo"]["zpusob_jednani"]:
        data["statutarni_organ_predstavenstvo"] = None # Consistent with _get_default_justice_structure

    if not data["dozorci_rada"]["clenove"] and not data["dozorci_rada"]["pocet_clenu"]:
        data["dozorci_rada"] = None # Consistent

    if not data["prokura"]["prokuriste"] and not data["prokura"]["zpusob_podepisovani"]:
        data["prokura"] = None # Consistent
        
    if data["jediny_akcionar"] and \
       not data["jediny_akcionar"]["nazev"] and \
       not data["jediny_akcionar"]["ic"] and \
       not data["jediny_akcionar"]["adresa"]:
        data["jediny_akcionar"] = None # Consistent


    return [data]

def get_justice_data(ico: str):
    """
    Fetches and parses justice.cz data for a given ICO.
    Always returns a list containing a single dictionary with the full data structure.
    In case of errors or no data, the dictionary will contain default (None or empty) values.
    """
    logger.info(f"Fetching justice data for ICO: {ico}")
    default_structure = _get_default_justice_structure()

    html_content = get_justice_info_by_ico(ico)
    if not html_content:
        logger.warning(f"Failed to load source HTML for ICO {ico} from justice.cz. Returning default structure.")
        return [default_structure.copy()]

    logger.info(f"Parsing justice data using BeautifulSoup for ICO: {ico}")
    try:
        parsed_data_list = scrape_justice_data(html_content) # Expected to return [dict_with_full_structure]

        if not parsed_data_list or not isinstance(parsed_data_list, list) or \
           len(parsed_data_list) == 0 or not isinstance(parsed_data_list[0], dict):
            logger.error(f"scrape_justice_data returned an unexpected result for ICO {ico}: {parsed_data_list}. Returning default structure.")
            return [default_structure.copy()]
        
        # Log if primary identifiers are missing, suggesting no real data was found
        # scrape_justice_data itself will return the structure with None values if parsing fails for sections.
        actual_data = parsed_data_list[0]
        if actual_data.get("obchodni_firma") is None and actual_data.get("spisova_znacka") is None:
            logger.info(f"Justice data for ICO {ico}: Key identifiers (obchodni_firma, spisova_znacka) are missing. Data might be incomplete or not found.")
        
        return parsed_data_list # This is [actual_data_dict]

    except Exception as e:
        logger.error(f"Exception during BeautifulSoup parsing or data processing for ICO {ico}: {e}", exc_info=True)
        return [default_structure.copy()]

# 5. Main execution
if __name__ == "__main__":
    # Basic logging configuration for standalone script execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    

    example_subjekt_id = '63474808' # Example: VÍTKOVICE, a.s.


    logger.info(f"--- Standalone Test for justice_info.py with subjektId: {example_subjekt_id} ---")
    
    data_list = get_justice_data(example_subjekt_id) # Call the new wrapper
    
    if data_list and isinstance(data_list, list) and len(data_list) > 0:
        result_data = data_list[0]
        if "error" in result_data:
            logger.error(f"Error fetching justice data: {result_data['error']}")
        else:
            logger.info("\n--- Scraped JSON Data (from get_justice_data) ---")
            # Still print JSON to stdout for standalone test output, or log it
            print(json.dumps(result_data, indent=2, ensure_ascii=False))
            # logger.info(f"Scraped data:\n{json.dumps(result_data, indent=2, ensure_ascii=False)}")


            # Optionally, save to a file for testing
            try:
                with open(f"extracted_data_scraped_{example_subjekt_id}.json", "w", encoding="utf-8") as outfile:
                    json.dump(result_data, outfile, indent=2, ensure_ascii=False)
                logger.info(f"Successfully saved scraped data to extracted_data_scraped_{example_subjekt_id}.json")
            except IOError as e:
                logger.error(f"Failed to save data to file: {e}", exc_info=True)

    else:
        logger.error("Failed to scrape data or no data was returned by get_justice_data.")

   