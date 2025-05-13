import json
import re
import logging
from difflib import SequenceMatcher
from typing import Dict, Any, Optional, List, Tuple

import openai
from bs4 import BeautifulSoup
# Assuming settings holds your OpenAI key correctly
# If not, fallback logic using os.environ is included
try:
    from backend.config.settings import settings
    OPENAI_API_KEY_SOURCE = "settings"
except ImportError:
    settings = None
    OPENAI_API_KEY_SOURCE = "environment"
import os


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Constants ---
INCOME_KEYWORDS = ['VÝKAZ ZISKU A ZTRÁTY', 'VÝKAZ ZISKU A ZTRÁTY, druhové členění', 'VYKAZ ZISKU A ZTRATY', 'VÝKAZ ZISKU', 'VYKAZ ZISKU', 'VÝSLEDOVKA', 'Income Statement']
BALANCE_KEYWORDS = ['ROZVAHA', 'Rozvaha', 'Balance Sheet', 'BILANCE', 'AKTIVA', 'PASIVA']
CASHFLOW_KEYWORDS = ['PŘEHLED O PENĚŽNICH TOCÍCH', 'PŘEHLED O PENĚŽNÍCH TOCÍCH', 'PREHLED O PENEZNICH TOCICH', 'CASH FLOW', 'PENĚŽNÍ TOKY', 'PENEZNI TOKY', 'Přehled o peněžních tocích']

# LLM Model Configuration
LLM_MODEL = "gpt-4o" # Or your preferred model
MAX_CONTEXT_CHARS = 12000
CONTEXT_LINES_BEFORE = 2
CONTEXT_LINES_AFTER = 45 # For standard sections
INFO_CONTEXT_LINES = 120 # More context for general company info and overall analysis
OVERALL_ANALYSIS_CONTEXT_LINES = 300 # Even more for overall document analysis

