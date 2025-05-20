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

# New functions for token limiting

def get_token_usage_status(current_user: User) -> tuple[UUID, int, int, str]:
    """
    Fetches the user's current token usage, handles monthly reset, and returns status.
    Returns:
        tuple: (user_db_id, current_token_usage, token_limit_per_month, current_month_start_iso)
    """
    try:
        if not current_user or not current_user.email:
            logger.error(f"Invalid user object passed to token usage checker. User ID: {current_user.id if current_user else 'None'}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not verify user identity for token usage limits (invalid user data)."
            )
        user_email = current_user.email
        public_user_id_for_log = current_user.id # This is the auth.users.id, which should match public.users.id if synced
        logger.info(f"Checking token usage for user email: {user_email} (User ID: {public_user_id_for_log})")

        # Query public.users to get token usage data
        # Ensure your public.users table has 'token_usage_this_month' (BIGINT) and 'token_usage_month_start' (DATE)
        public_user_query = supabase.table("users").select("id, token_usage_this_month, token_usage_month_start").eq("email", user_email).maybe_single().execute()

        if not public_user_query.data:
            logger.error(f"No corresponding user found in public.users table for email: {user_email} (User ID: {public_user_id_for_log})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User profile not found for token usage tracking."
            )

        public_user_data = public_user_query.data
        user_db_id = public_user_data["id"] # This is the public.users.id
        current_token_usage = public_user_data.get("token_usage_this_month", 0)
        db_month_start_str = public_user_data.get("token_usage_month_start")
        db_month_start = None

        if db_month_start_str:
            try:
                db_month_start = datetime.date.fromisoformat(db_month_start_str)
            except (ValueError, TypeError):
                logger.warning(f"Could not parse token_usage_month_start date '{db_month_start_str}' for user {user_email}. Resetting count.")
                db_month_start = None

        today = datetime.date.today()
        current_month_start = today.replace(day=1)
        token_limit = settings.USER_TOKEN_LIMIT_PER_MONTH

        if db_month_start != current_month_start:
            logger.info(f"Resetting token usage count for user {user_email} (public ID: {user_db_id}) for month {current_month_start.isoformat()}")
            current_token_usage = 0
            update_data = {
                "token_usage_this_month": 0,
                "token_usage_month_start": current_month_start.isoformat()
            }
            supabase.table("users").update(update_data).eq("id", user_db_id).execute()
            # If you want to return the very latest after reset, you could re-fetch,
            # but for this flow, returning 0 and the new month start is fine.
            db_month_start = current_month_start # Update for return value consistency

        return user_db_id, current_token_usage, token_limit, (db_month_start or current_month_start).isoformat()

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error getting token usage status for user {current_user.email if current_user else 'UNKNOWN'}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve token usage status. Please try again later."
        )

def update_user_token_usage(user_id: UUID, new_token_count: int, month_start_iso: str):
    """
    Updates the user's token usage count for the current billing month.
    Args:
        user_id: The ID of the user in the public.users table.
        new_token_count: The new total token count for the month.
        month_start_iso: The ISO format string of the start of the current billing month.
    """
    try:
        logger.info(f"Updating token usage for user ID {user_id} to {new_token_count} for month starting {month_start_iso}")
        update_data = {
            "token_usage_this_month": new_token_count,
            "token_usage_month_start": month_start_iso # Ensure this is always set
        }
        supabase.table("users").update(update_data).eq("id", user_id).execute()
    except Exception as e:
        # Log critical error, as this means usage might not be recorded correctly
        logger.critical(f"CRITICAL: Failed to update token usage for user ID {user_id} to {new_token_count}. Error: {e}", exc_info=True)
        # Depending on policy, you might not want to raise HTTPException here if the chat already succeeded,
        # but logging is essential. For now, let's re-raise to make it visible.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record token usage. Please contact support if this persists."
        ) 