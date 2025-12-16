from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .user import UserResponseSchema

class HootCreate(BaseModel):
    """Schema for creating a new hoot"""
    title: str = Field(..., min_length=1, max_length=255, description="Title of the hoot")
    text: str = Field(..., min_length=1, description="Content of the hoot")
    category: str = Field(..., min_length=1, max_length=50, description="Category (e.g., news, sports, tech)")

    class Config:
        schema_extra = {
            "example": {
                "title": "My First Hoot!",
                "text": "This is an amazing post about Python and FastAPI.",
                "category": "tech"
            }
        }

class HootUpdate(BaseModel):
    """Schema for updating a hoot (all fields optional)"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    text: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, min_length=1, max_length=50)

class CommentSchema(BaseModel):
    """Basic comment schema for nested display"""
    id: int
    text: str
    user: UserResponseSchema
    created_at: datetime

    class Config:
        orm_mode = True

class HootSchema(BaseModel):
    """Schema for returning hoot data"""
    id: int
    title: str
    text: str
    category: str
    created_at: datetime
    user: UserResponseSchema
    comments: List[CommentSchema] = []

    class Config:
        orm_mode = True