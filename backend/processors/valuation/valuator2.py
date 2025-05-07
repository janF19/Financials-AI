from typing import Dict, Any, Tuple
import logging
import re

logger = logging.getLogger(__name__)

class CompanyValuator2:
    def __init__(self, financial_data: Dict[str, Any]):
        self.financial_data = financial_data
        # Ensure financial_data has the expected structure, even if keys are missing
        self.financial_data.setdefault('information', {})
        self.financial_data.setdefault('income_statement', {})
    
    def get_multiples(self, industry: str) -> Tuple[float, float]:
        """
        Returns EV/EBITDA and EV/EBIT multiples for a given industry from hardcoded Damodaran data.
        Uses January 2025 data for "All firms" category.
        """
        normalized_industry = industry.lower().strip() if industry else "unknown"
        
        industry_multiples = {
            "advertising": (11.52, 14.65), "aerospace/defense": (19.24, 23.33),
            "air transport": (7.82, 12.40), "apparel": (12.56, 15.35),
            "auto & truck": (5.50, 8.99), "auto parts": (5.44, 9.73),
            "beverage (alcoholic)": (9.70, 12.20), "beverage (soft)": (13.19, 17.16),
            "broadcasting": (7.87, 8.75), "building materials": (13.90, 17.57),
            "business & consumer services": (13.96, 18.16), "cable tv": (7.25, 34.32),
            "chemical (basic)": (15.89, 44.60), "chemical (diversified)": (7.93, 23.12),
            "chemical (specialty)": (15.23, 23.73), "coal & related energy": (6.02, 5.81),
            "computer services": (14.77, 17.42), "computers/peripherals": (17.37, 20.48),
            "construction supplies": (8.46, 11.31), "diversified": (8.98, 8.11),
            "drugs (pharmaceutical)": (12.70, 14.80), "education": (14.98, 18.18),
            "electrical equipment": (20.97, 25.35), "electronics (general)": (14.86, 18.32),
            "engineering/construction": (8.56, 12.15), "entertainment": (33.45, 52.74),
            "environmental & waste services": (9.41, 14.41), "farming/agriculture": (9.16, 13.58),
            "financial svcs. (non-bank & insurance)": (79.73, 88.79), "food processing": (11.38, 15.30),
            "food wholesalers": (8.18, 20.70), "furn/home furnishings": (9.54, 23.01),
            "green & renewable energy": (11.23, 18.44), "healthcare products": (18.96, 26.70),
            "healthcare support services": (13.04, 18.14), "heathcare information and technology": (18.83, 30.25),
            "homebuilding": (10.00, 11.20), "hospitals/healthcare facilities": (15.20, 29.72),
            "hotel/gaming": (13.76, 18.14), "household products": (15.31, 16.89),
            "information services": (5.97, 8.61), "insurance (general)": (8.52, 7.41),
            "insurance (life)": (11.91, 10.90), "insurance (prop/cas.)": (12.67, 11.00),
            "investments & asset management": (17.05, 14.70), "machinery": (12.80, 16.16),
            "metals & mining": (5.51, 9.01), "office equipment & services": (6.45, 9.08),
            "oil/gas (integrated)": (3.28, 5.96), "oil/gas (production and exploration)": (2.33, 4.09),
            "oil/gas distribution": (6.35, 8.82), "oilfield svcs/equip.": (3.19, 6.32),
            "packaging & container": (11.20, 19.42), "paper/forest products": (10.45, 15.15),
            "power": (6.86, 10.51), "precious metals": (6.84, 19.60),
            "publishing & newspapers": (10.56, 15.80), "r.e.i.t.": (22.98, 22.34),
            "real estate (development)": (26.73, 81.05), "real estate (general/diversified)": (34.05, 45.85),
            "real estate (operations & services)": (25.93, 25.65), "recreation": (11.17, 15.97),
            "reinsurance": (9.37, 8.91), "restaurant/dining": (17.29, 24.44),
            "retail (automotive)": (8.17, 19.16), "retail (building supply)": (8.83, 11.35),
            "retail (distributors)": (11.62, 15.75), "retail (general)": (22.33, 31.66),
            "retail (grocery and food)": (8.99, 13.86), "retail (reits)": (18.88, 17.95),
            "retail (special lines)": (15.44, 18.41), "rubber& tires": (5.51, 8.63),
            "semiconductor": (8.09, 14.70), "semiconductor equip": (24.90, 30.99),
            "shipbuilding & marine": (6.40, 9.99), "shoe": (21.18, 26.32),
            "software (entertainment)": (15.84, 21.64), "software (internet)": (10.62, 21.61),
            "software (system & application)": (32.83, 33.47), "steel": (4.63, 27.19),
            "telecom (wireless)": (7.44, 13.49), "telecom. equipment": (8.92, 12.59),
            "telecom. services": (7.11, 13.46), "tobacco": (7.18, 8.61),
            "transportation": (11.31, 14.95), "transportation (railroads)": (13.87, 21.24),
            "trucking": (8.12, 12.66), "utility (general)": (5.91, 9.69),
            "utility (water)": (18.11, 28.94),
        }
        
        default_ev_ebitda = 18.53  # Total Market value
        default_ev_ebit = 25.16    # Total Market value
        
        for ind, multiples in industry_multiples.items():
            if normalized_industry in ind or ind in normalized_industry:
                logger.info(f"Found industry match: '{ind}' for query '{normalized_industry}'")
                ev_ebitda, ev_ebit = multiples
                return (ev_ebitda if ev_ebitda is not None else default_ev_ebitda,
                        ev_ebit if ev_ebit is not None else default_ev_ebit)
        
        logger.warning(f"Could not find exact match for industry '{industry}'. Using market average multiples.")
        return default_ev_ebitda, default_ev_ebit
        
    def adjust_values_to_2025(self, base_year: int, amount: float) -> float:
        if not isinstance(base_year, int) or not isinstance(amount, (int, float)):
            logger.warning(f"Invalid input for inflation adjustment: year={base_year}, amount={amount}. Returning original amount.")
            return amount
        if amount is None: # Explicitly check for None
             return None

        INFLATION_DATA = {
            2019: 0.028, 2020: 0.032, 2021: 0.038,
            2022: 0.151, 2023: 0.107, 2024: 0.024 
        }
        
        target_year = 2025
        if base_year >= target_year:
            return amount
        
        inflation_factor = 1.0
        for year in range(base_year + 1, target_year + 1): # Iterate up to and including target_year
            rate = INFLATION_DATA.get(year, sum(INFLATION_DATA.values()) / len(INFLATION_DATA)) # Use average if year not in data
            inflation_factor *= (1 + rate)
        
        return amount * inflation_factor
    
    def calculate_multiples(self) -> Dict[str, Any]:
        try:
            info_data = self.financial_data.get('information', {})
            income_data = self.financial_data.get('income_statement', {})

            accounting_period_str = info_data.get('accounting_period')
            period = 2024 # Default to 2024
            if accounting_period_str:
                try:
                    # Try to extract year, e.g., from "2023" or "31.12.2023"
                    match = re.search(r'(\d{4})', str(accounting_period_str))
                    if match:
                        period = int(match.group(1))
                    else:
                        period = int(accounting_period_str) # Fallback if it's just a year
                except (ValueError, TypeError):
                    logger.warning(f"Invalid accounting period format: {accounting_period_str}. Using default year {period}.")
            else:
                logger.warning(f"Accounting period missing. Using default year {period}.")

            operating_profit = income_data.get('operating_profit_current')
            depreciation_amortization = income_data.get('depreciation_current')
            industry = info_data.get('industry', 'Unknown')
            
            logger.info(f"Valuation for industry: {industry}, period: {period}")
            
            ebit = None
            if operating_profit is not None:
                try:
                    ebit = float(operating_profit)
                except (ValueError, TypeError):
                    logger.warning(f"Operating profit '{operating_profit}' is not a valid number. EBIT set to None.")
                    ebit = None
            else:
                logger.warning("Operating profit is None. EBIT cannot be calculated.")

            ebitda = None
            if ebit is not None:
                if depreciation_amortization is not None:
                    try:
                        ebitda = ebit + float(depreciation_amortization)
                    except (ValueError, TypeError):
                        logger.warning(f"Depreciation '{depreciation_amortization}' is not a valid number. EBITDA calculated as EBIT.")
                        ebitda = ebit # Fallback: EBITDA = EBIT if depreciation is invalid
                else:
                    logger.warning("Depreciation/amortization is None. EBITDA will equal EBIT.")
                    ebitda = ebit
            else:
                logger.warning("Cannot calculate EBITDA as EBIT is None.")
            
            ebit_original_val = ebit
            ebitda_original_val = ebitda
            
            current_year_for_adjustment = 2024 # Assuming multiples are for start of 2025, so adjust up to end of 2024
            if period < current_year_for_adjustment: # Only adjust if period is before the "current" year for multiples
                if ebit is not None:
                    ebit_adjusted = self.adjust_values_to_2025(period, ebit)
                    logger.info(f"EBIT adjusted from {ebit} (year {period}) to {ebit_adjusted} (for 2025)")
                    ebit = ebit_adjusted
                if ebitda is not None:
                    ebitda_adjusted = self.adjust_values_to_2025(period, ebitda)
                    logger.info(f"EBITDA adjusted from {ebitda} (year {period}) to {ebitda_adjusted} (for 2025)")
                    ebitda = ebitda_adjusted
            
            ev_ebitda_multiple, ev_ebit_multiple = self.get_multiples(industry)

            enterprise_ebitda_value = ebitda * ev_ebitda_multiple if ebitda is not None else None
            enterprise_ebit_value = ebit * ev_ebit_multiple if ebit is not None else None

            return {
                "EBIT_original": { # Renamed for clarity
                    "value": ebit_original_val,
                    "year": period
                },
                "EBITDA_original": { # Renamed for clarity
                    "value": ebitda_original_val,
                    "year": period
                },
                "EBIT_adjusted_for_2025": ebit, # Renamed for clarity
                "EBITDA_adjusted_for_2025": ebitda, # Renamed for clarity
                "EV_EBITDA_Multiple": ev_ebitda_multiple, # Renamed for clarity
                "EV_EBIT_Multiple": ev_ebit_multiple, # Renamed for clarity
                "Enterprise_Value_based_on_EBITDA_Kč_thousands": enterprise_ebitda_value, # Renamed
                "Enterprise_Value_based_on_EBIT_Kč_thousands": enterprise_ebit_value # Renamed
            }
        except Exception as e: # Catching a broader exception for unexpected issues
            logger.error(f"Error during valuation calculation (ValuatorV2): {e}", exc_info=True)
            # Return a structure indicating failure or partial data
            return {
                "error": str(e),
                "EBIT_original": {"value": None, "year": None},
                "EBITDA_original": {"value": None, "year": None},
                "EBIT_adjusted_for_2025": None,
                "EBITDA_adjusted_for_2025": None,
                "EV_EBITDA_Multiple": None,
                "EV_EBIT_Multiple": None,
                "Enterprise_Value_based_on_EBITDA_Kč_thousands": None,
                "Enterprise_Value_based_on_EBIT_Kč_thousands": None
            }

