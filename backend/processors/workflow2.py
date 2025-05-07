import logging
from pathlib import Path
from backend.processors.ocr.processing import OCRProcessor # Assuming OCRProcessor is reusable
from backend.processors.financials.extractor2 import FinancialExtractor2
from backend.processors.valuation.valuator2 import CompanyValuator2
from backend.processors.reporting.generator2 import ReportGenerator2
from backend.config.settings import settings
import json
import os
import uuid
from backend.storage.report_archive import save_report, cleanup_temp_file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ValuationWorkflow2:
    def __init__(self, keep_intermediate_files: bool = False):
        self.temp_dir_path = Path(settings.TEMP_STORAGE_PATH) / f"workflow_temp_{uuid.uuid4()}"
        self.temp_dir_path.mkdir(parents=True, exist_ok=True)
        self.keep_intermediate_files = keep_intermediate_files # Store the flag
        logger.info(f"Temporary directory for workflow created: {self.temp_dir_path}")
        if self.keep_intermediate_files:
            logger.info(f"Intermediate files in {self.temp_dir_path} will be preserved for this run.")

    def _cleanup_temp_dir(self):
        if self.temp_dir_path.exists():
            for item in self.temp_dir_path.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        # shutil.rmtree(item) # If you need to remove subdirectories
                        pass # For now, only removing files in the top temp_dir
                except Exception as e:
                    logger.error(f"Error cleaning up temp item {item}: {e}")
            try:
                self.temp_dir_path.rmdir() # Remove the temp_dir itself if empty
                logger.info(f"Successfully cleaned up temporary directory: {self.temp_dir_path}")
            except OSError as e: # Directory not empty
                logger.warning(f"Could not remove temporary directory {self.temp_dir_path} as it might not be empty: {e}")


    def execute(self, file_path: str, user_id: str = None, report_id: str = None, output_path: str = None):
        logger.info(f"Starting valuation workflow V2 for user: {user_id}, report: {report_id}")
        logger.info(f"Processing document: {file_path}")

        # Define paths for intermediate files within the unique temp directory
        html_output_path = self.temp_dir_path / "ocr_output.html"
        financial_data_json_path = self.temp_dir_path / "financial_data_v2.json"
        valuation_json_path = self.temp_dir_path / "valuation_v2.json"
        
        all_data_for_report = {} # To hold combined data for the report generator

        try:
            # 1. OCR Processing (reusing existing processor)
            logger.info("Initializing OCR processing (V2 workflow)")
            if not settings.MISTRAL_API_KEY:
                logger.error("MISTRAL_API_KEY is not set or empty")
                raise ValueError("MISTRAL_API_KEY_MISSING", "Mistral API key is missing.")
            
            ocr_processor = OCRProcessor(api_key=settings.MISTRAL_API_KEY)
            logger.info("Processing document with OCR...")
            # Assuming process_document returns HTML content directly or as first element of a tuple
            ocr_result = ocr_processor.process_document(str(file_path), format="html")
            html_content = ocr_result[0] if isinstance(ocr_result, tuple) else ocr_result
            
            with open(html_output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"OCR HTML content saved to {html_output_path}")
            all_data_for_report['ocr_html_path'] = str(html_output_path)


            # 2. Financial Data Extraction (using ExtractorV2)
            logger.info("Initializing Financial Extractor V2...")
            extractor = FinancialExtractor2() # OPENAI_API_KEY should be picked from settings by ExtractorV2
            financial_and_analytical_data = extractor.extract_from_html(html_content)
            
            with open(financial_data_json_path, "w", encoding="utf-8") as f:
                json.dump(financial_and_analytical_data, f, indent=4, ensure_ascii=False)
            logger.info(f"Financial and analytical data (V2) saved to {financial_data_json_path}")
            
            if not financial_and_analytical_data or \
               (not financial_and_analytical_data.get('information') and \
                not financial_and_analytical_data.get('income_statement') and \
                not financial_and_analytical_data.get('document_analysis')):
                logger.warning("Financial extractor V2 returned limited or no data.")
                # Potentially raise an error or handle as a partial success depending on requirements
                # For now, we'll proceed but the report might be sparse.
            
            all_data_for_report.update(financial_and_analytical_data)


            # 3. Company Valuation (using ValuatorV2)
            logger.info("Initializing Company Valuator V2...")
            valuator = CompanyValuator2(financial_and_analytical_data) # Pass the rich data
            valuation_results = valuator.calculate_multiples()
            
            with open(valuation_json_path, "w", encoding="utf-8") as f:
                json.dump(valuation_results, f, indent=4, ensure_ascii=False)
            logger.info(f"Valuation results (V2) saved to {valuation_json_path}")
            all_data_for_report['result_valuation'] = valuation_results


            # 4. Report Generation (using GeneratorV2)
            logger.info("Initializing Report Generator V2...")
            report_generator = ReportGenerator2()
            report_document = report_generator.generate(all_data_for_report) # Pass all collected data
            
            report_filename_base = f"report_v2_{report_id or uuid.uuid4()}"
            # Determine if output_path is a directory or a full file path
            if output_path:
                p_output_path = Path(output_path)
                if p_output_path.is_dir():
                    temp_report_path = p_output_path / f"{report_filename_base}.docx"
                else: # Assumed to be a full file path
                    temp_report_path = p_output_path
                    p_output_path.parent.mkdir(parents=True, exist_ok=True) # Ensure directory exists
            else: # Default to temp_dir_path if no output_path
                temp_report_path = self.temp_dir_path / f"{report_filename_base}.docx"

            report_document.save(str(temp_report_path))
            logger.info(f"Report (V2) temporarily saved to {temp_report_path}")

            # 5. Save to Storage (if user_id and report_id are provided for Supabase)
            report_url = None
            if user_id and report_id:
                original_filename = os.path.basename(file_path)
                try:
                    report_url = save_report(user_id, temp_report_path, original_filename, report_id, is_v2=True)
                    logger.info(f"Report (V2) saved to Supabase: {report_url}")
                except Exception as storage_error:
                    logger.error(f"Report (V2) storage failed: {str(storage_error)}")
                    # Decide if this is a critical failure or if local path is acceptable
                    raise ValueError("STORAGE_FAILED_V2", f"Failed to save report (V2) to storage: {str(storage_error)}") from storage_error
            else:
                report_url = str(temp_report_path.resolve()) # Local file path if not saving to Supabase
                logger.info(f"Report (V2) available locally at: {report_url} (Supabase upload skipped)")


            # Clean up the original uploaded file if it's in a temp location managed by this workflow
            # Assuming file_path could be a temporary upload that needs cleanup.
            # Be cautious with this if file_path is a persistent user file.
            # For now, let's assume it's a temp file that can be cleaned.
            # cleanup_temp_file(Path(file_path)) 
            # logger.info(f"Cleaned up original uploaded file: {file_path}")
            # The above line is commented out as cleaning up file_path might be risky
            # if it's not guaranteed to be a temporary file specific to this workflow run.

            return {
                "report_url": report_url,
                "status": "success",
                "version": "2.0",
                "intermediate_files": { # For debugging or inspection
                    "ocr_html": str(html_output_path.resolve()),
                    "financial_data_json": str(financial_data_json_path.resolve()),
                    "valuation_json": str(valuation_json_path.resolve()),
                    "final_report_path": str(temp_report_path.resolve())
                }
            }

        except ValueError as ve:
            error_category = ve.args[0] if len(ve.args) >= 1 else "VALIDATION_ERROR_V2"
            error_message = ve.args[1] if len(ve.args) >= 2 else str(ve)
            logger.error(f"Error in valuation workflow V2 ({error_category}): {error_message}", exc_info=True)
            return {"status": "failed", "error_category": error_category, "error_message": error_message, "version": "2.0"}
        except Exception as e:
            logger.error(f"Unexpected error in valuation workflow V2: {str(e)}", exc_info=True)
            return {"status": "failed", "error_category": "UNEXPECTED_ERROR_V2", "error_message": str(e), "version": "2.0"}
        finally:
            if self.keep_intermediate_files:
                logger.info(f"KEEP_INTERMEDIATE_FILES is True. All files in temporary directory {self.temp_dir_path} will be preserved.")
            else:
                # Original cleanup logic
                # This logic aims to clean the temp_dir if the final report is NOT in it,
                # or if an error occurred before the report was generated.
                # If the final report IS in the temp_dir (e.g. output_path was not given or was the temp_dir),
                # it tries to clean only the intermediate files.
                
                # Determine if the final report (if generated) is within the temp_dir_path
                final_report_is_in_temp_dir = False
                if 'report_url' in locals() and report_url:
                    try:
                        p_report_url = Path(report_url)
                        # Check if it's a file and its parent is the temp_dir
                        if p_report_url.is_file() and p_report_url.parent.resolve() == self.temp_dir_path.resolve():
                            final_report_is_in_temp_dir = True
                    except Exception:
                        # report_url might be a URL or invalid path, assume not in temp_dir for cleanup purposes
                        pass
                
                if 'report_url' not in locals() or not report_url: # Error before report_url was set or report_url is empty
                    logger.info(f"Error occurred before report generation or report_url not set. Performing full cleanup of {self.temp_dir_path}.")
                    self._cleanup_temp_dir()
                elif not final_report_is_in_temp_dir:
                    # This means report_url is set, and it's not a file in self.temp_dir_path
                    # (e.g., it's a Supabase URL, or a local path outside temp_dir)
                    logger.info(f"Final report is not in the temporary directory {self.temp_dir_path} (URL: {report_url}). Performing full cleanup.")
                    self._cleanup_temp_dir()
                else:
                    # report_url is set and it IS a file in self.temp_dir_path
                    logger.info(f"Final report is in {self.temp_dir_path}. Performing selective cleanup of intermediate files only.")
                    # Selectively clean intermediate files, ensuring not to delete the final report
                    # This assumes intermediate file names are distinct from the final report name pattern.
                    if html_output_path.exists() and (not report_url or Path(report_url).name != html_output_path.name):
                        cleanup_temp_file(html_output_path)
                    if financial_data_json_path.exists() and (not report_url or Path(report_url).name != financial_data_json_path.name):
                        cleanup_temp_file(financial_data_json_path)
                    if valuation_json_path.exists() and (not report_url or Path(report_url).name != valuation_json_path.name):
                        cleanup_temp_file(valuation_json_path)
                    logger.info(f"Temporary directory {self.temp_dir_path} will be left as it contains the final report and/or other files.")


