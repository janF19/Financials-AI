import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def check_or_create_execute_sql_function(supabase: Client):
    """
    Checks if the execute_sql helper function exists by trying to call it.
    If it doesn't exist, provides instructions for manual creation.
    """
    print("Checking if execute_sql helper function exists...")
    test_sql = "SELECT 1;" # A simple command to test the function call
    function_sql_to_create = """
    CREATE OR REPLACE FUNCTION public.execute_sql(sql_command text)
    RETURNS void
    LANGUAGE plpgsql
    SECURITY DEFINER -- Allows execution with definer's privileges (service_role)
    AS $$
    BEGIN
        EXECUTE sql_command;
    END;
    $$;
    """
    try:
        # Try calling the function with a simple command
        supabase.rpc('execute_sql', {'sql_command': test_sql}).execute()
        # If the above line doesn't raise an exception, the function exists and is callable
        print("✅ Helper function execute_sql exists and is callable.")
        return True # Indicate success
    except Exception as e:
        # Check if the specific error is "Could not find the function"
        # The exact error message might vary slightly depending on client/server versions
        error_str = str(e).lower()
        if 'could not find the function public.execute_sql' in error_str or \
           'function public.execute_sql(' in error_str and ') does not exist' in error_str:

            print("❌ Helper function 'execute_sql' not found or not callable.")
            print("   Please run the following SQL manually ONCE in your Supabase SQL Editor:")
            print("--------------------------------------------------")
            print(function_sql_to_create)
            print("--------------------------------------------------")
            # Raise an exception to stop the script because the function is required
            raise Exception("Helper function 'execute_sql' needs to be created manually before proceeding.") from e
        else:
            # It failed for a different reason (permissions, network, etc.)
            print(f"⚠️ An unexpected error occurred while checking for execute_sql function: {e}")
            # Raise a different exception or handle as appropriate
            raise Exception("Failed to verify execute_sql helper function due to an unexpected error.") from e