if __name__ == "__main__":
    import os
    import json

    # Example usage:
    # Create a dummy financial_data.json for testing
    dummy_data = {
        "information": {
            "accounting_period": "2022",
            "industry": "Software (System & Application)"
        },
        "income_statement": {
            "operating_profit_current": 10000, # in thousands Kč
            "depreciation_current": 2000     # in thousands Kč
        }
    }
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # json_path = os.path.join(script_dir, 'financial_data_v2_test.json')
    # with open(json_path, 'w', encoding='utf-8') as f:
    #     json.dump(dummy_data, f, indent=4)

    # logger.info(f"Loading data from: financial_data_v2_test.json (dummy)")
    # valuator = CompanyValuator2(dummy_data)
    # result = valuator.calculate_multiples()
    # print(json.dumps(result, indent=4))

    # Test with more complex industry name
    dummy_data_complex_industry = {
        "information": {
            "accounting_period": "2023",
            "industry": "Diversified Chemical Manufacturer" # Test fuzzy matching
        },
        "income_statement": {
            "operating_profit_current": 15000,
            "depreciation_current": 3000
        }
    }
    logger.info(f"Testing complex industry name")
    valuator_complex = CompanyValuator2(dummy_data_complex_industry)
    result_complex = valuator_complex.calculate_multiples()
    print("Complex Industry Test:")
    print(json.dumps(result_complex, indent=4))

    dummy_data_missing = {
        "information": {
            "accounting_period": "2023",
            "industry": "Retail" 
        },
        "income_statement": {
            "operating_profit_current": None, # Missing data
            "depreciation_current": 1000
        }
    }
    logger.info(f"Testing missing data")
    valuator_missing = CompanyValuator2(dummy_data_missing)
    result_missing = valuator_missing.calculate_multiples()
    print("Missing Data Test:")
    print(json.dumps(result_missing, indent=4)) 