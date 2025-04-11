from typing import Optional
from uuid import UUID

from backend.models.user import User
from backend.database import supabase

class UserService:
    """Service for user-related database operations."""
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get a user by their ID.
        
        Args:
            user_id: The user's UUID
            
        Returns:
            User object if found, None otherwise
        """
        user_response = supabase.table("users").select("*").eq("id", user_id).execute()
        
        if not user_response.data:
            return None
            
        return User(**user_response.data[0])
