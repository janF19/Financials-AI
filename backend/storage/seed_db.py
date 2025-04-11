import os
import requests
from dotenv import load_dotenv

load_dotenv()


def create_database_tables():
    """Create the necessary tables in Supabase database."""
    # Get Supabase credentials from environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    print("Creating database tables...")
    
    # Test if environment variables are loaded
    if not supabase_url or not supabase_key:
        print("❌ Failed to load Supabase credentials from .env file")
        return False
    
    try:
        # Use the URL directly since it's already in the correct format
        api_url = supabase_url.rstrip('/')
        
        # Set up headers for authentication
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        # SQL to create users table
        users_table_sql = """
        CREATE TABLE IF NOT EXISTS public.users (
            id UUID PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
        
        # SQL to create reports table
        reports_table_sql = """
        CREATE TABLE IF NOT EXISTS public.reports (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES public.users(id),
            file_name TEXT NOT NULL,
            report_url TEXT NOT NULL,
            original_file_path TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            status TEXT NOT NULL DEFAULT 'processed'
        );
        """
        
        # Execute SQL queries using the REST API
        response = requests.post(
            f"{api_url}/rest/v1/rpc/execute_sql",
            headers=headers,
            json={"sql": users_table_sql}
        )
        
        if response.status_code in [200, 201, 204]:
            print("✅ Successfully created users table!")
        else:
            print(f"⚠️ Failed to create users table. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        response = requests.post(
            f"{api_url}/rest/v1/rpc/execute_sql",
            headers=headers,
            json={"sql": reports_table_sql}
        )
        
        if response.status_code in [200, 201, 204]:
            print("✅ Successfully created reports table!")
            return True
        else:
            print(f"⚠️ Failed to create reports table. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating database tables: {str(e)}")
        return False

# Add this to the if __name__ == "__main__" block


from supabase import create_client

def create_database_tables_with_client():
    """Create the necessary tables using the Supabase client."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    print("Creating database tables with Supabase client...")
    
    if not supabase_url or not supabase_key:
        print("❌ Failed to load Supabase credentials from .env file")
        return False
    
    try:
        # Initialize Supabase client
        supabase = create_client(supabase_url, supabase_key)
        
        # SQL to create users table
        users_table_sql = """
        CREATE TABLE IF NOT EXISTS public.users (
            id UUID PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
        
        # SQL to create reports table
        reports_table_sql = """
        CREATE TABLE IF NOT EXISTS public.reports (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES public.users(id),
            file_name TEXT NOT NULL,
            report_url TEXT NOT NULL,
            original_file_path TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            status TEXT NOT NULL DEFAULT 'processed'
        );
        """
        
        # Execute SQL queries
        supabase.table("users").execute_sql(users_table_sql)
        print("✅ Successfully created users table!")
        
        supabase.table("reports").execute_sql(reports_table_sql)
        print("✅ Successfully created reports table!")
        
        return True
            
    except Exception as e:
        print(f"❌ Error creating database tables: {str(e)}")
        return False
    
    
if __name__ == "__main__":
    
    #create_database_tables()  # Add this line
    create_database_tables_with_client()