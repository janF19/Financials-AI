from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)


class UserInDB(UserBase):
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class User(UserInDB):
    pass


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime