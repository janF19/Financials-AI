from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
import os
import logging
from pydantic import Field

load_dotenv()

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # API Settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 1 day
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_JWT_SECRET: Optional[str] = os.getenv("SUPABASE_JWT_SECRET")
    
    # Storage Settings
    STORAGE_BUCKET: str = os.getenv("STORAGE_BUCKET", "reports")
    TEMP_STORAGE_PATH: str = os.getenv("TEMP_STORAGE_PATH", "backend/temp")
    
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Optional: Local path for archiving reports, if used
    REPORT_ARCHIVE_PATH: Optional[str] = os.getenv("REPORT_ARCHIVE_PATH")
    
    # API Keys for external services
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # User API Call Limit (ensure this matches your .env and usage_limiter logic)
    USER_API_CALL_LIMIT_PER_MONTH: int = int(os.getenv("USER_API_CALL_LIMIT_PER_MONTH", 5))

    # Celery Configuration
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # New settings for token limiting
    USER_TOKEN_LIMIT_PER_MONTH: int = os.getenv("USER_TOKEN_LIMIT_PER_MONTH", 1000000)
    
    MAX_OUTPUT_TOKENS_GEMINI: int = os.getenv("MAX_OUTPUT_TOKENS_GEMINI", 2048)
    
    
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = 'ignore' # Ignore extra fields from environment variables


settings = Settings()

# Ensure temp directory exists
Path(settings.TEMP_STORAGE_PATH).mkdir(parents=True, exist_ok=True)

# Optional: Ensure report archive directory exists if path is set
if settings.REPORT_ARCHIVE_PATH:
    Path(settings.REPORT_ARCHIVE_PATH).mkdir(parents=True, exist_ok=True)

# Validate required API keys (OpenAI or Mistral)
if not settings.MISTRAL_API_KEY and not settings.OPENAI_API_KEY:
    # You might want to allow one or the other, or make one strictly required.
    # For now, let's assume at least one should be present if they are used.
    # Adjust this logic based on your application's actual needs.
    logger.warning("Neither MISTRAL_API_KEY nor OPENAI_API_KEY are set. Some features might not work.")
    # raise ValueError("At least one of MISTRAL_API_KEY or OPENAI_API_KEY must be provided if used by the application")

if not settings.GOOGLE_API_KEY:
    logger.error("GOOGLE_API_KEY is not set. Chat functionality will not work.")
    raise ValueError("GOOGLE_API_KEY must be configured in .env for chat features.")

if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured in .env")

if not settings.SECRET_KEY == "default_secret_key_please_change" and settings.SECRET_KEY: # Check if it's not the default and not empty
    pass
else:
    logger.warning("SECRET_KEY is not set or is using the default. Please set a strong secret key in your .env file for production.")
    if settings.DEBUG is False: # Stricter check for production
         raise ValueError("SECRET_KEY must be set to a strong value in production.")