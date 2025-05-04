

# test_scraper.py
import logging
from backend.searching.scraping_scripts.ico_file_scraper import get_latest_financial_document

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Test ICO
ico = 47679191  # Replace with the ICO you want to test

# Run the function
file_content, filename, year = get_latest_financial_document(ico)

if file_content:
    print(f"Successfully retrieved document: {filename} from year {year}")
    print(f"File size: {len(file_content)} bytes")
    print(f"First 20 bytes: {file_content[:20]}")
    
    # Save the file for inspection
    with open(f"test_download_{ico}.pdf", "wb") as f:
        f.write(file_content)
    print(f"Saved file to test_download_{ico}.pdf")
else:
    print(f"Failed to retrieve document for ICO {ico}")