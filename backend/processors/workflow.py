import logging
from pathlib import Path
from backend.processors.ocr.processing import OCRProcessor
from backend.processors.reporting.generator import ReportGenerator
from backend.config.settings import settings
from backend.processors.valuation.valuator import CompanyValuator
from backend.processors.financials.extractor import FinancialExtractor
import json
import os
import uuid
from backend.storage.report_archive import save_report, cleanup_temp_file
# Configure logging here
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ValuationWorkflow:
    def execute(self, file_path: str, user_id: str = None, report_id: str = None, output_path: str = None):
        logger.info(f"Starting valuation workflow for user: {user_id}, report: {report_id}")
        
        # Create temp_results directory (only for intermediate processing)
        self.temp_dir = Path(settings.TEMP_STORAGE_PATH)  # Use config for temp dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        temp_dir = self.temp_dir
        
        
        logger.info(f"Starting valuation workflow for user: {user_id}")
        logger.info(f"Processing document: {file_path}")
            
        try:
            # OCR Processing
            logger.info("Initializing OCR processing")
            # Verify API key is available
            if not settings.MISTRAL_API_KEY:
                logger.error("MISTRAL_API_KEY is not set or empty")
                raise ValueError("MISTRAL_API_KEY is missing. Please check your environment variables or settings.")
            
            # Add more detailed logging for API key
            logger.info(f"Using Mistral API key (first 5 chars): {settings.MISTRAL_API_KEY[:5]}...")
            logger.info(f"API key length: {len(settings.MISTRAL_API_KEY)}")
            
            processor = OCRProcessor(api_key=settings.MISTRAL_API_KEY)
            
            logger.info("Processing document with OCR")
            try:
                # Add a retry mechanism for API calls
                max_retries = 3
                retry_count = 0
                last_error = None
                
                while retry_count < max_retries:
                    try:
                        logger.info(f"OCR attempt {retry_count + 1}/{max_retries}")
                        result = processor.process_document(
                            str(file_path), format="html"
                        )
                        
                        html_content = result[0] if isinstance(result, tuple) else result
                        logger.info("OCR processing completed successfully")
                        
                        # Save html_content
                        with open(temp_dir / "html_content.html", "w", encoding="utf-8") as f:
                            f.write(html_content)
                        logger.info("Saved HTML content to temp_results")
                        break  # Success, exit the retry loop
                    except Exception as retry_error:
                        retry_count += 1
                        last_error = retry_error
                        logger.warning(f"OCR attempt {retry_count} failed: {str(retry_error)}")
                        if retry_count < max_retries:
                            import time
                            wait_time = 2 ** retry_count  # Exponential backoff
                            logger.info(f"Retrying in {wait_time} seconds...")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"All {max_retries} OCR attempts failed")
                            raise last_error
            except Exception as ocr_error:
                logger.error(f"OCR processing failed: {str(ocr_error)}")
                
                # Check if it's an authentication error
                if "401 Unauthorized" in str(ocr_error) or "authentication" in str(ocr_error).lower():
                    logger.error("Authentication error detected. Please verify your Mistral API key is valid and not expired.")
                    raise ValueError("Mistral API authentication failed. Please check your API key.") from ocr_error
                
                raise ValueError("ocr_failed", f"OCR processing failed: {str(ocr_error)}") from ocr_error
            
            #zde je problem pokud vevnitr failed to process income statement atd, try more
            #new strategy - look for keyword rozvaha pokud je v tabulce soucasti tabulky tak posli llm 
            #na processing pokud ne hledej dal do te doby nez najdes
            
            #dalsi moznost fuzzy search provozni vysldek hospodareni v celem dokumentu a grab number around it
            
            #last resort if this returns empty value for any of those values than call aws ocr api
            
            
            
            logger.info("Extracting financial data")
            extractor = FinancialExtractor()
            try:
                financial_data = extractor.extract_from_html(html_content)
                logger.info("Financial data extraction completed")
                # Save financial_data with proper encoding for Czech characters
                
                # Save financial_data temporarily (for debugging, optional)
                financial_data_path = self.temp_dir / "financial_data.json"
                with open(financial_data_path, "w", encoding="utf-8") as f:
                    json.dump(financial_data, f, indent=4, ensure_ascii=False)
                logger.info("Saved financial data to temp")
            except Exception as extraction_error:
                logger.error(f"Financial data extraction failed: {str(extraction_error)}")
                raise ValueError("data_extraction_failed", f"Failed to extract financial data: {str(extraction_error)}") from extraction_error
            
            
            try:
                logger.info("Calculating valuation multiples")
                valuation_multiple = CompanyValuator(financial_data)
                result_valuation = valuation_multiple.calculate_multiples()
                logger.info("Valuation calculations completed")
                
                # Save valuation results temporarily (for debugging, optional)
                valuation_path = self.temp_dir / "result_valuation.json"
                with open(valuation_path, "w", encoding="utf-8") as f:
                    json.dump(result_valuation, f, indent=4, ensure_ascii=False)
                logger.info("Saved valuation results to temp")
            except Exception as valuation_error:
                logger.error(f"Valuation calculation failed: {str(valuation_error)}")
                raise ValueError("valuation_failed", f"Failed to calculate valuation: {str(valuation_error)}") from valuation_error
            
            
            # Generate Report
            try:
                logger.info("Generating final report")
                report = ReportGenerator.generate({
                    "financial_data": financial_data,
                    "result_valuation": result_valuation
                })
                
                # Save report to Supabase Storage
                report_filename = f"report_{uuid.uuid4()}.docx"
                temp_report_path = self.temp_dir / report_filename
                report.save(str(temp_report_path))
                logger.info(f"Temporarily saved report to {temp_report_path}")
            except Exception as report_gen_error:
                logger.error(f"Report generation failed: {str(report_gen_error)}")
                raise ValueError("report_generation_failed", f"Failed to generate report: {str(report_gen_error)}") from report_gen_error
            
            try:
                # Use report_archive to save to Supabase storage
                # Get original filename from the file_path
                original_filename = os.path.basename(file_path)
                
                # Upload to Supabase and get public URL
                report_url = save_report(user_id, temp_report_path, original_filename, report_id)
                logger.info(f"Report saved to Supabase: {report_url}")
            except Exception as storage_error:
                logger.error(f"Report storage failed: {str(storage_error)}")
                raise ValueError("storage_failed", f"Failed to save report to storage: {str(storage_error)}") from storage_error
            
            
            # Clean up temporary files
            cleanup_temp_file(temp_report_path)
            cleanup_temp_file(financial_data_path)
            cleanup_temp_file(valuation_path)
            cleanup_temp_file(Path(file_path))  # Clean up original uploaded file
            
            # Clean up temporary report file
            if os.path.exists(temp_report_path):
                os.remove(temp_report_path)
                logger.info(f"Cleaned up temporary report file")
            
            return {
                "report_url": report_url,
                "status": "success"
            }
            
        except ValueError as ve:
            # Handle our custom categorized errors
            if len(ve.args) >= 2:
                error_category = ve.args[0]
                error_message = ve.args[1]
                logger.error(f"Error in valuation workflow ({error_category}): {error_message}")
                
                # Clean up any temporary files if an error occurs
                for temp_file in self.temp_dir.glob("*"):
                    cleanup_temp_file(temp_file)
                
                return {
                    "status": "failed",
                    "error_category": error_category,
                    "error_message": error_message
                }
            else:
                # Handle regular ValueError
                logger.error(f"Error in valuation workflow: {str(ve)}", exc_info=True)
                
                # Clean up any temporary files if an error occurs
                for temp_file in self.temp_dir.glob("*"):
                    cleanup_temp_file(temp_file)
                
                return {
                    "status": "failed",
                    "error_category": "validation_error",
                    "error_message": str(ve)
                }
        except Exception as e:
            logger.error(f"Error in valuation workflow: {str(e)}", exc_info=True)
            # Clean up any temporary files if an error occurs
            for temp_file in self.temp_dir.glob("*"):
                cleanup_temp_file(temp_file)
            
            return {
                "status": "failed",
                "error_category": "unexpected_error",
                "error_message": str(e)
            }