def setup_database_schema(supabase: Client):
    """Creates or updates the necessary tables, adding usage columns to public.users."""
    print("Setting up database schema using existing public.users table...")

    # --- Users Table (Modify existing definition) ---
    # Add API usage tracking columns directly to public.users
    # NOTE: Assumes public.users already exists or is created elsewhere with
    #       at least 'id UUID PRIMARY KEY' and 'email TEXT UNIQUE NOT NULL'.
    #       This script will just add the columns if the table exists.
    users_table_sql = """
    DO $$
    BEGIN
        -- Check if the table exists before trying to alter it
        IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users') THEN
            -- Add columns if they don't exist
            ALTER TABLE public.users
            ADD COLUMN IF NOT EXISTS api_calls_this_month INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS api_calls_month_start DATE;

            -- You might need other columns here based on your original definition
            -- ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_hash TEXT;
            -- ALTER TABLE public.users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

            -- Ensure email has a UNIQUE constraint if not already set
            -- ALTER TABLE public.users ADD CONSTRAINT users_email_key UNIQUE (email);

            RAISE NOTICE 'Columns added/ensured on public.users table.';
        ELSE
            -- Optionally, create the table if it truly doesn't exist,
            -- but the user indicated it does. Add necessary columns.
            -- RAISE NOTICE 'Table public.users does not exist. Creating it.';
            -- CREATE TABLE public.users (
            --     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            --     email TEXT UNIQUE NOT NULL,
            --     password_hash TEXT NOT NULL, -- If you store hashes here
            --     created_at TIMESTAMPTZ DEFAULT NOW(),
            --     api_calls_this_month INTEGER NOT NULL DEFAULT 0,
            --     api_calls_month_start DATE
            -- );
            RAISE WARNING 'Table public.users not found. Columns not added. Please ensure it exists.';
        END IF;
    END $$;
    """
    try:
        # Now call the execute_sql function we created (or assume exists)
        supabase.rpc('execute_sql', {'sql_command': users_table_sql}).execute()
        print("✅ Ensured API usage columns on public.users table.")
    except Exception as e:
        print(f"⚠️ Error altering public.users table via RPC: {e}")
        print("   (Ensure the execute_sql function exists and the service key has permissions)")

    # --- Row Level Security (RLS) for public.users (Example) ---
    # This is more complex as we need to link via email potentially
    # Basic example: Allow users to see/update their own row based on email match
    # WARNING: This assumes email in public.users matches auth.users.email()
    #          Consider security implications carefully.
    users_rls_sql = """
    DO $$ BEGIN ALTER TABLE public.users ENABLE ROW LEVEL SECURITY; EXCEPTION WHEN duplicate_object THEN RAISE NOTICE 'RLS already enabled on public.users'; END $$;
    DROP POLICY IF EXISTS "Users can view their own user record by email" ON public.users;
    DROP POLICY IF EXISTS "Users can update their own user record by email" ON public.users;
    DROP POLICY IF EXISTS "Allow backend service role access" ON public.users;
    CREATE POLICY "Users can view their own user record by email" ON public.users FOR SELECT USING ( email = auth.email() );
    CREATE POLICY "Users can update their own user record by email" ON public.users FOR UPDATE USING ( email = auth.email() ) WITH CHECK ( email = auth.email() );
    CREATE POLICY "Allow backend service role access" ON public.users FOR ALL USING ( TRUE ) WITH CHECK ( TRUE );
    """
    try:
        supabase.rpc('execute_sql', {'sql_command': users_rls_sql}).execute()
        print("✅ Applied basic Row Level Security policies for public.users.")
    except Exception as e:
        print(f"⚠️ Error applying RLS for public.users via RPC: {e}")

    # --- Reports Table ---
    # Ensure it references YOUR public.users table's ID
    reports_table_sql = """
    CREATE TABLE IF NOT EXISTS public.reports (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE, -- References YOUR users table
        file_name TEXT,
        report_url TEXT,
        original_file_path TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        status TEXT NOT NULL DEFAULT 'pending',
        error_message TEXT,
        ico TEXT
    );
    """
    try:
        supabase.rpc('execute_sql', {'sql_command': reports_table_sql}).execute()
        print("✅ Ensured reports table exists (references public.users).")
    except Exception as e:
        print(f"⚠️ Error creating/updating reports table via RPC: {e}")

    # --- RLS for Reports (Example - Referencing public.users) ---
    # This policy assumes the user_id in reports matches the id in public.users,
    # and we check if the logged-in user's email matches the email in the referenced public.users row.
    reports_rls_sql = """
    DO $$ BEGIN ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY; EXCEPTION WHEN duplicate_object THEN RAISE NOTICE 'RLS already enabled on public.reports'; END $$;
    DROP POLICY IF EXISTS "Users can manage reports linked to their public user record" ON public.reports;
    DROP POLICY IF EXISTS "Allow backend service role access" ON public.reports;
    CREATE POLICY "Users can manage reports linked to their public user record" ON public.reports FOR ALL USING ( auth.email() = (SELECT email FROM public.users WHERE id = user_id) ) WITH CHECK ( auth.email() = (SELECT email FROM public.users WHERE id = user_id) );
    CREATE POLICY "Allow backend service role access" ON public.reports FOR ALL USING ( TRUE ) WITH CHECK ( TRUE );
    """
    try:
        supabase.rpc('execute_sql', {'sql_command': reports_rls_sql}).execute()
        print("✅ Applied Row Level Security policies for reports (linked to public.users).")
    except Exception as e:
        print(f"⚠️ Error applying RLS for reports via RPC: {e}")

    # --- Remove Profile Trigger Function and Trigger ---
    # (No longer needed as we're not using a separate profiles table)
    drop_trigger_sql = """
    DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
    """
    drop_function_sql = """
    DROP FUNCTION IF EXISTS public.handle_new_user();
    """
    try:
        # It's okay if these don't exist, so ignore errors cautiously
        supabase.rpc('execute_sql', {'sql_command': drop_trigger_sql}).execute()
        print("✅ Ensured profile creation trigger is removed.")
    except Exception:
        print("ℹ️ Profile creation trigger likely did not exist or drop failed.")
    try:
        supabase.rpc('execute_sql', {'sql_command': drop_function_sql}).execute()
        print("✅ Ensured profile creation function is removed.")
    except Exception:
        print("ℹ️ Profile creation function likely did not exist or drop failed.")


    print("✅ Database schema setup complete attempt (using public.users).")
    return True


if __name__ == "__main__":
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    print("Running database setup script (modifying public.users)...")

    if not supabase_url or not supabase_key:
        print("❌ Failed to load Supabase URL and SERVICE KEY from .env file")
        print("   Ensure SUPABASE_URL and SUPABASE_SERVICE_KEY are set correctly.")
    else:
        try:
            supabase: Client = create_client(supabase_url, supabase_key)
            print("Supabase client initialized.")

            # --- Check if the helper function exists ---
            # This will raise an exception if manual creation is needed
            check_or_create_execute_sql_function(supabase)
            # ---

            # Run the main setup function
            setup_database_schema(supabase)

        except Exception as e:
            print(f"❌ An error occurred during setup: {str(e)}")
            # If the error was about creating the helper function manually,
            # the script might have already stopped inside check_or_create_execute_sql_function.