if __name__ == '__main__':
    # This is a placeholder for a test execution.
    # You would need a sample PDF file and potentially an output directory.
    
    # Create a dummy PDF file for testing OCR (if OCR is not mocked)
    # For a real test, use an actual PDF.
    # For now, let's assume OCR produces some dummy HTML if file_path is fake.
    
    # Ensure your settings.py has MISTRAL_API_KEY and OPENAI_API_KEY
    if not settings.MISTRAL_API_KEY or not settings.OPENAI_API_KEY:
        print("Please set MISTRAL_API_KEY and OPENAI_API_KEY in your settings or environment for testing.")
    else:
        # Create a dummy file to simulate an upload
        # dummy_pdf_path = Path("dummy_financial_report.pdf") # Comment out or remove dummy file creation
        # with open(dummy_pdf_path, "w") as f: # Comment out or remove dummy file creation
        #     f.write("This is a dummy PDF content placeholder.") # OCR will process this # Comment out or remove dummy file creation
        
        # --- MODIFICATION: Specify the path to your real PDF file ---
        real_pdf_file_path = "./vz_2023_isotra.pdf" # <-- CHANGE THIS to your file's path
        # Ensure this file exists before running.

        # Define an output directory for the report
        test_output_dir = Path("test_workflow_v2_output")
        test_output_dir.mkdir(parents=True, exist_ok=True)
        
        workflow_v2 = ValuationWorkflow2(keep_intermediate_files=True) # MODIFIED: Set to True for testing
        
        # Test case 1: Execute with local output path
        print("\n--- Test Case 1: Local Output ---")
        # If you want this test case to interact with Supabase, user_id and report_id must be valid.
        # If report_id is intended for Supabase, it MUST be a valid UUID.
        # The "local_" prefix made it invalid for the Supabase 'id' column of type UUID.
        # If you want to test without Supabase, set user_id=None or report_id=None.
        # For this test, let's assume you want to test the Supabase upload.
        test_report_id = str(uuid.uuid4()) # Generate a valid UUID

        result_local = workflow_v2.execute(
            file_path=str(real_pdf_file_path), # <-- USE THE REAL FILE PATH HERE
            user_id="test_user_local", # This will trigger Supabase interaction if report_id is also present
            report_id=test_report_id,  # Pass the valid UUID
            output_path=str(test_output_dir) # Save to local directory
        )
        print(f"Workflow V2 Result (Local): {json.dumps(result_local, indent=2)}")
        if result_local['status'] == 'success':
            print(f"Report should be in: {result_local.get('report_url')}")
            print(f"Intermediate files: {result_local.get('intermediate_files')}")

        # Clean up dummy PDF
        # dummy_pdf_path.unlink(missing_ok=True)

        # Note: For a full end-to-end test, you'd mock external API calls (Mistral, OpenAI, Supabase)
        # or run against actual services with test credentials.
        # The current __main__ provides a basic execution flow.
        # The `save_report` function in `report_archive.py` would need to handle `is_v2` if you want different storage paths. 