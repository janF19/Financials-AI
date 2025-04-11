import os
import logging
from supabase import create_client, Client
from backend.config.settings import settings

logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    """
    Create and return a Supabase client using the configuration from settings.
    """
    try:
        supabase: Client = create_client(
            settings.SUPABASE_URL, 
            settings.SUPABASE_KEY
        )
        return supabase
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {str(e)}")
        raise e

# Create a global supabase client
supabase = get_supabase_client()