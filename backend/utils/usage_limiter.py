import datetime
from uuid import UUID
from fastapi import HTTPException, status, Depends
import logging
import dotenv

from backend.database import supabase
from backend.config.settings import settings
from backend.models.user import User # Import User model if needed for auth lookup

logger = logging.getLogger(__name__)

def check_and_increment_api_usage(current_user: User):
    """
    Checks if the user (identified by email from the passed User object)
    is within their monthly API call limit stored in public.users.
    If yes, increments the count. If no, raises HTTPException 429.
    Args:
        current_user: The User object obtained from the get_current_user dependency.
    """
    try:
        # --- Step 1: Get email directly from the User object ---
        if not current_user or not current_user.email:
            logger.error(f"Invalid user object passed to usage limiter. User ID: {current_user.id if current_user else 'None'}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not verify user identity for API usage limits (invalid user data)."
            )
        user_email = current_user.email
        # Use the ID from the user object (which is the public.users ID) for logging if needed
        public_user_id_for_log = current_user.id
        logger.info(f"Checking API usage for user email: {user_email} (Public User ID: {public_user_id_for_log})")

        # --- Step 2: Find the user in public.users using the email ---
        # We still need to query public.users to get the latest API count data
        public_user_query = supabase.table("users").select("id, api_calls_this_month, api_calls_month_start").eq("email", user_email).maybe_single().execute()

        if not public_user_query.data:
            logger.error(f"No corresponding user found in public.users table for email: {user_email} (associated with Public User ID: {public_user_id_for_log})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, # Or 500
                detail="User profile not found for API usage tracking."
            )

        public_user_data = public_user_query.data
        # Use the ID fetched from this query for the update operation
        public_user_id_for_update = public_user_data["id"]
        current_calls = public_user_data.get("api_calls_this_month", 0)
        db_month_start_str = public_user_data.get("api_calls_month_start")
        db_month_start = None

        if db_month_start_str:
            try:
                db_month_start = datetime.date.fromisoformat(db_month_start_str)
            except (ValueError, TypeError):
                logger.warning(f"Could not parse date '{db_month_start_str}' for user {user_email}. Resetting count.")
                db_month_start = None

        # --- Step 3: Check and update logic ---
        today = datetime.date.today()
        current_month_start = today.replace(day=1)
        
        limit = settings.USER_API_CALL_LIMIT_PER_MONTH

        # Check if we need to reset the count for a new month
        if db_month_start != current_month_start:
            logger.info(f"Resetting API call count for user {user_email} (public ID: {public_user_id_for_update}) for month {current_month_start.isoformat()}")
            current_calls = 0
            update_data = {
                "api_calls_this_month": 0,
                "api_calls_month_start": current_month_start.isoformat()
            }
            supabase.table("users").update(update_data).eq("id", public_user_id_for_update).execute()

        # Check limit
        if current_calls >= limit:
            logger.warning(f"User {user_email} (public ID: {public_user_id_for_update}) exceeded API limit of {limit} calls for month {current_month_start.isoformat()}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"You have reached your monthly limit of {limit} processing calls." # Generic message
            )

        # Increment the count for this call
        new_count = current_calls + 1
        update_data = {
            "api_calls_this_month": new_count,
            "api_calls_month_start": current_month_start.isoformat() # Ensure month start is set
        }
        logger.info(f"Incrementing API call count for user {user_email} (public ID: {public_user_id_for_update}) to {new_count} for month {current_month_start.isoformat()}")
        supabase.table("users").update(update_data).eq("id", public_user_id_for_update).execute()

        return True # Indicate usage is okay

    except HTTPException as http_exc:
        raise http_exc # Re-raise 429 or other specific HTTP exceptions
    except Exception as e:
        # Catch potential errors during db operations
        logger.error(f"Error checking/incrementing API usage for user {current_user.email if current_user else 'UNKNOWN'}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not verify API usage limits. Please try again later."
        ) 