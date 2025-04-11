from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional
from uuid import UUID

from backend.models.user import User
from backend.database import supabase
from backend.config.settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Validate access token and return the current user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
        # Get user from database
        user_response = supabase.table("users").select("*").eq("id", user_id).execute()
        
        if not user_response.data:
            raise credentials_exception
            
        user_data = user_response.data[0]
        return User(**user_data)
        
    except JWTError:
        raise credentials_exception


def create_access_token(user_id: UUID, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT access token for a user.
    """
    to_encode = {"sub": str(user_id)}
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt