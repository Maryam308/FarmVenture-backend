from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Union
from datetime import datetime
from .product import ProductSchema
from .activity import ActivitySchema

class FavoriteCreate(BaseModel):
    """Schema for creating a favorite"""
    item_id: int = Field(..., description="ID of the product or activity")
    item_type: str = Field(..., description="Type: 'product' or 'activity'")
    
    model_config = ConfigDict(from_attributes=True)

class FavoriteResponse(BaseModel):
    """Schema for returning favorite data"""
    id: int
    user_id: int
    item_id: int
    item_type: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class FavoriteWithDetails(BaseModel):
    """Schema for returning favorite with item details"""
    id: int
    user_id: int
    item_id: int
    item_type: str
    created_at: datetime
    item: Union[ProductSchema, ActivitySchema, dict]
    
    model_config = ConfigDict(from_attributes=True)