import datetime
from uuid import UUID
from fastapi import HTTPException, status
import logging

from backend.database import supabase
from backend.config import settings

logger = logging.getLogger(__name__)

def check_and_increment_api_usage(user_id: UUID):
    """
    Checks if the user is within their monthly API call limit.
    If yes, increments the count. If no, raises HTTPException 429.

    Assumes a 'profiles' table linked to 'auth.users' with columns:
    - id (UUID, FK to auth.users.id)
    - api_calls_this_month (INTEGER)
    - api_calls_month_start (DATE)
    """
    try:
        today = datetime.date.today()
        current_month_start = today.replace(day=1)
        limit = settings.USER_API_CALL_LIMIT_PER_MONTH

        # Fetch current usage data for the user
        # Ensure you select from your actual user profile table name
        profile_query = supabase.table("profiles").select("api_calls_this_month", "api_calls_month_start").eq("id", str(user_id)).maybe_single().execute()

        profile_data = profile_query.data
        current_calls = 0
        db_month_start = None

        if profile_data:
            current_calls = profile_data.get("api_calls_this_month", 0)
            db_month_start_str = profile_data.get("api_calls_month_start")
            if db_month_start_str:
                try:
                    # Supabase might return date as string 'YYYY-MM-DD'
                    db_month_start = datetime.date.fromisoformat(db_month_start_str)
                except (ValueError, TypeError):
                     logger.warning(f"Could not parse date '{db_month_start_str}' for user {user_id}. Resetting count.")
                     db_month_start = None # Treat as needing reset

        # Check if we need to reset the count for a new month
        if db_month_start != current_month_start:
            logger.info(f"Resetting API call count for user {user_id} for month {current_month_start.isoformat()}")
            current_calls = 0
            update_data = {
                "api_calls_this_month": 0,
                "api_calls_month_start": current_month_start.isoformat()
            }
            # Update month start and reset count to 0 before checking limit
            supabase.table("profiles").update(update_data).eq("id", str(user_id)).execute()
            # No need to handle error here specifically, subsequent check will work

        # Check limit
        if current_calls >= limit:
            logger.warning(f"User {user_id} exceeded API limit of {limit} calls for month {current_month_start.isoformat()}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"You have reached your monthly limit of {limit} report processing calls."
            )

        # Increment the count for this call
        # Use current_calls + 1 because we reset it to 0 if it was a new month
        new_count = current_calls + 1
        update_data = {
            "api_calls_this_month": new_count,
            "api_calls_month_start": current_month_start.isoformat() # Ensure month start is set
        }
        logger.info(f"Incrementing API call count for user {user_id} to {new_count} for month {current_month_start.isoformat()}")
        supabase.table("profiles").update(update_data).eq("id", str(user_id)).execute()

        # If we reached here, the user is within limits and count is incremented
        return True

    except HTTPException as http_exc:
        # Re-raise the specific 429 exception
        raise http_exc
    except Exception as e:
        logger.error(f"Error checking/incrementing API usage for user {user_id}: {e}", exc_info=True)
        # Fail open or closed? Failing closed (denying request) is safer for costs.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not verify API usage limits. Please try again later."
        ) 