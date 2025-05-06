from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
import logging

from backend.config import settings
from backend.database import supabase # Assuming supabase client is initialized here or accessible
from backend.models.user import User, TokenData
from backend.utils.usage_limiter import check_and_increment_api_usage # Import the updated function

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token") # Adjust tokenUrl if needed

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # In Supabase, the JWT secret is needed for verification
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub") # 'sub' usually holds the user ID
        if user_id is None:
            logger.warning("Token payload missing 'sub' (user ID)")
            raise credentials_exception

        # --- Query YOUR public.users table ---
        # This assumes your JWT 'sub' claim contains the ID from public.users
        response = supabase.table("users").select("*").eq("id", user_id).maybe_single().execute()

        if not response.data:
            logger.error(f"User with ID {user_id} found in token but not in public.users table.")
            raise credentials_exception # Or potentially a 404/403

        # Validate data against your User model (optional but good practice)
        try:
            user = User(**response.data)
        except ValidationError as e:
             logger.error(f"Data validation error for user {user_id}: {e}")
             raise HTTPException(status_code=500, detail="Error processing user data.")

        return user

    except JWTError as e:
        logger.error(f"JWT Error: {e}", exc_info=True)
        raise credentials_exception
    except Exception as e:
        # Catch other potential errors (e.g., database connection)
        logger.error(f"Error fetching user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving user information.")


# --- New Dependency for API Usage Check ---
async def check_api_usage(current_user: User = Depends(get_current_user)):
    """
    Dependency that checks API usage limits by calling the utility function.
    Relies on get_current_user to provide the necessary User object.
    Raises HTTPException 429 if the limit is exceeded.
    """
    try:
        # Call the utility function, passing the user object
        check_and_increment_api_usage(current_user)
        # If it doesn't raise an exception, usage is okay
        return True # Or return nothing, the check happens via exception
    except HTTPException as http_exc:
        # Re-raise the specific exception (e.g., 429 Too Many Requests)
        # from check_and_increment_api_usage
        raise http_exc
    except Exception as e:
        # Handle unexpected errors during the check
        logger.error(f"Unexpected error during API usage check for user {current_user.email}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify API usage limits."
        )
# --- 