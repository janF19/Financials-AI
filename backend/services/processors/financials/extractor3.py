# backend/processors/financials/extractor3.py
import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Any, Union, List

from pydantic import BaseModel, Field, model_validator, ValidationError
from google.api_core import exceptions as google_exceptions

# Attempt to import settings for API key
try:
    from backend.config.settings import settings
    GOOGLE_API_KEY_SOURCE = "settings"
except ImportError:
    settings = None
    GOOGLE_API_KEY_SOURCE = "environment"

# Try to import genai, handle if not installed
try:
    import google.generativeai as genai
    GENAI_INSTALLED = True
except ImportError:
    genai = None
    GENAI_INSTALLED = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Pydantic Models for Gemini Response Structure ---

class FinancialStatementLineItem(BaseModel):
    """Represents a single line item in a financial statement, including its name (key)."""
    item_name: str = Field(description="The name or key of the financial item (e.g., 'Aktiva celkem').")
    value: Optional[str] = Field(None, description="The monetary value or text of this item. Numerical values should be returned as strings.")
    description: Optional[str] = Field(None, description="Optional description of this item.")
    model_config = {"extra": "allow"}

class Statement(BaseModel):
    """Financial statement model"""
    name: Optional[str] = Field(None, description="Name of financial statement (e.g., Rozvaha)")
    items: List[FinancialStatementLineItem] = Field(
        default_factory=list,
        description="List of line items in the statement. Each item includes its name (item_name), value, and optional description."
    )

    model_config = {"extra": "allow"}

class Finance(BaseModel):
    """Complete financial information extracted from reports using Gemini"""
    employee_count: Optional[str] = Field(None, description="Počet zaměstnanců")
    year: Optional[str] = Field(None, description="Rok finančního výkazu")
    company_name: Optional[str] = Field(None, description="Název společnosti")
    ic: Optional[str] = Field(None, description="IČO společnosti")
    registered_capital: Optional[str] = Field(None, description="Základní kapitál")
    headquarters: Optional[str] = Field(None, description="Sídlo společnosti")
    revenue_current_year: Optional[str] = Field(None, description="Celkové tržby společnosti (aktuální rok)")
    revenue_last_year: Optional[str] = Field(None, description="Celkové tržby společnosti (minulý rok)")
    industry: Optional[str] = Field(None, description="Odvětví, ve kterém společnost podniká")
    analytical_summary: Optional[str] = Field(None, description="Stručný analytický souhrn klíčových zjištění z dokumentu.")
    balance_sheet: Optional[Statement] = Field(
        default_factory=lambda: Statement(name="Rozvaha", items=[]),
        description="Informace z Rozvahy (Balance Sheet)"
    )
    cashflow_statement: Optional[Statement] = Field(
        default_factory=lambda: Statement(name="Výkaz peněžních toků", items=[]),
        description="Informace z Výkazu peněžních toků (Cash Flow Statement)"
    )
    income_statement: Optional[Statement] = Field(
        default_factory=lambda: Statement(name="Výkaz zisků a ztrát", items=[]),
        description="Informace z Výkazu zisků a ztrát (Income Statement)"
    )

    model_config = {"extra": "allow"} # Allow Gemini to return extra fields if needed

