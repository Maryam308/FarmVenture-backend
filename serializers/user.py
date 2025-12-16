from pydantic import BaseModel, Field
from typing import Optional
from models.user import UserRole  

class UserSchema(BaseModel):
    username: str
    email: str
    password: str
    role: Optional[UserRole] = Field(default=UserRole.CUSTOMER)  

    class Config:
        orm_mode = True
        use_enum_values = True  

class UserResponseSchema(BaseModel):
    username: str
    email: str
    role: UserRole 

    class Config:
        orm_mode = True
        use_enum_values = True

class UserLogin(BaseModel):
    username: str
    password: str

class UserToken(BaseModel):
    token: str
    message: str
    role: UserRole  

    class Config:
        orm_mode = True
        use_enum_values = True