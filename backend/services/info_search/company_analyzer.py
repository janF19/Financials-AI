#!/usr/bin/env python3
import argparse
import requests
import os
from typing import List, Dict, Optional, Any
from serpapi import GoogleSearch
from openai import OpenAI
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timezone
from dateutil import parser as dateutil_parser
import logging
from backend.config import settings
# Configuration - Replace with your actual API keys



logger = logging.getLogger(__name__)

def get_formatted_recent_articles_for_prompt(search_results_list: List[Dict[str, str]], count: int = 2) -> str:
    """
    Identifies the most recent articles from search results and formats them for the AI prompt.
    Ensures dates are consistently handled for correct sorting.
    """
    dated_articles = []

    for i, item in enumerate(search_results_list):
        date_str = item.get("date")
        if date_str:
            try:
                parsed_date = dateutil_parser.parse(date_str)
                
                # Ensure all dates are timezone-aware and in UTC for correct sorting
                if parsed_date.tzinfo is None or parsed_date.tzinfo.utcoffset(parsed_date) is None:
                    # Naive datetime: assume UTC
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                else:
                    # Aware datetime: convert to UTC
                    parsed_date = parsed_date.astimezone(timezone.utc)
                
                dated_articles.append({
                    "title": item.get("title", "N/A"),
                    "snippet": item.get("snippet", "N/A"),
                    "date_str": date_str, # Keep original date string for display
                    "parsed_date": parsed_date, # Use this for sorting (now consistently UTC aware)
                    "original_index": i + 1 # 1-based index for "Výsledek X"
                })
            except (ValueError, TypeError, OverflowError) as e:
                # print(f"Could not parse or convert date: {date_str} for item {i+1}. Error: {e}") # Optional debug
                continue # Skip if date is unparsable or problematic

    # Sort by parsed_date (UTC aware), most recent first
    try:
        dated_articles.sort(key=lambda x: x["parsed_date"], reverse=True)
    except TypeError as e:
        # This should be much less likely now, but good to keep as a fallback.
        print(f"Warning: Could not sort articles by date due to an unexpected comparison issue: {e}. Recent articles section might be incomplete or unsorted.")
        # Proceed with potentially unsorted or partially sorted if some dates were uncomparable

    recent_articles_prompt_text = ""
    if dated_articles:
        recent_articles_prompt_text += "\n\nKromě toho věnujte zvláštní pozornost těmto nejnovějším zprávám (seřazeným od nejnovějších, pokud je to možné) a začleňte jejich klíčové poznatky, zejména do bodu o nejnovějších událostech. Uveďte, že se jedná o nejnovější zprávy:\n"
        for article_info in dated_articles[:count]:
            snippet_preview = article_info['snippet']
            if len(snippet_preview) > 200: # Truncate snippet for prompt brevity
                snippet_preview = snippet_preview[:197] + "..."
            
            recent_articles_prompt_text += (
                f"- Nejnovější zpráva (původně Výsledek {article_info['original_index']}): "
                f"\"{article_info['title']}\" (Publikováno: {article_info['date_str']}). "
                f"Úryvek: \"{snippet_preview}\"\n"
            )
    return recent_articles_prompt_text

