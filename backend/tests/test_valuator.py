
import os
import json
import unittest
from backend.processors.valuation.valuator import CompanyValuator



class ValuatorTesting(unittest.TestCase):
       
    def setUp(self):
        self.financial_data = self._read_financial_data()
        self.valuator = CompanyValuator(self.financial_data)
    
    def _read_financial_data(self):
        current_dir = os.path.dirname(__file__)
        file_path = os.path.join(current_dir, "test_files", "financial_data.json")
        
        try:
            
            with open(file_path, "r", encoding = "utf-8") as f:
                self.financial_data =  json.load(f)
        except Exception as e:
            
            print(f"Exception occured when reading file {e}")
            raise ValueError("Could not load financial data")
            
        
    def test_multiples(self):
        
        
        self.assertEqual(self.valuator.get_multiples("Advertising"), (11.52, 14.65), "the multiple calculation is wrong for Advertising")
        self.assertEqual(self.valuator.get_multiples("tobacco"), (7.18, 8.61), "the multiple calculation is wrong for tabaco")
    
    
    
    
if __name__ == '__main__':
    unittest.main()
    