class FinancialExtractor2:
    """
    Extracts financial data and analytical insights from HTML reports using an LLM-first approach.
    Focuses on robust section finding, detailed LLM prompts for extraction, and qualitative analysis.
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        self.financial_data = self._initialize_financial_data()
        api_key_to_use = openai_api_key

        if not api_key_to_use:
            if OPENAI_API_KEY_SOURCE == "settings" and settings and hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
                api_key_to_use = settings.OPENAI_API_KEY
                logger.info("Loaded OpenAI API key from settings.")
            elif os.environ.get("OPENAI_API_KEY"):
                 api_key_to_use = os.environ.get("OPENAI_API_KEY")
                 logger.info(f"Loaded OpenAI API key from environment variable (Source: {OPENAI_API_KEY_SOURCE}).")

        if api_key_to_use:
            try:
                self.client = openai.OpenAI(api_key=api_key_to_use)
                self.client.models.list() # Verify key
                logger.info(f"OpenAI client initialized and key verified using model: {LLM_MODEL}")
            except openai.AuthenticationError:
                 logger.error("OpenAI Authentication Error: The provided API key is invalid or expired.")
                 self.client = None
            except Exception as e:
                 logger.error(f"Failed to initialize OpenAI client: {e}")
                 self.client = None
        else:
            self.client = None
            logger.warning("No OpenAI API key provided or found. LLM extraction will not be possible.")


    def _initialize_financial_data(self) -> Dict[str, Dict]:
        return {
            'information': {},
            'income_statement': {},
            'balance_sheet': {},
            'cash_flow': {},
            'document_analysis': {} # New section for overall document insights
        }

    def _clean_text(self, text: str) -> str:
        """More aggressive cleaning for comparison."""
        text = ' '.join(text.split()) # Normalize whitespace
        text = text.replace('\xa0', ' ') # Replace non-breaking spaces
        return text.lower().strip()

    def _fuzzy_match_score(self, s1_clean: str, s2_clean: str) -> float:
        """Calculates similarity score between two already cleaned lowercase strings."""
        return SequenceMatcher(None, s1_clean, s2_clean).ratio()

    def _validate_financial_context(self, context: str, section_type: str) -> bool:
        """Validates that the extracted context likely contains actual financial data."""
        if not context:
            return False
        
        has_numbers = bool(re.search(r'\d{3,}', context))  # Multiple digit numbers
        
        if section_type == 'cash_flow':
            cash_flow_indicators = [
                'Stav peněžních prostředků', 'Peněžní toky z', 'Čistý peněžní tok',
                'PENĚŽNÍ TOKY', 'Cash flow', 'Počáteční stav peněžních', 'Konečný stav peněžních'
            ]
            has_cf_terms = False
            context_lower = context.lower()
            threshold = 0.75
            for line in context.split('\n'):
                line_clean = self._clean_text(line)
                for indicator in cash_flow_indicators:
                    indicator_clean = self._clean_text(indicator)
                    if len(indicator_clean) > 5 and (
                       indicator_clean in line_clean or 
                       self._fuzzy_match_score(indicator_clean, line_clean) > threshold):
                        has_cf_terms = True
                        break
                if has_cf_terms:
                    break
            return has_numbers and has_cf_terms
        
        return has_numbers

    def _find_section_context(self,
                              text_lines: List[str],
                              keywords: List[str],
                              threshold: float = 0.85,
                              section_type: str = None,
                              context_lines_after_override: Optional[int] = None) -> Optional[Tuple[str, int]]:
        """
        Refined section finding. `context_lines_after_override` can be used for specific sections.
        """
        best_match_score = 0.0
        best_match_index = -1
        best_match_line_original = ""
        cleaned_keywords = [self._clean_text(kw) for kw in keywords]
        
        effective_context_lines_after = context_lines_after_override if context_lines_after_override is not None else CONTEXT_LINES_AFTER

        logger.debug(f"Searching for keywords like '{cleaned_keywords[0]}' with threshold {threshold}")

        # First pass: Look for exact HTML heading matches
        for i, line in enumerate(text_lines):
            line_original = line.strip()
            if not line_original:
                continue
            
            heading_match = re.search(r'<h\d>(.*?)</h\d>', line_original, re.IGNORECASE)
            if heading_match:
                heading_text = heading_match.group(1)
                heading_clean = self._clean_text(heading_text)
                
                for kw_clean in cleaned_keywords:
                    if kw_clean == heading_clean or self._fuzzy_match_score(kw_clean, heading_clean) > 0.95:
                        logger.info(f"Found exact HTML heading match: '{line_original}' for keywords at line {i}")
                        start_line = max(0, i - CONTEXT_LINES_BEFORE)
                        end_line = min(len(text_lines), i + effective_context_lines_after)
                        context_lines_original = text_lines[start_line:end_line]
                        context_text = "\n".join(context_lines_original).strip()
                        
                        if section_type and not self._validate_financial_context(context_text, section_type):
                            logger.warning(f"Found heading but context doesn't contain financial data at line {i}")
                            continue
                            
                        if len(context_text) > MAX_CONTEXT_CHARS:
                            context_text = context_text[:MAX_CONTEXT_CHARS]
                            
                        return context_text, i

        # Second pass: Standard fuzzy matching approach
        for i, line in enumerate(text_lines):
            line_original = line.strip()
            if not line_original:
                 continue
            line_clean = self._clean_text(line_original)
            if not line_clean:
                 continue

            current_line_best_score_for_any_keyword = 0.0
            for kw_clean in cleaned_keywords:
                score_contained = 0.0
                if kw_clean in line_clean:
                     matcher = SequenceMatcher(None, kw_clean, line_clean)
                     match = matcher.find_longest_match(0, len(kw_clean), 0, len(line_clean))
                     if match and match.size >= len(kw_clean) * 0.95:
                         block_similarity = SequenceMatcher(None, kw_clean, line_clean[match.b:match.b + match.size]).ratio()
                         score_contained = block_similarity * 0.98
                score_prefix = 0.0
                line_segment_clean = line_clean[:len(kw_clean) + 5]
                prefix_sim = self._fuzzy_match_score(kw_clean, line_segment_clean)
                if prefix_sim > 0.8:
                     score_prefix = prefix_sim
                score_direct = self._fuzzy_match_score(kw_clean, line_clean)
                line_keyword_best_score = max(score_contained, score_prefix, score_direct)
                if len(line_clean) < len(kw_clean) + 20:
                    line_keyword_best_score *= 1.05
                current_line_best_score_for_any_keyword = max(current_line_best_score_for_any_keyword, line_keyword_best_score)

            if current_line_best_score_for_any_keyword > best_match_score:
                best_match_score = current_line_best_score_for_any_keyword
                best_match_index = i
                best_match_line_original = line_original

        if best_match_score >= threshold:
            logger.info(f"Found potential section header '{best_match_line_original}' (Best Score: {best_match_score:.2f}) at line {best_match_index} for keywords starting with '{keywords[0]}'.")
            start_line = max(0, best_match_index - CONTEXT_LINES_BEFORE)
            end_line = min(len(text_lines), best_match_index + effective_context_lines_after)
            context_lines_original = text_lines[start_line:end_line]
            context_text = "\n".join(context_lines_original).strip()
            
            if section_type and not self._validate_financial_context(context_text, section_type):
                logger.warning(f"Context doesn't contain expected financial data patterns for {section_type}")
                return None

            if len(context_text) > MAX_CONTEXT_CHARS:
                original_len = len(context_text)
                context_text = context_text[:MAX_CONTEXT_CHARS]
                logger.warning(f"Truncated context from {original_len} to {MAX_CONTEXT_CHARS} characters for LLM.")
            return context_text, best_match_index
        else:
            logger.warning(f"No section found for keywords starting with '{keywords[0]}...' with threshold {threshold}. Best score found: {best_match_score:.2f}")
            return None

    def _all_values_null(self, data: Optional[Dict[str, Any]]) -> bool:
        if not data or not isinstance(data, dict):
            return True
        # Consider a key like 'analytical_summary' as non-null even if other data points are null
        # if it contains meaningful text.
        has_meaningful_analysis = False
        if "analytical_summary" in data and isinstance(data["analytical_summary"], str) and len(data["analytical_summary"].strip()) > 10:
            has_meaningful_analysis = True
        
        # Check if all *other* values are null
        all_other_null = True
        for key, value in data.items():
            if key == "analytical_summary":
                continue
            if value is not None:
                all_other_null = False
                break
        
        return all_other_null and not has_meaningful_analysis


    def _call_llm_for_extraction(self, context: str, prompt_template: str, section_name: str) -> Optional[Dict[str, Any]]:
        if not self.client:
            logger.error(f"Cannot extract {section_name}: OpenAI client not initialized.")
            return None
        if not context:
            logger.warning(f"Cannot extract {section_name}: No context provided.")
            return None
        
        logger.info(f"Printing context for {section_name} (first 500 chars): {context[:500]}...")

        prompt = prompt_template.format(context=context)

        try:
            logger.info(f"Sending request to LLM for {section_name} extraction...")
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are a highly accurate financial data extraction assistant expert in Czech financial documents, including those with OCR errors. Return ONLY the requested valid JSON object. Use `null` only if a value is genuinely missing or unreadable. For analytical summaries, provide concise insights based *only* on the provided text context."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.05, # Low temperature for factual extraction
                response_format={"type": "json_object"}
            )
            response_content = response.choices[0].message.content
            logger.info(f"LLM response received for {section_name}.")

            try:
                extracted_data = json.loads(response_content)
                if not isinstance(extracted_data, dict):
                     logger.error(f"LLM did not return a JSON object for {section_name}. Response: {response_content}")
                     return None
                logger.info(f"Successfully parsed LLM JSON response for {section_name}.")
                logger.debug(f"Parsed LLM data for {section_name}: {json.dumps(extracted_data, ensure_ascii=False)}")

                if self._all_values_null(extracted_data):
                    logger.warning(f"LLM returned only null values (or non-meaningful analysis) for {section_name}. Treating as extraction failure.")
                    return None
                return extracted_data
            except json.JSONDecodeError as json_err:
                logger.error(f"Failed to parse LLM JSON response for {section_name}: {json_err}")
                logger.error(f"LLM Raw Response causing error: {response_content}")
                return None
        except openai.APIError as api_err:
            logger.error(f"OpenAI API error during {section_name} extraction: {api_err}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error during {section_name} LLM extraction: {e}", exc_info=True)
            return None

    # --- LLM Prompt Templates (Modified with analytical_summary) ---
    COMPANY_INFO_PROMPT = """
    Extract the following company information from the provided Czech financial report (výroční zpráva). Return ONLY a valid JSON object. Use `null` if a value cannot be reliably found. Ensure numbers are integers.
    Also, provide a brief analytical summary based on the text, focusing on the company's main business, strategic direction, or significant achievements mentioned in the introductory parts or company profile.

    Text Context:
    ---
    {context}
    ---

    Required JSON Object Structure:
    {{
        "IC": "string or null (Find IČ or IČO, typically 8 digits)",
        "registered_capital": "string or null (Find 'Základní kapitál')",
        "employee_count": "integer or null (Find 'Počet zaměstnanců')",
        "accounting_period": "string or null (Find the reporting year, e.g., '2023')",
        "company_name": "string or null (Find full company name)",
        "legal_form": "string or null (Find 'Právní forma')",
        "main_activities": ["string", ...] or [],
        "established": "string or null (Find 'Datum vzniku / založení')",
        "headquarters": "string or null (Find 'Sídlo')",
        "news": "string or null (Summarize key developments, partnerships, awards, product launches from the report year, if available in this context)",
        "industry": "string or null (Infer based on activities/description. Choose from: [Advertising, Aerospace/Defense, Apparel, Auto & Truck, Auto Parts, Beverage (Alcoholic), Beverage (Soft), Broadcasting, Building Materials, Business & Consumer Services, Cable TV, Chemical (Basic), Chemical (Diversified), Chemical (Specialty), Coal & Related Energy, Computer Services, Computers/Peripherals, Construction Supplies, Diversified, Drugs (Pharmaceutical), Education, Electrical Equipment, Electronics (General), Engineering/Construction, Farming/Agriculture, Food Processing, Food Wholesalers, Furn/Home Furnishings, Homebuilding, Hotel/Gaming, Household Products, Information Services, Machinery, Manufacturing, Metals & Mining, Office Equipment & Services, Paper/Forest Products, Power, Real Estate, Recreation, Restaurant/Dining, Retail, Rubber& Tires, Semiconductor, Software, Steel, Telecommunications, Transportation, Trucking, Utility]. Default to 'Manufacturing' or 'Services' if unclear.)",
        "analytical_summary": "string or null (Brief 2-4 sentence summary of the company's core business, strategy, or key highlights from the provided text context, focusing on information typically found in an introduction or company profile.)"
    }}
    Provide ONLY the JSON object.
    """

    INCOME_STATEMENT_PROMPT = """
    Extract key financial metrics from the provided Czech Income Statement (Výkaz zisku a ztráty). Focus on the CURRENT accounting period ('běžném období').
    Also, provide a brief textual analysis (2-3 sentences) of any notable aspects, significant items, or trends in the current period data. For example, 'Revenue is primarily driven by product sales, with personnel costs being the largest expense.'
    Return ONLY a valid JSON object. Use `null` if a value is genuinely missing. Convert values to integers.

    Text Context:
    ---
    {context}
    ---

    Required JSON Object Structure (CURRENT PERIOD ONLY):
    {{
        "revenue_from_products_and_services_current": "integer or null",
        "revenue_from_goods_current": "integer or null",
        "production_consumption_current": "integer or null",
        "personnel_costs_current": "integer or null",
        "wage_costs_current": "integer or null",
        "depreciation_current": "integer or null",
        "operating_profit_current": "integer or null",
        "ebit_current": "integer or null (same as operating_profit_current)",
        "analytical_summary": "string or null (Brief 2-3 sentence analysis of key items, performance drivers, or notable aspects of the current period's income statement based *only* on the provided context.)"
    }}
    Provide ONLY the JSON object.
    """

    BALANCE_SHEET_PROMPT = """
    Extract key financial metrics from the provided Czech Balance Sheet (Rozvaha) for CURRENT ('Běžné') and PREVIOUS ('Minulé') periods.
    Also, provide a brief textual analysis (2-3 sentences) of any significant changes in asset/liability structure between periods, or notable aspects of the current period's balance sheet (e.g., 'Total assets grew mainly due to an increase in tangible assets, while equity remained stable.').
    Return ONLY a valid JSON object. Use `null` if a value is genuinely missing. Convert values to integers.

    Text Context:
    ---
    {context}
    ---

    Required JSON Object Structure:
    {{
        "total_assets_current": "integer or null",
        "total_assets_previous": "integer or null",
        "intangible_assets_current": "integer or null",
        "intangible_assets_previous": "integer or null",
        "tangible_assets_current": "integer or null",
        "tangible_assets_previous": "integer or null",
        "current_assets_current": "integer or null",
        "current_assets_previous": "integer or null",
        "total_liabilities_equity_current": "integer or null",
        "total_liabilities_equity_previous": "integer or null",
        "equity_current": "integer or null",
        "equity_previous": "integer or null",
        "liabilities_current": "integer or null",
        "liabilities_previous": "integer or null",
        "analytical_summary": "string or null (Brief 2-3 sentence analysis of significant changes or notable aspects of the balance sheet structure based *only* on the provided context.)"
    }}
    Provide ONLY the JSON object.
    """

    CASH_FLOW_PROMPT = """
    Extract key financial metrics from the provided Czech Cash Flow Statement (Přehled o peněžních tocích) for CURRENT ('běžné') and PREVIOUS ('minulé') periods.
    Also, provide a brief textual analysis (2-3 sentences) of the company's cash generation, major cash flows, or overall cash health (e.g., 'Operating activities generated strong cash flow, largely used for investments.').
    Return ONLY a valid JSON object. Use `null` if a value is genuinely missing. Convert values to integers.

    Text Context:
    ---
    {context}
    ---

    Required JSON Object Structure:
    {{
        "initial_cash_balance_current": "integer or null",
        "initial_cash_balance_previous": "integer or null",
        "profit_before_tax_current": "integer or null",
        "profit_before_tax_previous": "integer or null",
        "net_operating_cash_flow_current": "integer or null",
        "net_operating_cash_flow_previous": "integer or null",
        "capex_current": "integer or null (usually negative)",
        "capex_previous": "integer or null (usually negative)",
        "proceeds_from_sale_of_fixed_assets_current": "integer or null",
        "proceeds_from_sale_of_fixed_assets_previous": "integer or null",
        "analytical_summary": "string or null (Brief 2-3 sentence analysis of cash generation, major flows, or overall cash health based *only* on the provided context.)"
    }}
    Provide ONLY the JSON object.
    """

    OVERALL_DOCUMENT_ANALYSIS_PROMPT = """
    Based on the provided text context from a financial report, extract key qualitative insights.
    Focus on summarizing management's perspective, strategic direction, significant events, risks, and outlook if mentioned.
    Return ONLY a valid JSON object. Use `null` if specific information is not found in the context.

    Text Context:
    ---
    {context}
    ---

    Required JSON Object Structure:
    {{
        "management_discussion_summary": "string or null (Summarize the main points from any management discussion, company performance overview, or strategic commentary.)",
        "significant_events_achievements": "string or null (List key events, achievements, or milestones mentioned for the reporting period.)",
        "key_risks_and_uncertainties": "string or null (Identify and summarize any major risks, challenges, or uncertainties highlighted by the company.)",
        "future_outlook_and_strategy": "string or null (Summarize any statements about future plans, strategy, or outlook for the company.)"
    }}
    Provide ONLY the JSON object. Be concise and stick to information present in the text.
    """

    # --- Main Extraction Method ---
    def extract_from_html(self, html_content: str) -> Dict[str, Any]:
        if not self.client:
             logger.error("Extraction cancelled: OpenAI client is not initialized.")
             return self._initialize_financial_data()
        if not html_content or not isinstance(html_content, str) or len(html_content.strip()) == 0:
            logger.error("Invalid or empty HTML content provided.")
            return self._initialize_financial_data()

        logger.info("Starting financial data and insights extraction from HTML (ExtractorV2)...")
        self.financial_data = self._initialize_financial_data()

        try:
            soup = BeautifulSoup(html_content, 'html.parser', from_encoding='utf-8')
            # ... (encoding detection logic from original can be kept if needed) ...
            
            text_parts = []
            for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'table', 'div', 'span']): # Added div and span
                 text = element.get_text(separator=' ', strip=True)
                 if text:
                      text_parts.append(text)
                      if element.name.startswith('h') or element.name == 'table' or element.name == 'div': # Add newline after div too
                           text_parts.append("\n")

            full_text = "\n".join(text_parts)
            text_lines = [line.strip() for line in full_text.split('\n') if line.strip()]

            if not text_lines or len(text_lines) < 10:
                 logger.warning("Advanced text extraction yielded few lines, falling back to simple get_text.")
                 full_text_simple = soup.get_text()
                 text_lines = [line.strip() for line in full_text_simple.split('\n') if line.strip()]

            logger.info(f"Processed HTML into {len(text_lines)} non-empty text lines.")

            # --- Extraction Sequence ---
            # 1. Company Information
            logger.info("Attempting to extract Company Information & Summary...")
            # Use a larger chunk of text from the beginning for company info
            company_info_context = "\n".join(text_lines[:INFO_CONTEXT_LINES]).strip()
            if len(company_info_context) > MAX_CONTEXT_CHARS:
                company_info_context = company_info_context[:MAX_CONTEXT_CHARS]
            if company_info_context:
                extracted_info = self._call_llm_for_extraction(company_info_context, self.COMPANY_INFO_PROMPT, "Company Information")
                if extracted_info:
                    self.financial_data['information'] = extracted_info
                    logger.info("Successfully extracted Company Information & Summary.")
                else:
                    logger.warning("LLM extraction failed for Company Information. Storing empty dictionary.")
                    self.financial_data['information'] = {} # Ensure it's an empty dict
            else:
                logger.warning("No context for Company Information.")
                self.financial_data['information'] = {}


            # 2. Financial Statements (Income, Balance, Cash Flow)
            financial_sections_to_extract = [
                ("Income Statement", CONTEXT_LINES_AFTER, self.INCOME_STATEMENT_PROMPT, 'income_statement', INCOME_KEYWORDS, 0.85),
                ("Balance Sheet", CONTEXT_LINES_AFTER, self.BALANCE_SHEET_PROMPT, 'balance_sheet', BALANCE_KEYWORDS, 0.85),
                ("Cash Flow Statement", CONTEXT_LINES_AFTER, self.CASH_FLOW_PROMPT, 'cash_flow', CASHFLOW_KEYWORDS, 0.75),
            ]

            for name, context_size, prompt, data_key, keywords, threshold in financial_sections_to_extract:
                logger.info(f"Attempting to extract {name} & Analysis...")
                context_tuple = self._find_section_context(text_lines, keywords, threshold, section_type=data_key, context_lines_after_override=context_size)
                if context_tuple:
                    context, _ = context_tuple
                    extracted_data = self._call_llm_for_extraction(context, prompt, name)
                    if extracted_data:
                        self.financial_data[data_key] = extracted_data
                        logger.info(f"Successfully extracted data and analysis for {name}.")
                    else:
                        logger.warning(f"LLM extraction failed for {name}. Storing empty dictionary.")
                        self.financial_data[data_key] = {}
                else:
                    logger.warning(f"Could not locate {name} section. Storing empty dictionary.")
                    self.financial_data[data_key] = {}
            
            # 3. Overall Document Analysis (e.g., Management Discussion)
            logger.info("Attempting to extract Overall Document Analysis...")
            # Consider using a significant portion of the document, e.g., first N lines or a smarter selection
            # For simplicity, using a larger chunk from the beginning, but this could be refined
            # to find specific sections like "Management Discussion" or "Report of the Directors"
            overall_context_lines = text_lines[:OVERALL_ANALYSIS_CONTEXT_LINES] # Use a larger context
            
            # Alternative: Try to find a "management discussion" like section
            # management_keywords = ["zpráva představenstva", "komentář vedení", "management discussion", "vývoj společnosti"]
            # mgmt_context_tuple = self._find_section_context(text_lines, management_keywords, 0.70, context_lines_after_override=150)
            # if mgmt_context_tuple:
            #    overall_doc_context = mgmt_context_tuple[0]
            # else: # Fallback to top N lines
            overall_doc_context = "\n".join(overall_context_lines).strip()

            if len(overall_doc_context) > MAX_CONTEXT_CHARS * 1.5: # Allow slightly more for this
                 overall_doc_context = overall_doc_context[:int(MAX_CONTEXT_CHARS * 1.5)]
                 logger.warning(f"Truncated context for Overall Document Analysis to {len(overall_doc_context)} chars.")

            if overall_doc_context:
                extracted_overall_analysis = self._call_llm_for_extraction(overall_doc_context, self.OVERALL_DOCUMENT_ANALYSIS_PROMPT, "Overall Document Analysis")
                if extracted_overall_analysis:
                    self.financial_data['document_analysis'] = extracted_overall_analysis
                    logger.info("Successfully extracted Overall Document Analysis.")
                else:
                    logger.warning("LLM extraction failed for Overall Document Analysis. Storing empty dictionary.")
                    self.financial_data['document_analysis'] = {}
            else:
                logger.warning("No context for Overall Document Analysis.")
                self.financial_data['document_analysis'] = {}


            logger.info("Financial data and insights extraction process completed (ExtractorV2).")

        except Exception as e:
            logger.error(f"Critical error during HTML processing or extraction orchestration (ExtractorV2): {e}", exc_info=True)
            # Return partially filled data or initialized data
            return self.financial_data

        return self.financial_data


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract financial data and insights from HTML files (V2)')
    parser.add_argument('input_file', help='Path to the input HTML file')
    parser.add_argument('output_file', help='Path to the output JSON file')
    parser.add_argument('--log', help='Path to log file (optional)')
    args = parser.parse_args()
    
    if args.log:
        log_dir = os.path.dirname(args.log)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(args.log, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        logger.info(f"Logging to file: {args.log}")
    
    extractor = FinancialExtractor2()
    
    try:
        if not os.path.exists(args.input_file):
            raise FileNotFoundError(f"Input file not found: {args.input_file}")
            
        logger.info(f"Reading HTML content from: {args.input_file}")
        with open(args.input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        logger.info("HTML content read successfully")

        output_dir = os.path.dirname(args.output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        logger.info("Starting extraction (V2)")
        financial_data_output = extractor.extract_from_html(html_content)
        logger.info("Extraction finished (V2)")

        logger.info(f"Saving extracted data to {args.output_file}")
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(financial_data_output, f, indent=4, ensure_ascii=False)
        logger.info("Data saved successfully")

        print("\n--- Extraction V2 Summary ---")
        print(f"Data saved to: {args.output_file}")
        for key, value in financial_data_output.items():
            has_data = bool(value and (isinstance(value, dict) and any(v is not None for v_key, v in value.items() if v_key != 'analytical_summary') or (isinstance(value.get('analytical_summary'), str) and value['analytical_summary'])))
            print(f"{key.replace('_', ' ').title()} extracted: {'Yes' if has_data else 'No'}")
            if isinstance(value, dict) and value.get('analytical_summary'):
                 print(f"  Analytical Summary for {key.replace('_', ' ').title()}: Present")
        print("------------------------\n")
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        print(f"Error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in main execution (V2): {e}", exc_info=True)
        print(f"An unexpected error occurred: {str(e)}") 