import requests
import json

# Base URL - change this to match your server
BASE_URL = "http://localhost:8001"

def print_response(response, description):
    print(f"\n🔍 Testing: {description}")
    print(f"Endpoint: {response.url}")
    print(f"Status code: {response.status_code}")
    
    try:
        data = response.json()
        print("Response:")
        print(json.dumps(data, indent=2))
        if response.status_code >= 400:
            print("❌ Request failed!")
        else:
            print("✅ Request successful!")
    except:
        print(f"Raw response: {response.text}")

# Authenticate and get token
print("🔑 Authenticating user...")
auth_response = requests.post(
    f"{BASE_URL}/auth/token",
    data={"username": "honza@email.com", "password": "123456789"},
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)

if auth_response.status_code != 200:
    print(f"❌ Authentication failed: {auth_response.text}")
    exit(1)

token_data = auth_response.json()
token = token_data.get("access_token")
print(f"✅ Authentication successful! Token: {token[:20]}... (truncated)")

# Set up headers with token
headers = {
    "Authorization": f"Bearer {token}"
}

# Test search by person name
person_response = requests.get(
    f"{BASE_URL}/search/person",
    params={"first_name": "Bomumír", "last_name": "Blachut"},
    headers=headers
)
print_response(person_response, "Search companies by person name")

# Test search by company name
company_response = requests.get(
    f"{BASE_URL}/search/company",
    params={"company_name": "ISOTRA"},
    headers=headers
)
print_response(company_response, "Search companies by company name")

# Test search by ICO
ico_response = requests.get(
    f"{BASE_URL}/search/ico",
    params={"ico": 47679191},
    headers=headers
)
print_response(ico_response, "Search company by ICO")

print("\n✅ All tests completed!")