def get_company_name_by_ico(ico: str) -> dict[str, str] | None:
    """
    Translates a company IČO to its name by scraping the justice.cz website using Selenium.
    This version is quieter and reduces terminal output on errors.

    Args:
        ico: The company identification number (IČO) as a string.

    Returns:
        A dictionary with 'name' and 'ico' if found, otherwise None.
    """
    url = "https://or.justice.cz/ias/ui/rejstrik-$firma"

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = None
    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.set_page_load_timeout(60)
        driver.get(url)

        ico_input_selector_id = "id3"
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, ico_input_selector_id))
        )
        ico_input_element = driver.find_element(By.ID, ico_input_selector_id)
        ico_input_element.send_keys(ico)
        # print(f"Filled IČO {ico} into input field.") # Debug print removed

        search_button_xpath = "//p[@class='search-buttons']//button[normalize-space(.//span)='Vyhledat']"
        # print(f"Waiting for search button with XPath: {search_button_xpath}") # Debug print removed
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, search_button_xpath))
        )
        search_button = driver.find_element(By.XPATH, search_button_xpath)
        # print("Search button found and clickable.") # Debug print removed
        search_button.click()
        # print(f"Clicked search button for IČO {ico}.") # Debug print removed

        result_table_selector_class = "result-details"
        # print(f"Waiting for result table with class '{result_table_selector_class}'...") # Debug print removed
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, result_table_selector_class))
        )
        # print("Result table found.") # Debug print removed

        company_name_xpath = '//table[@class="result-details"]//th[normalize-space(text())="Název subjektu:"]/following-sibling::td/strong[@class="left"]'
        company_name_element = driver.find_element(By.XPATH, company_name_xpath)
        company_name = company_name_element.text
        return {"name": company_name.strip(), "ico": ico}

    except TimeoutException:
        # Quieter error logging: removed page source dump
        print(f"Timeout (get_company_name_by_ico): Could not find company details for IČO {ico}. The IČO might be invalid or the page structure changed.")
        # if driver: # Page source print removed to reduce terminal flood
            # print("Page source at the time of timeout (first 5000 chars):")
            # print(driver.page_source[:5000])
        return None
    except NoSuchElementException:
        print(f"Element not found (get_company_name_by_ico): Could not find company details for IČO {ico}. Page structure might have changed.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in get_company_name_by_ico for IČO {ico}: {e}")
        return None
    finally:
        if driver:
            driver.quit()


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Analyze company data by IČO and generate an AI summary.")
    parser.add_argument("ico", help="Company IČO (Identifikační číslo osoby)")
    return parser.parse_args()

def perform_search(query: str, num_results: int = 15) -> List[Dict[str, str]]:
    """Perform a news search for a company using SerpApi and return results."""
    params = {
        "q": query,
        "engine": "google",
        "tbm": "nws",
        "num": str(num_results),
        "api_key": settings.SERPAPI_API_KEY
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    
    search_results = []
    if "news_results" in results:
        for item in results["news_results"][:num_results]:
            search_results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "date": item.get("date", "")
            })
    elif "organic_results" in results: # Fallback
        for item in results["organic_results"][:num_results]:
            search_results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "date": item.get("date", "")
            })
    return search_results

def extract_content(search_results: List[Dict[str, str]]) -> str:
    """Extract and format content from search results, including dates."""
    formatted_content = ""
    for i, result in enumerate(search_results, 1):
        formatted_content += f"Result {i}:\n"
        formatted_content += f"Title: {result['title']}\n"
        formatted_content += f"URL: {result['link']}\n"
        if result.get('date'):
            formatted_content += f"Date: {result['date']}\n"
        formatted_content += f"Snippet: {result['snippet']}\n\n"
    return formatted_content

