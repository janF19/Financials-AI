from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

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
    
    # Workflow Settings
  
    
    # API Keys
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # NEW: API Call Limit
    USER_API_CALL_LIMIT_PER_MONTH: int = int(os.getenv("USER_API_CALL_LIMIT_PER_MONTH", 5)) # Default to 5

    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your_jwt_secret")
    REPORT_ARCHIVE_PATH: str = os.getenv("REPORT_ARCHIVE_PATH", "backend/storage/archived_reports")
    MAX_API_CALLS_PER_MONTH: int = int(os.getenv("MAX_API_CALLS_PER_MONTH", 100))

    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = 'ignore' # Ignore extra fields from environment variables


settings = Settings()

# Ensure temp directory exists
Path(settings.TEMP_STORAGE_PATH).mkdir(parents=True, exist_ok=True)

# Validate required API keys
if not settings.MISTRAL_API_KEY and not settings.OPENAI_API_KEY:
    raise ValueError("MISTRAL_API_KEY and OPENAI_API_KEY must be provided")