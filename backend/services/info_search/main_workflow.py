import argparse
import json
from concurrent.futures import ThreadPoolExecutor
import logging
from backend.services.info_search.justice_info import get_justice_data
from backend.services.info_search.dph_info import get_dph_info
from backend.services.info_search.dotace import scrape_dotace
from backend.services.info_search.company_analyzer import analyze_company_data

# Configure logger for this module
logger = logging.getLogger(__name__)

def collect_all_info_data(ico: str):
    """
    Collects data from various sources for a given ICO concurrently.
    Ensures a predictable structure for each data source in the final result.
    """
    final_result = {}
    logger.info(f"Starting data collection for ICO: {ico}")

    # Define default structures for fallback and logging checks
    default_justice_structure = {
        "obchodni_firma": None, "sídlo": {"adresa_kompletni": None}, "identifikacni_cislo": None,
        "pravni_forma": None, "datum_vzniku_a_zapisu": None, "spisova_znacka": None,
        "predmet_podnikani": [], "statutarni_organ_predstavenstvo": None,
        "dozorci_rada": None, "prokura": None, "jediny_akcionar": None,
        "akcie": [], "zakladni_kapital": None, "splaceno": None, "ostatni_skutecnosti": []
    }
    default_dph_structure = {"nespolehlivy_platce": None, "registrace_od_data": None}
    default_dotace_structure = {"uvolnena": None}
    default_web_search_analysis_structure = {"name": None, "summary": None}

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_justice = executor.submit(get_justice_data, ico)
        future_dph = executor.submit(get_dph_info, ico)
        future_dotace = executor.submit(scrape_dotace, ico)
        future_web_search = executor.submit(analyze_company_data, ico)

        # 1. Process Justice Information
        logger.info(f"Submitting task for Justice Ministry information for ICO: {ico}")
        try:
            justice_data_list = future_justice.result() # Expected: [dict_with_full_structure]
            if justice_data_list and isinstance(justice_data_list, list) and \
               len(justice_data_list) > 0 and isinstance(justice_data_list[0], dict):
                final_result["justice_info"] = justice_data_list[0]
                # Log if the data seems to be just the default empty state
                if not final_result["justice_info"].get("obchodni_firma") and \
                   not final_result["justice_info"].get("spisova_znacka"):
                    logger.info(f"Justice info for ICO {ico} appears to be default/empty. Check justice_info module logs for details.")
                else:
                    logger.info(f"Successfully processed Justice Ministry information for ICO: {ico}")
            else:
                logger.error(f"get_justice_data for ICO {ico} returned an unexpected structure: {justice_data_list}. Assigning default empty structure.")
                final_result["justice_info"] = default_justice_structure.copy()
        except Exception as e:
            logger.error(f"Exception during justice_info fetch for ICO {ico}: {str(e)}", exc_info=True)
            final_result["justice_info"] = default_justice_structure.copy()

        # 2. Process DPH Information
        logger.info(f"Submitting task for DPH (VAT) information for ICO: {ico}")
        try:
            dph_data = future_dph.result() # Expected: dict_with_full_structure
            if isinstance(dph_data, dict):
                final_result["dph_info"] = dph_data
                # Log if the data seems to be just the default empty state
                if dph_data.get("nespolehlivy_platce") is None and dph_data.get("registrace_od_data") is None:
                     # This check is a bit simplistic as one field could be legitimately None.
                     # dph_info.py logs more specifically if "Údaje o subjektu DPH" is not found.
                    logger.info(f"DPH info for ICO {ico} has all fields as None. Check dph_info module logs for details.")
                else:
                    logger.info(f"Successfully processed DPH information for ICO: {ico}")
            else:
                logger.error(f"get_dph_info for ICO {ico} returned an unexpected structure: {dph_data}. Assigning default empty structure.")
                final_result["dph_info"] = default_dph_structure.copy()
        except Exception as e:
            logger.error(f"Exception during dph_info fetch for ICO {ico}: {str(e)}", exc_info=True)
            final_result["dph_info"] = default_dph_structure.copy()

        # 3. Process Dotace (Subsidies) Information
        logger.info(f"Submitting task for Dotace (Subsidies) information for ICO: {ico}")
        try:
            dotace_data = future_dotace.result() # Expected: {"uvolnena": <float_or_None>}
            if isinstance(dotace_data, dict) and "uvolnena" in dotace_data:
                final_result["dotace_info"] = dotace_data
                if dotace_data.get("uvolnena") is not None:
                    logger.info(f"Successfully fetched Dotace information for ICO {ico}: {dotace_data['uvolnena']}")
                else: # uvolnena is None
                    logger.info(f"Dotace information for ICO {ico}: No subsidy data found or an issue occurred within scrape_dotace (uvolnena is None).")
            else:
                logger.warning(f"Unexpected data structure from scrape_dotace for ICO {ico}. Received: {dotace_data}. Setting dotace_info to default.")
                final_result["dotace_info"] = default_dotace_structure.copy()
        except Exception as e:
            logger.error(f"Exception occurred while fetching/processing dotace_info for ICO {ico}: {str(e)}", exc_info=True)
            final_result["dotace_info"] = default_dotace_structure.copy()

        # 4. Process Web Search Analysis (News, Sentiment, etc.)
        logger.info(f"Submitting task for Web Search Analysis for ICO: {ico}")
        try:
            web_search_result = future_web_search.result() # Expected: {"name": str|None, "summary": list|None}
            if isinstance(web_search_result, dict) and \
               "name" in web_search_result and "summary" in web_search_result:
                final_result["web_search_analysis"] = web_search_result
                company_name_from_analysis = web_search_result.get("name")
                summary_object = web_search_result.get("summary") # Can be None or a list

                if company_name_from_analysis and summary_object is not None: # Both name and summary (even if empty list) are present
                    logger.info(f"Successfully processed Web Search Analysis for ICO {ico} (Company: {company_name_from_analysis}). Summary generated.")
                elif company_name_from_analysis and summary_object is None: # Name found, but no summary
                    logger.warning(f"Web Search Analysis for ICO {ico} (Company: {company_name_from_analysis}) completed, but no summary was generated. This might be due to no news found or an issue in the analysis process. Check company_analyzer logs.")
                elif not company_name_from_analysis: # Name is None, summary will also be None as per analyze_company_data logic
                    logger.warning(f"Web Search Analysis for ICO {ico}: Could not retrieve company name via company_analyzer. No analysis performed. This might be due to an invalid ICO or issues with the external name lookup. Check company_analyzer logs.")
                # No explicit else, as the above conditions should cover valid outputs from analyze_company_data
            else:
                logger.error(f"analyze_company_data for ICO {ico} returned an unexpected structure: {web_search_result}. Assigning default empty structure.")
                final_result["web_search_analysis"] = default_web_search_analysis_structure.copy()
        except Exception as e:
            logger.error(f"Exception during Web Search Analysis task for ICO {ico}: {str(e)}", exc_info=True)
            final_result["web_search_analysis"] = default_web_search_analysis_structure.copy()
    
    logger.info(f"Data collection finished for ICO: {ico}")
    logger.info(f"Final result: {final_result}")
    return final_result

def main():
    # Configure basic logging for the application
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler() # Outputs to stderr by default
        ]
    )

    parser = argparse.ArgumentParser(description="Collect company information from various sources based on ICO.")
    parser.add_argument("ico", help="The IČO (company identification number) to search for.")
    args = parser.parse_args()
    
    ico_to_search = args.ico
    logger.info(f"Processing request for ICO: {ico_to_search}")
    
    all_company_data = collect_all_info_data(ico_to_search)
    
    # Print only the JSON to stdout for API friendliness
    print(json.dumps(all_company_data, indent=2, ensure_ascii=False))

    # File saving has been removed.
    # If you need to save for debugging, you can temporarily add it back here,
    # or rely on redirecting stdout from your API call.
    # For example, to save for debugging:
    # output_filename = f"combined_data_{ico_to_search}.json"
    # try:
    #     with open(output_filename, "w", encoding="utf-8") as outfile:
    #         json.dump(all_company_data, outfile, indent=2, ensure_ascii=False)
    #     logger.info(f"Successfully saved combined data to {output_filename} (for debugging)")
    # except IOError as e:
    #     logger.error(f"Error saving data to file {output_filename}: {e}", exc_info=True)


if __name__ == "__main__":
    main()