def generate_ai_summary(company_name: str, search_content: str, recent_articles_prompt_addition: str = "") -> Optional[str]:
    """Generate an AI summary about a company based on news search results."""
    if not search_content.strip() and not recent_articles_prompt_addition.strip(): # If no content at all
        return "Nebyly nalezeny žádné relevantní informace pro generování shrnutí."

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    prompt = f"""
    Na základě následujících výsledků vyhledávání zpráv o společnosti "{company_name}" uveďte shrnutí, které se zabývá těmito body:
    1. Jaké jsou nejnovější významné zprávy nebo události týkající se této společnosti? (Uveďte data, pokud jsou k dispozici ve výsledcích vyhledávání)
    2. Existují nějaké náznaky pozitivního vývoje, úspěchů nebo expanze?
    3. Existují nějaké zprávy o problémech, kontroverzích, stížnostech nebo negativním sentimentu kolem společnosti? Pokud ano, shrňte je.
    4. Jaké jsou hlavní činnosti nebo oblasti zaměření společnosti, jak se odrážejí v nedávných zprávách?
    5. Další důležité informace pro posouzení finančního zdraví (pokud jsou ve výsledcích náznaky).
    6. Další důležité informace nebo pozorování.
    {recent_articles_prompt_addition}
    Výsledky vyhledávání (s časovými značkami, pokud jsou k dispozici):
    {search_content}

    Poskytněte stručné shrnutí ke každé otázce založené *pouze* na informacích dostupných v těchto výsledcích vyhledávání (včetně speciálně zvýrazněných nejnovějších zpráv).
    Při odkazování na konkrétní informace z výsledků vyhledávání uveďte číslo výsledku v závorce, například (Výsledek 1) nebo (Výsledky 2, 3).
    Odpovězte jasně strukturovaně formou až šesti očíslovaných bodů (1. ..., 2. ..., atd.).
    Pokud pro některý bod nebudou nalezeny žádné konkrétní informace, uveďte to v rámci daného bodu.
    Odpovězte prosím v českém jazyce.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Jste užitečný asistent, který analyzuje výsledky vyhledávání zpráv týkajících se společností a poskytuje faktická shrnutí v českém jazyce, strukturovaná do několika očíslovaných bodů (maximálně 6). Při použití informací z konkrétního výsledku vyhledávání uveďte jeho číslo, např. (Výsledek 1)."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

def analyze_company_data(company_ico_str: str) -> Dict[str, Optional[Any]]:
    """
    Analyzes company data based on IČO.
    Retrieves company name, searches for news, and generates an AI summary.

    Args:
        company_ico_str: The company IČO as a string.

    Returns:
        A dictionary with "name" (company name or None) and 
        "summary" (list of AI summary strings with embedded links, or None).
    """
    logger.info(f"Starting company analysis for ICO: {company_ico_str}")

    if len(company_ico_str) != 8 or not company_ico_str.isdigit():
        logger.warning(f"Invalid ICO format: {company_ico_str}. Must be 8 digits.")
        return {"name": None, "summary": None}
        
    
    company_info = get_company_name_by_ico(company_ico_str)

    if not company_info or not company_info.get("name"):
        # get_company_name_by_ico already prints its specific error
        logger.warning(f"Could not retrieve company name for ICO: {company_ico_str}. Analysis aborted.")
        return {"name": None, "summary": None}

    company_name = company_info["name"]
    
    search_results: List[Dict[str, str]] = []
    try:
        logger.debug(f"Performing news search for: {company_name}")
        search_results = perform_search(company_name) 
    except requests.exceptions.RequestException as e: # Catch network/request related errors
        logger.error(f"Error during news search for {company_name} (ICO: {company_ico_str}): {e}", exc_info=True)
        # Company name is known, but search failed.
        return {"name": company_name, "summary": None}

    if not search_results:
        # This case is if perform_search ran successfully but returned no results
        logger.info(f"No news search results found for {company_name} (ICO: {company_ico_str}).")
        return {"name": company_name, "summary": None}
    
    logger.debug(f"Extracting content from search results for {company_name}")
    search_content = extract_content(search_results)
    
    # Prepare information about recent articles for the prompt
    recent_articles_prompt_addition = get_formatted_recent_articles_for_prompt(search_results)
    
    logger.debug(f"Generating AI summary for {company_name}")
    ai_summary_str = generate_ai_summary(company_name, search_content, recent_articles_prompt_addition)
    
    if not ai_summary_str:
        # generate_ai_summary prints its own error if OpenAI API call fails
        logger.warning(f"AI summary generation failed for {company_name} (ICO: {company_ico_str}).")
        return {"name": company_name, "summary": None}

    # Parse AI summary string into a list of points
    parsed_summary_points = []
    raw_summary_lines = ai_summary_str.strip().splitlines()
    current_point_lines = []
    for line in raw_summary_lines:
        stripped_line = line.strip()
        if re.match(r"^\d+\.\s+", stripped_line): # Starts a new numbered point
            if current_point_lines: # Save previous point
                parsed_summary_points.append(" ".join(current_point_lines).strip())
            current_point_lines = [re.sub(r"^\d+\.\s*", "", stripped_line, count=1)] # Start new, remove prefix, fix DeprecationWarning
        elif current_point_lines: # Continuation of the current point
            current_point_lines.append(stripped_line)
    if current_point_lines: # Add the last collected point
        parsed_summary_points.append(" ".join(current_point_lines).strip())

    if not parsed_summary_points and ai_summary_str: # Check ai_summary_str to avoid logging if it was empty initially
        logger.warning(f"Could not parse AI summary into distinct points for {company_name}. Returning raw summary.")
        return {"name": company_name, "summary": [ai_summary_str]}

    # Embed links into summary points
    processed_summary_points_with_links = []

    def link_replacer_callback(match_obj):
        full_match_text = match_obj.group(0) # The whole matched text e.g., "(Výsledek 6)" or "Výsledek 6"
        # Group 1: Optional opening parenthesis
        # Group 2: "Výsledek" or "Výsledky"
        # Group 3: The number(s) string e.g., "6" or "4, 5, 7, 9"
        # Group 4: Optional closing parenthesis
        
        keyword = match_obj.group(2) 
        numbers_str = match_obj.group(3)

        individual_numbers = []
        try:
            individual_numbers = [int(n.strip()) for n in numbers_str.split(',')]
        except ValueError:
            return full_match_text # Should not happen with the regex, but good practice

        source_details_parts = [] # To store "link [date]" or just "link"
        for num in individual_numbers:
            result_idx = num - 1 # Adjust for 0-based indexing
            if 0 <= result_idx < len(search_results):
                link = search_results[result_idx].get('link')
                date = search_results[result_idx].get('date') # Get the date
                
                if link:
                    detail_str = link
                    if date:
                        detail_str += f" (Datum: {date})" # Append date if available
                    source_details_parts.append(detail_str)
        
        if source_details_parts:
            links_display_str = ', '.join(source_details_parts)
            # Construct the text that was matched, without the optional parentheses
            core_reference_text = f"{keyword} {numbers_str}"
            
            # If original match had parentheses, keep them around the new text
            if match_obj.group(1) and match_obj.group(4): # Both ( and ) were present
                 return f"({core_reference_text} - Zdroje: {links_display_str})"
            else: # No parentheses or mismatched (regex tries to avoid mismatch)
                 return f"{core_reference_text} (Zdroje: {links_display_str})"
        else:
            return full_match_text # No links found for these numbers, return original text

    for point_text in parsed_summary_points:
        # Regex to find references like "Výsledek 6", "(Výsledek 6)", "Výsledky 4, 5, 9", "(Výsledky 4,5,9)"
        # It captures: (\()?\s*(Výsledek|Výsledky)\s*(\d+(?:\s*,\s*\d+)*)(\))?
        # Group 1: Optional opening parenthesis
        # Group 2: "Výsledek" or "Výsledky"
        # Group 3: The number(s) string e.g., "6" or "4, 5, 7, 9"
        # Group 4: Optional closing parenthesis
        processed_point = re.sub(
            r"(\()?\s*(Výsledek|Výsledky)\s*((?:\d+\s*,\s*)*\d+)\s*(\))?",
            link_replacer_callback,
            point_text
        )
        processed_summary_points_with_links.append(processed_point)
    
    return {"name": company_name, "summary": processed_summary_points_with_links}

def main():
    """
    Main function to handle command-line execution.
    """
    # Configure basic logging for standalone script execution if not already configured by a higher-level module
    # This is often good practice for scripts that can be run directly.
    if not logging.getLogger().hasHandlers(): # Check if root logger is already configured
        logging.basicConfig(
            level=logging.INFO, # Or logging.DEBUG for more verbose output
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )

    args = parse_arguments()
    company_ico_arg = args.ico
    
    # These print statements are for CLI feedback during standalone execution
    logger.info(f"Attempting to analyze company with IČO: {company_ico_arg} (standalone execution)...")

    result = analyze_company_data(company_ico_arg)
    
    
    
    
    logger.debug(f"Raw analysis result: {result}") # Use logger.debug for raw dict

    # Output the result
    # For programmatic use, you might just want `print(result)`
    # For CLI, a more formatted output is often better:
    if result["name"] is None: # Changed "ico" to "name"
        # Specific error messages would have been printed by get_company_name_by_ico or analyze_company_data
        logger.error(f"Critical error: Could not retrieve company name or other critical issue for IČO: {company_ico_arg}.")
        # print(f"Returned data: {result}") # Optionally print raw data on error
    elif result["summary"] is None:
        # Specific error messages (e.g. search failure, no results, AI summary failure) would have been printed
        logger.warning(f"Company: {result['name']} (IČO: {company_ico_arg}). No news summary could be generated or an error occurred.")
        # print(f"Returned data: {result}") # Optionally print raw data
    else:
        logger.info(f"\n=== Analysis for {result['name']} (IČO: {company_ico_arg}) ===") # Changed "ico" to "name"
        logger.info("\n--- AI SUMMARY ---")
        for point in result["summary"]:
            logger.info(f"- {point}") # Added a dash for better readability of points
        # If you want to print the raw dictionary as well for CLI:
        # print("\n--- Returned Data ---")
        # print(result)

if __name__ == "__main__":
    main()
    
    
    
#change it make it search for company using ICO and convert to name and then using that name search for new information in news
#some late events ect. make output, { "news": newsUptodate, "problems": "soome issue found with this compay online"}