# --- Function to inline JSON schema definitions ---
def inline_json_schema_defs(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively inlines $ref definitions in a JSON schema.
    The Google API expects a schema without $defs or $ref.
    """
    if not isinstance(schema, dict):
        return schema

    defs = schema.get("$defs")

    # Create a new schema, initially without $defs if it exists.
    # We will build the inlined version from other parts.
    inlined_schema_root = {k: v for k, v in schema.items() if k != "$defs"}

    def _resolve_refs(current_obj):
        if isinstance(current_obj, dict):
            if "$ref" in current_obj:
                ref_path = current_obj["$ref"]
                # Expecting refs like "#/$defs/MyModelName"
                if ref_path.startswith("#/$defs/") and defs:
                    def_key = ref_path.split('/')[-1]
                    if def_key in defs:
                        # Recursively resolve refs in the definition itself before inlining.
                        # Make a copy to avoid modifying the original defs dict if a definition
                        # is complex and might be referenced multiple times (though less likely here).
                        resolved_def = _resolve_refs(defs[def_key].copy())
                        return resolved_def
                    else:
                        logger.warning(f"Reference '{ref_path}' not found in $defs. Keeping original ref.")
                        return current_obj # Keep original ref if not found, though this is an issue
                else:
                    logger.warning(f"Unsupported $ref format or $defs missing: '{ref_path}'. Keeping original ref.")
                    return current_obj # Keep original ref if format is unexpected
            else:
                # Recursively process other dictionary items
                return {k: _resolve_refs(v) for k, v in current_obj.items()}
        elif isinstance(current_obj, list):
            # Recursively process list items
            return [_resolve_refs(item) for item in current_obj]
        else:
            # Non-dict, non-list items are returned as is
            return current_obj

    return _resolve_refs(inlined_schema_root)


def remove_unsupported_schema_keywords(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively removes keywords from a JSON schema that are not supported
    by the Google API's Schema definition (like 'title', 'default')
    and attempts to simplify 'anyOf' constructs from Pydantic's Optional/Union.
    """
    if not isinstance(schema, dict):
        return schema

    unsupported_general_keywords = ["title", "definitions", "$defs", "default", "additionalProperties"]
    
    # Make a mutable copy to work with
    cleaned_schema = schema.copy()

    # Special handling for 'anyOf' (primarily for Optional[T] or Union[T1, T2, ...])
    if "anyOf" in cleaned_schema:
        any_of_list = cleaned_schema.pop("anyOf") # Remove 'anyOf' and get its value
        non_null_schema_branches = []
        if isinstance(any_of_list, list):
            for branch_schema in any_of_list:
                is_null_type_schema = isinstance(branch_schema, dict) and \
                                      branch_schema.get("type") == "null" and \
                                      len(branch_schema) == 1
                if not is_null_type_schema:
                    non_null_schema_branches.append(branch_schema)
        
        if len(non_null_schema_branches) == 1:
            # This is likely an Optional[T]. We take the schema of T.
            # The content of the chosen branch needs to be merged into the current cleaned_schema.
            # Subsequent processing in this function will then clean this merged content.
            chosen_branch_content = non_null_schema_branches[0]
            if isinstance(chosen_branch_content, dict):
                for k, v in chosen_branch_content.items():
                    # Merge keys from the chosen branch. If a key (e.g., 'description')
                    # existed at the 'anyOf' level and also inside the branch,
                    # the branch's version will take precedence here.
                    cleaned_schema[k] = v
        elif len(non_null_schema_branches) > 1:
            # This is a Union[T1, T2, ...]. This is complex for Google's schema.
            # Simplification to a single type (e.g., string) will lose properties.
            # For now, we'll try to extract a type, prioritizing string.
            # This part may need to be revisited if complex Unions of objects are essential.
            extracted_types = []
            for branch in non_null_schema_branches:
                if isinstance(branch, dict) and "type" in branch:
                    extracted_types.append(branch["type"])
            
            if "string" in extracted_types:
                cleaned_schema["type"] = "string"
            elif extracted_types:
                cleaned_schema["type"] = extracted_types[0]
            # Note: This simplification for Unions loses detailed structure.
            # Any existing properties in cleaned_schema from before 'anyOf' processing are kept,
            # but properties specific to the Union branches are not merged.
        # If non_null_schema_branches is empty, cleaned_schema is as it was, just without 'anyOf'.

    # Remove other general unsupported keywords from the current level of cleaned_schema
    # This will also apply to keys merged from an 'anyOf' branch.
    keys_to_delete = [key for key in unsupported_general_keywords if key in cleaned_schema]
    for k_del in keys_to_delete:
        del cleaned_schema[k_del]
    
    # Recursively clean nested dictionaries and lists
    # Build the final schema for this level by processing values of the (now modified) cleaned_schema
    final_schema_at_this_level = {}
    for key, value in cleaned_schema.items():
        if isinstance(value, dict):
            final_schema_at_this_level[key] = remove_unsupported_schema_keywords(value)
        elif isinstance(value, list):
            final_schema_at_this_level[key] = [
                remove_unsupported_schema_keywords(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            final_schema_at_this_level[key] = value

    return final_schema_at_this_level


# --- Gemini Schema Definition from Pydantic Model ---
# We derive the schema directly from the Pydantic model for consistency
# and then inline the definitions.
raw_gemini_schema = Finance.model_json_schema()
GEMINI_SCHEMA = remove_unsupported_schema_keywords(inline_json_schema_defs(raw_gemini_schema))

# Optional: For debugging, you can print the schema to see its structure
# import json
# logger.debug(f"Raw Gemini Schema with $defs: {json.dumps(raw_gemini_schema, indent=2)}")
# logger.debug(f"Inlined Gemini Schema for API: {json.dumps(GEMINI_SCHEMA, indent=2)}")

# --- Financial Extractor Class ---

class FinancialExtractor3:
    """
    Extracts financial data and analytical insights directly from PDF reports
    using the Google Gemini API with function calling/structured output.
    """

    def __init__(self, google_api_key: Optional[str] = None):
        if not GENAI_INSTALLED:
            logger.error("google.generativeai package not found. Please install it (`pip install google-generativeai`)")
            raise ImportError("google.generativeai package is required for FinancialExtractor3.")

        self.client = None
        api_key_to_use = google_api_key

        if not api_key_to_use:
            if GOOGLE_API_KEY_SOURCE == "settings" and settings and hasattr(settings, 'GOOGLE_API_KEY') and settings.GOOGLE_API_KEY:
                api_key_to_use = settings.GOOGLE_API_KEY
                logger.info("Loaded Google API key from settings.")
            elif os.environ.get("GOOGLE_API_KEY"):
                 api_key_to_use = os.environ.get("GOOGLE_API_KEY")
                 logger.info(f"Loaded Google API key from environment variable (Source: {GOOGLE_API_KEY_SOURCE}).")

        if api_key_to_use:
            try:
                genai.configure(api_key=api_key_to_use)
                # Test connection by listing models (optional, but good practice)
                # models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                # if not models:
                #     raise ValueError("No suitable Gemini models found with the provided API key.")
                self.model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-04-17") # Or "gemini-1.5-pro"
                logger.info(f"Google GenAI client configured successfully using model: {self.model.model_name}")
            except Exception as e:
                 logger.error(f"Failed to configure Google GenAI client: {e}", exc_info=True)
                 self.model = None
        else:
            self.model = None
            logger.warning("No Google API key provided or found. LLM extraction (V3) will not be possible.")

    def _map_finance_to_dict(self, finance_obj: Finance) -> Dict[str, Any]:
        """Maps the Pydantic Finance object to the dict structure expected by downstream V2 components."""
        output_dict = {
            'information': {},
            'income_statement': {},
            'balance_sheet': {},
            'cash_flow': {},
            'document_analysis': {} # Placeholder for potential future analysis fields
        }

        # Map top-level info
        output_dict['information'] = {
            "IC": finance_obj.ic,
            "registered_capital": finance_obj.registered_capital,
            "employee_count": finance_obj.employee_count,
            "accounting_period": finance_obj.year,
            "company_name": finance_obj.company_name,
            "headquarters": finance_obj.headquarters,
            "industry": finance_obj.industry,
            "analytical_summary": finance_obj.analytical_summary # Map overall summary here
            # Add other fields from Finance model if needed by downstream tasks
        }

        # Map statements - Convert List[FinancialStatementLineItem] to Dict[str, str (value)]
        # Downstream components might need adjustment if they expect more detail than just the value.
        if finance_obj.income_statement and finance_obj.income_statement.items:
            output_dict['income_statement'] = {
                item.item_name: item.value
                for item in finance_obj.income_statement.items
                if item.item_name and item.value is not None # Ensure key exists and value is not None
            }
            # Add analytical summary if present in the statement itself (optional) - this would need 'analytical_summary' field in Statement model
            # output_dict['income_statement']['analytical_summary'] = getattr(finance_obj.income_statement, 'analytical_summary', None)

        if finance_obj.balance_sheet and finance_obj.balance_sheet.items:
            output_dict['balance_sheet'] = {
                item.item_name: item.value
                for item in finance_obj.balance_sheet.items
                if item.item_name and item.value is not None
            }
            # output_dict['balance_sheet']['analytical_summary'] = getattr(finance_obj.balance_sheet, 'analytical_summary', None)

        if finance_obj.cashflow_statement and finance_obj.cashflow_statement.items:
             output_dict['cash_flow'] = {
                item.item_name: item.value
                for item in finance_obj.cashflow_statement.items
                if item.item_name and item.value is not None
            }
            # output_dict['cash_flow']['analytical_summary'] = getattr(finance_obj.cashflow_statement, 'analytical_summary', None)

        # Placeholder for document_analysis - could be populated from finance_obj.analytical_summary
        output_dict['document_analysis']['overall_summary'] = finance_obj.analytical_summary

        # Clean None values from the nested dictionaries for cleaner output
        for section in output_dict:
            if isinstance(output_dict[section], dict):
                output_dict[section] = {k: v for k, v in output_dict[section].items() if v is not None}

        return output_dict


    def extract_from_pdf(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extracts structured financial data from a PDF file using the Gemini API.

        Args:
            file_path: Path to the PDF file to analyze.

        Returns:
            A dictionary containing the extracted financial data, mapped to the
            structure expected by downstream components, or None if extraction fails.
        """
        if not self.model:
            logger.error("Extraction cancelled: Google GenAI client is not initialized.")
            return None
        if not os.path.exists(file_path):
            logger.error(f"Input file not found: {file_path}")
            return None

        logger.info(f"Starting financial data extraction from PDF (ExtractorV3): {file_path}")

        try:
            logger.info(f"Uploading file to Google API: {os.path.basename(file_path)}")
            pdf_file = genai.upload_file(path=file_path, display_name=os.path.basename(file_path))
            logger.info(f"File uploaded successfully: {pdf_file.name}")

            # Wait for file processing if necessary (usually fast, but good practice)
            while pdf_file.state.name == "PROCESSING":
                print('.', end='')
                time.sleep(5)
                pdf_file = genai.get_file(pdf_file.name)
            if pdf_file.state.name != "ACTIVE":
                 logger.error(f"File processing failed or did not become active: {pdf_file.state.name}")
                 # Consider deleting the file: genai.delete_file(pdf_file.name)
                 return None
            logger.info("File is active and ready for processing.")


            # Define the prompt for Gemini
            prompt = f"""
            Analyzuj následující finanční výkaz (PDF soubor) a extrahuj strukturovaná data v češtině.
            Zaměř se na následující informace za poslední dostupný účetní rok v dokumentu:

            1.  **Základní informace o společnosti:**
                *   Název společnosti
                *   IČO (Identifikační číslo osoby)
                *   Sídlo společnosti
                *   Základní kapitál
                *   Počet zaměstnanců (průměrný přepočtený stav, pokud je uveden)
                *   Účetní období (např. "2023" nebo "1.1.2023 - 31.12.2023")
                *   Odvětví/předmět podnikání

            2.  **Klíčové finanční ukazatele:**
                *   Celkové tržby (nebo Výnosy celkem) za aktuální období
                *   Celkové tržby (nebo Výnosy celkem) za minulé období

            3.  **Finanční výkazy (extrahuj položky jako seznam objektů):**
                Pro každý výkaz (Rozvaha, Výkaz zisku a ztráty, Výkaz peněžních toků):
                *   Uveďte název výkazu (např. "Rozvaha").
                *   Položky výkazu extrahujte jako seznam (pole) objektů do pole 'items'. Každý objekt v seznamu by měl obsahovat:
                    *   `item_name`: Název položky (např. "Aktiva celkem"). Musí být string.
                    *   `value`: Hodnota položky (jako text, např. "123.45" nebo "10000"). Může být null, pokud chybí.
                    *   `description`: Volitelný popis položky (jako text). Může být null.
                Příklad pro jednu položku v seznamu 'items' pro Rozvahu:
                `{{ "item_name": "Aktiva celkem", "value": "1234567.89", "description": "Celková aktiva společnosti" }}`
                Další příklad:
                `{{ "item_name": "Dlouhodobý nehmotný majetek", "value": "50000.00", "description": null }}`

            4.  **Analytický souhrn:** Poskytni velmi stručný (2-4 věty) souhrn klíčových zjištění, trendů nebo významných událostí zmíněných v dokumentu (např. hlavní zdroj příjmů, významné investice, změny ve struktuře majetku/dluhu).

            Vrať výsledek POUZE jako JSON objekt, který odpovídá poskytnutému schématu.
            Pro číselné hodnoty v poli 'value' vraťte číslo jako text (např. "123.45" nebo "1000"). Pro nečíselné hodnoty vraťte text. Použij `null`, pokud hodnota chybí nebo není relevantní (např. pro 'description').
            """

            logger.info("Sending request to Gemini API for structured data extraction...")
            response = self.model.generate_content(
                [prompt, pdf_file],
                generation_config=genai.types.GenerationConfig(
                    # Ensure JSON output by specifying the schema
                    response_mime_type="application/json",
                    response_schema=GEMINI_SCHEMA # Use the schema derived from Pydantic
                )
                # stream=False # Ensure we get the full response at once
            )

            # Clean up the uploaded file after processing
            try:
                logger.info(f"Deleting uploaded file: {pdf_file.name}")
                genai.delete_file(pdf_file.name)
                logger.info("Uploaded file deleted successfully.")
            except Exception as del_err:
                logger.warning(f"Could not delete uploaded file {pdf_file.name}: {del_err}")


            logger.info("Gemini response received.")
            # Debug: Log the raw response text
            # logger.debug(f"Gemini Raw Response Text: {response.text}")

            # Validate and parse the JSON response using the Pydantic model
            try:
                finance_data = Finance.model_validate_json(response.text)
                logger.info("Successfully parsed and validated Gemini JSON response.")

                # Map the Pydantic object to the dictionary format needed downstream
                mapped_data = self._map_finance_to_dict(finance_data)
                logger.info("Successfully mapped extracted data to V2 dictionary format.")
                return mapped_data

            except json.JSONDecodeError as json_err:
                logger.error(f"Failed to parse Gemini JSON response: {json_err}")
                logger.error(f"LLM Raw Response causing error: {response.text}")
                return None
            except ValidationError as val_err:
                 logger.error(f"Gemini response failed Pydantic validation: {val_err}")
                 logger.error(f"LLM Raw Response causing error: {response.text}")
                 return None

        except google_exceptions.GoogleAPIError as api_err:
            logger.error(f"Google API error during extraction: {api_err}", exc_info=True)
            # Attempt to delete the file if it exists and an API error occurred
            if 'pdf_file' in locals() and pdf_file and hasattr(pdf_file, 'name'):
                 try:
                     genai.delete_file(pdf_file.name)
                     logger.info(f"Cleaned up potentially orphaned file {pdf_file.name} after API error.")
                 except Exception as del_err:
                     logger.warning(f"Could not delete file {pdf_file.name} after API error: {del_err}")
            return None
        except FileNotFoundError as fnf_err: # Catch specific file upload error if path is wrong initially
             logger.error(f"File not found during upload preparation: {fnf_err}")
             return None
        except Exception as e:
            logger.error(f"Unexpected error during Gemini extraction (V3): {e}", exc_info=True)
            # Attempt to delete the file if it exists and an unexpected error occurred
            if 'pdf_file' in locals() and pdf_file and hasattr(pdf_file, 'name'):
                 try:
                     genai.delete_file(pdf_file.name)
                     logger.info(f"Cleaned up potentially orphaned file {pdf_file.name} after unexpected error.")
                 except Exception as del_err:
                     logger.warning(f"Could not delete file {pdf_file.name} after unexpected error: {del_err}")
            return None

# --- Main block for testing ---
if __name__ == "__main__":
    import sys
    import argparse
    import time # Needed for sleep

    parser = argparse.ArgumentParser(description='Extract financial data from PDF files using Gemini (V3)')
    parser.add_argument('input_file', help='Path to the input PDF file')
    parser.add_argument('output_file', help='Path to the output JSON file')
    parser.add_argument('--log', help='Path to log file (optional)')
    args = parser.parse_args()

    if args.log:
        log_dir = os.path.dirname(args.log)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(args.log, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        # Add handler to the root logger
        logging.getLogger().addHandler(file_handler)
        logging.getLogger().setLevel(logging.INFO) # Ensure root logger level is appropriate
        logger.info(f"Logging to file: {args.log}")

    # Ensure API key is available
    api_key_present = (settings and hasattr(settings, 'GOOGLE_API_KEY') and settings.GOOGLE_API_KEY) or os.environ.get("GOOGLE_API_KEY")
    if not api_key_present:
        logger.error("GOOGLE_API_KEY not found in settings or environment variables. Cannot proceed.")
        print("Error: GOOGLE_API_KEY is required. Set it in settings or environment.", file=sys.stderr)
        sys.exit(1)
    if not GENAI_INSTALLED:
         logger.error("google.generativeai package not installed. Cannot proceed.")
         print("Error: google.generativeai package is required. Run `pip install google-generativeai`", file=sys.stderr)
         sys.exit(1)


    extractor = FinancialExtractor3()

    try:
        if not os.path.exists(args.input_file):
            raise FileNotFoundError(f"Input file not found: {args.input_file}")

        output_dir = os.path.dirname(args.output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Created output directory: {output_dir}")

        logger.info("Starting extraction (V3)")
        financial_data_output = extractor.extract_from_pdf(args.input_file)
        logger.info("Extraction finished (V3)")

        if financial_data_output:
            logger.info(f"Saving extracted data to {args.output_file}")
            with open(args.output_file, 'w', encoding='utf-8') as f:
                json.dump(financial_data_output, f, indent=4, ensure_ascii=False)
            logger.info("Data saved successfully")

            print("\n--- Extraction V3 Summary ---")
            print(f"Data saved to: {args.output_file}")
            for key, value in financial_data_output.items():
                 has_data = bool(value) # Check if the section dict is non-empty
                 print(f"{key.replace('_', ' ').title()} extracted: {'Yes' if has_data else 'No'}")
                 if isinstance(value, dict) and value.get('analytical_summary'):
                      print(f"  Analytical Summary for {key.replace('_', ' ').title()}: Present")
                 elif key == 'document_analysis' and value.get('overall_summary'):
                      print(f"  Overall Summary: Present")

            print("------------------------\n")
        else:
            print(f"Extraction failed. No output generated. Check logs ({args.log or 'console'}) for details.")
            sys.exit(1)

    except FileNotFoundError as e:
        logger.error(f"File not found error in main execution: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ImportError as e:
         logger.error(f"Import error: {e}")
         print(f"Import Error: {e}. Make sure required packages are installed.", file=sys.stderr)
         sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred in main execution (V3): {e}", exc_info=True)
        print(f"An unexpected error occurred: {str(e)}", file=sys.stderr)
        sys.exit(1)
