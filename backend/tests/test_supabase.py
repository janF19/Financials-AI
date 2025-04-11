import os
import requests
import jwt
import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_supabase_connection():
    # Get Supabase credentials from environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    
    print("Testing Supabase connection...")
    
    # Test if environment variables are loaded
    if not supabase_url or not supabase_key or not jwt_secret:
        print("❌ Failed to load Supabase credentials from .env file")
        return False
    
    # Extract the project URL from the database URL
    # Convert from postgresql://user:pass@db.xyz.supabase.co:5432/postgres
    # to https://xyz.supabase.co
    try:
        # Extract the domain part
        domain_part = supabase_url.split('@')[1].split(':')[0]
        project_ref = domain_part.split('.')[1]
        api_url = f"https://{project_ref}.supabase.co"
        
        print(f"API URL: {api_url}")
        
        # Test REST API connection
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}"
        }
        
        # Try to get the health status
        response = requests.get(f"{api_url}/rest/v1/", headers=headers)
        
        if response.status_code == 200:
            print("✅ Successfully connected to Supabase REST API!")
        else:
            print(f"⚠️ Supabase REST API returned status code: {response.status_code}")
            print(f"Response: {response.text}")
        
        # Test JWT token creation with the secret
        try:
            payload = {
                "iss": "test_script",
                "sub": "test_user",
                "exp": datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(hours=1)
            }
            token = jwt.encode(payload, jwt_secret, algorithm="HS256")
            print("✅ Successfully created JWT token with the provided secret")
            
            # Verify the token
            decoded = jwt.decode(token, jwt_secret, algorithms=["HS256"])
            print("✅ Successfully verified JWT token")
            
            return True
        except Exception as e:
            print(f"❌ JWT test failed: {str(e)}")
            return False
            
    except Exception as e:
        print(f"❌ Supabase connection failed: {str(e)}")
        return False

def check_report_bucket():
    """Check if the 'reports' bucket exists in Supabase storage."""
    # Get Supabase credentials from environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    print("Checking for 'reports' bucket in Supabase storage...")
    
    # Test if environment variables are loaded
    if not supabase_url or not supabase_key:
        print("❌ Failed to load Supabase credentials from .env file")
        return False
    
    try:
        # Extract the domain part
        domain_part = supabase_url.split('@')[1].split(':')[0]
        project_ref = domain_part.split('.')[1]
        api_url = f"https://{project_ref}.supabase.co"
        
        # Set up headers for authentication
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}"
        }
        
        # Get list of buckets
        response = requests.get(f"{api_url}/storage/v1/bucket", headers=headers)
        print(f"Full response: {response.text}")
        
        if response.status_code == 200:
            buckets = response.json()
            print("All available buckets:", [bucket.get('name') for bucket in buckets])
            
            report_bucket_exists = any(bucket.get('name') in ['report', 'reports'] for bucket in buckets)
            
            if report_bucket_exists:
                print("✅ 'reports' bucket exists in Supabase storage!")
                return True
            else:
                print("❌ 'reports' bucket does not exist in Supabase storage")
                print("Available buckets:", [bucket.get('name') for bucket in buckets])
                return False
        else:
            print(f"⚠️ Failed to get buckets list. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking for 'reports' bucket: {str(e)}")
        return False

if __name__ == "__main__":
    test_supabase_connection()
    check_report_bucket()