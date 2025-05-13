# backend/processors/workflow3.py
import logging
from pathlib import Path
# Removed OCRProcessor import
from backend.processors.financials.extractor3 import FinancialExtractor3 # Import V3 Extractor
from backend.processors.valuation.valuator2 import CompanyValuator2 # Reusing V2 Valuator for now
from backend.processors.reporting.generator2 import ReportGenerator2 # Reusing V2 Generator for now
from backend.config.settings import settings
import json
import os
import uuid
import shutil
from backend.storage.report_archive import save_report, cleanup_temp_file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ValuationWorkflow3:
    """
    Valuation workflow using Google Gemini for direct PDF processing (V3).
    """
    def __init__(self, keep_intermediate_files: bool = False):
        self.temp_dir_path = Path(settings.TEMP_STORAGE_PATH) / f"workflow_temp_v3_{uuid.uuid4()}" # Added v3 marker
        self.temp_dir_path.mkdir(parents=True, exist_ok=True)
        self.keep_intermediate_files = keep_intermediate_files
        logger.info(f"Temporary directory for V3 workflow created: {self.temp_dir_path}")
        if self.keep_intermediate_files:
            logger.info(f"Intermediate files in {self.temp_dir_path} will be preserved for this run.")

    def _cleanup_temp_dir(self):
        # Identical to V2 cleanup logic
        if self.temp_dir_path.exists():
            try:
                shutil.rmtree(self.temp_dir_path)
                logger.info(f"Successfully removed temporary directory tree: {self.temp_dir_path}")
            except Exception as e:
                logger.error(f"Error removing temporary directory tree {self.temp_dir_path}: {e}", exc_info=True)
        else:
            logger.info(f"Temporary directory {self.temp_dir_path} does not exist, no cleanup needed.")


    def execute(self, file_path: str, user_id: str = None, report_id: str = None, output_path: str = None):
        logger.info(f"Starting valuation workflow V3 for user: {user_id}, report: {report_id}")
        logger.info(f"Processing PDF document directly: {file_path}")

        # Define paths for intermediate files within the unique temp directory
        # No OCR HTML path needed
        financial_data_json_path = self.temp_dir_path / "financial_data_v3.json"
        valuation_json_path = self.temp_dir_path / "valuation_v3.json"

        all_data_for_report = {} # To hold combined data for the report generator

        try:
            # 1. Financial Data Extraction (using ExtractorV3 - Gemini)
            logger.info("Initializing Financial Extractor V3 (Gemini)...")
            # GOOGLE_API_KEY should be picked from settings/env by ExtractorV3
            if not ((settings and hasattr(settings, 'GOOGLE_API_KEY') and settings.GOOGLE_API_KEY) or os.environ.get("GOOGLE_API_KEY")):
                 logger.error("GOOGLE_API_KEY is not set or empty in settings or environment.")
                 raise ValueError("GOOGLE_API_KEY_MISSING", "Google API key is missing.")

            extractor = FinancialExtractor3()
            # ExtractorV3 takes the PDF path directly
            financial_and_analytical_data = extractor.extract_from_pdf(file_path)

            if not financial_and_analytical_data:
                # ExtractorV3 returns None on failure
                logger.error("Financial extractor V3 failed to return data.")
                raise ValueError("EXTRACTION_FAILED_V3", "Gemini financial data extraction failed.")

            # Save the extracted (and mapped) data
            with open(financial_data_json_path, "w", encoding="utf-8") as f:
                json.dump(financial_and_analytical_data, f, indent=4, ensure_ascii=False)
            logger.info(f"Financial and analytical data (V3) saved to {financial_data_json_path}")

            # Basic check if essential data sections are present after mapping
            if not financial_and_analytical_data.get('information') and \
               not financial_and_analytical_data.get('income_statement') and \
               not financial_and_analytical_data.get('balance_sheet'):
                logger.warning("Financial extractor V3 returned limited or no data in key sections.")
                # Decide if this is critical. For now, proceed.

            all_data_for_report.update(financial_and_analytical_data)
            # Add the path to the extracted JSON for potential use in the report
            all_data_for_report['financial_data_json_path'] = str(financial_data_json_path)


            # 2. Company Valuation (reusing ValuatorV2)
            logger.info("Initializing Company Valuator (V2 logic with V3 data)...")
            # ValuatorV2 expects the dictionary format produced by ExtractorV3's mapping function
            valuator = CompanyValuator2(financial_and_analytical_data)
            valuation_results = valuator.calculate_multiples() # Assuming this method still works

            with open(valuation_json_path, "w", encoding="utf-8") as f:
                json.dump(valuation_results, f, indent=4, ensure_ascii=False)
            logger.info(f"Valuation results (V3 workflow) saved to {valuation_json_path}")
            all_data_for_report['result_valuation'] = valuation_results


            # 3. Report Generation (reusing GeneratorV2)
            logger.info("Initializing Report Generator (V2 logic with V3 data)...")
            report_generator = ReportGenerator2()
            # GeneratorV2 needs to handle the structure of all_data_for_report from V3
            # It might need adjustments if it specifically looks for 'ocr_html_path' etc.
            # For now, assume it can work with the available keys.
            report_document = report_generator.generate(all_data_for_report)

            report_filename_base = f"report_v3_{report_id or uuid.uuid4()}" # Use v3 marker
            # Determine output path (same logic as V2)
            if output_path:
                p_output_path = Path(output_path)
                if p_output_path.is_dir():
                    temp_report_path = p_output_path / f"{report_filename_base}.docx"
                else:
                    temp_report_path = p_output_path
                    p_output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                temp_report_path = self.temp_dir_path / f"{report_filename_base}.docx"

            report_document.save(str(temp_report_path))
            logger.info(f"Report (V3) temporarily saved to {temp_report_path}")

            # 4. Save to Storage (if user_id and report_id are provided)
            report_url = None
            if user_id and report_id:
                original_filename = os.path.basename(file_path)
                try:
                    # Assuming save_report can handle is_v3 or uses a generic approach
                    report_url = save_report(user_id, temp_report_path, original_filename, report_id, is_v3=True) # Added is_v3 flag
                    logger.info(f"Report (V3) saved to Storage: {report_url}")
                except Exception as storage_error:
                    logger.error(f"Report (V3) storage failed: {str(storage_error)}")
                    raise ValueError("STORAGE_FAILED_V3", f"Failed to save report (V3) to storage: {str(storage_error)}") from storage_error
            else:
                report_url = str(temp_report_path.resolve())
                logger.info(f"Report (V3) available locally at: {report_url} (Storage upload skipped)")


            # Cleanup of original file is generally NOT done here, as it's the primary input.

            return {
                "report_url": report_url,
                "status": "success",
                "version": "3.0", # Version updated
                "intermediate_files": { # Updated intermediate files
                    # "ocr_html": None, # No OCR HTML
                    "financial_data_json": str(financial_data_json_path.resolve()),
                    "valuation_json": str(valuation_json_path.resolve()),
                    "final_report_path": str(temp_report_path.resolve())
                }
            }

        except ValueError as ve:
            error_category = ve.args[0] if len(ve.args) >= 1 else "VALIDATION_ERROR_V3"
            error_message = ve.args[1] if len(ve.args) >= 2 else str(ve)
            logger.error(f"Error in valuation workflow V3 ({error_category}): {error_message}", exc_info=True)
            return {"status": "failed", "error_category": error_category, "error_message": error_message, "version": "3.0"}
        except ImportError as ie: # Catch missing google package
             logger.error(f"Import error in valuation workflow V3: {str(ie)}", exc_info=True)
             return {"status": "failed", "error_category": "IMPORT_ERROR_V3", "error_message": str(ie), "version": "3.0"}
        except Exception as e:
            logger.error(f"Unexpected error in valuation workflow V3: {str(e)}", exc_info=True)
            return {"status": "failed", "error_category": "UNEXPECTED_ERROR_V3", "error_message": str(e), "version": "3.0"}
        finally:
            # Cleanup logic remains the same as V2, adapted for V3 paths
            if self.keep_intermediate_files:
                logger.info(f"KEEP_INTERMEDIATE_FILES is True. All files in temporary directory {self.temp_dir_path} will be preserved.")
            else:
                final_report_is_in_temp_dir = False
                # Use 'temp_report_path' which is defined within the try block if successful
                final_report_path_local = locals().get('temp_report_path')
                if final_report_path_local and final_report_path_local.exists():
                     try:
                         # Check if its parent is the temp_dir
                         if final_report_path_local.parent.resolve() == self.temp_dir_path.resolve():
                             final_report_is_in_temp_dir = True
                     except Exception:
                         pass # Path comparison failed

                # If error occurred before report path was set OR report is outside temp dir
                if not final_report_path_local or not final_report_is_in_temp_dir:
                    logger.info(f"Performing full cleanup of {self.temp_dir_path} (Report not generated/saved in temp dir, or error occurred).")
                    self._cleanup_temp_dir()
                else:
                    # Report IS in the temp dir, clean intermediates only
                    logger.info(f"Final report is in {self.temp_dir_path}. Performing selective cleanup.")
                    # Selectively clean intermediate files
                    if financial_data_json_path.exists() and financial_data_json_path != final_report_path_local:
                        cleanup_temp_file(financial_data_json_path)
                    if valuation_json_path.exists() and valuation_json_path != final_report_path_local:
                        cleanup_temp_file(valuation_json_path)
                    # Check if the directory is now empty except for the report
                    try:
                        remaining_items = list(self.temp_dir_path.iterdir())
                        if len(remaining_items) == 1 and remaining_items[0].resolve() == final_report_path_local.resolve():
                             logger.info(f"Only the final report remains in {self.temp_dir_path}.")
                        elif not remaining_items:
                             logger.info(f"Temporary directory {self.temp_dir_path} is empty after selective cleanup.")
                             self._cleanup_temp_dir() # Remove empty dir
                        else:
                             logger.info(f"Temporary directory {self.temp_dir_path} contains the final report and potentially other files.")
                    except Exception as list_err:
                         logger.warning(f"Could not list remaining items in temp dir for final check: {list_err}")


