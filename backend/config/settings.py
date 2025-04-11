from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_JWT_SECRET: Optional[str] = None
    
    # Storage Settings
    STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", "reports")
    TEMP_STORAGE_PATH = os.getenv("TEMP_STORAGE_PATH", "backend/temp")
    
    # Workflow Settings
  
    
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Ensure temp directory exists
Path(settings.TEMP_STORAGE_PATH).mkdir(parents=True, exist_ok=True)