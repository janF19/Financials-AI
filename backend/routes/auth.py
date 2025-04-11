from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
import uuid
from passlib.context import CryptContext

from backend.models.user import UserCreate, UserResponse, UserUpdate, User
from backend.database import supabase
from backend.auth.dependencies import create_access_token, get_current_user
from backend.config.settings import settings

router = APIRouter(prefix="/auth", tags=["authentication"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)



#authentication flow
# User registers with email/password
# Password is hashed before storage
# User logs in with credentials
# If valid, server returns JWT token
# Client includes token in Authorization header for protected requests
# Server validates token before processing protected endpoints


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    Register a new user.
    """
    # Check if email already exists
    existing_user = supabase.table("users").select("*").eq("email", user_data.email).execute()
    
    if existing_user.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Hash the password
    hashed_password = get_password_hash(user_data.password)
    
    # Create user record
    new_user = {
        "id": str(uuid.uuid4()),
        "email": user_data.email,
        "password_hash": hashed_password,
    }
    
    response = supabase.table("users").insert(new_user).execute()
    
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )
    
    created_user = response.data[0]
    return UserResponse(
        id=created_user["id"],
        email=created_user["email"],
        created_at=created_user["created_at"],
    )


@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate user and return JWT token.
    """
    # Find user by email
    user_response = supabase.table("users").select("*").eq("email", form_data.username).execute()
    
    if not user_response.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = user_response.data[0]
    
    # Verify password
    if not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        user_id=user["id"], 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse)
async def get_user_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        created_at=current_user.created_at,
    )


@router.put("/me", response_model=UserResponse)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update current user's profile.
    """
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Hash password if it's being updated
    if "password" in update_data:
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))
    
    # Update user in database
    if update_data:
        response = supabase.table("users").update(update_data).eq("id", str(current_user.id)).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user",
            )
    
    # Get updated user data
    updated_user = supabase.table("users").select("*").eq("id", str(current_user.id)).execute().data[0]
    
    return UserResponse(
        id=updated_user["id"],
        email=updated_user["email"],
        created_at=updated_user["created_at"],
    )