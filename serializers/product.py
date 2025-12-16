from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .user import UserResponseSchema

class ProductCreate(BaseModel):
    """Schema for creating a new product"""
    name: str = Field(..., min_length=1, max_length=100, description="Name of the product")
    description: str = Field(..., max_length=500, description="Description of the product")
    price: float = Field(..., gt=0, description="Price of the product")
    category: str = Field(..., min_length=1, max_length=50, description="Category (e.g., fruits, vegetables, dairy)")
    image_url: Optional[str] = Field(None, max_length=500, description="Product image URL")
    # is_active is not included here - new products are always active

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "name": "Organic Apples",
                "description": "Fresh organic apples from local farm",
                "price": 4.99,
                "category": "fruits",
                "image_url": "https://res.cloudinary.com/cloudname/image/upload/v1/farmventure/products/apples.jpg"
            }
        }

class ProductUpdate(BaseModel):
    """Schema for updating a product (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, gt=0)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    image_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = Field(None, description="Set product as active or inactive")

    class Config:
        from_attributes = True

class ProductSchema(BaseModel):
    """Schema for returning product data"""
    id: int
    name: str
    description: str
    price: float
    category: str
    image_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    user: UserResponseSchema

    class Config:
        from_attributes = True