if __name__ == '__main__':
    # Placeholder for V3 test execution. Requires a real PDF and Google API Key.

    # Ensure settings.py has GOOGLE_API_KEY or it's set as an environment variable
    google_key_present = (settings and hasattr(settings, 'GOOGLE_API_KEY') and settings.GOOGLE_API_KEY) or os.environ.get("GOOGLE_API_KEY")
    if not google_key_present:
        print("Please set GOOGLE_API_KEY in your settings or environment for testing Workflow V3.")
    else:
        # --- MODIFICATION: Specify the path to your real PDF file ---
        # Use the same test file as before, assuming it's a PDF
        real_pdf_file_path = "./vz_2023_isotra.pdf" # <-- CHANGE THIS if needed
        if not Path(real_pdf_file_path).exists():
             print(f"Error: Test PDF file not found at {real_pdf_file_path}")
             exit()
        if not Path(real_pdf_file_path).suffix.lower() == ".pdf":
             print(f"Error: Input file {real_pdf_file_path} must be a PDF for Workflow V3.")
             exit()


        # Define an output directory for the report
        test_output_dir = Path("test_workflow_v3_output") # Changed output dir name
        test_output_dir.mkdir(parents=True, exist_ok=True)

        # Instantiate V3 workflow
        workflow_v3 = ValuationWorkflow3(keep_intermediate_files=True) # Keep files for inspection

        # Test case: Execute with local output path
        print("\n--- Test Case: Workflow V3 Local Output ---")
        # Set user_id/report_id to None to skip storage upload for this test
        test_report_id_v3 = str(uuid.uuid4()) # Generate a valid UUID if testing storage

        result_local_v3 = workflow_v3.execute(
            file_path=str(real_pdf_file_path),
            user_id=None, # Set to None to skip Supabase/Storage upload
            report_id=None, # Set to None to skip Supabase/Storage upload
            # user_id="test_user_v3", # Use these if testing storage
            # report_id=test_report_id_v3, # Use these if testing storage
            output_path=str(test_output_dir) # Save to local directory
        )
        print(f"Workflow V3 Result (Local): {json.dumps(result_local_v3, indent=2)}")
        if result_local_v3.get('status') == 'success':
            print(f"Report should be in: {result_local_v3.get('report_url')}")
            print(f"Intermediate files: {result_local_v3.get('intermediate_files')}")
        else:
            print(f"Workflow V3 failed. Error: {result_local_v3.get('error_category')} - {result_local_v3.get('error_message')}")

        # Note: For a full end-to-end test, you might need to mock Gemini API calls
        # or run against the actual service with a valid API key.
        # The `save_report` function in `report_archive.py` would need to handle `is_v3=True`.
        # The ValuatorV2 and ReportGeneratorV2 might need adjustments based on the
        # exact structure and content returned by Gemini via ExtractorV3.