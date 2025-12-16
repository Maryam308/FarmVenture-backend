from pydantic import BaseModel

class UserSchema(BaseModel):
    username: str
    email: str
    password: str

    class Config:
        orm_mode = True

class UserResponseSchema(BaseModel):
    username: str
    email: str

# New schema for user login (captures username and password during login)
class UserLogin(BaseModel):
    username: str  # Username provided by the user during login
    password: str  # Plain text password provided by the user during login

# New schema for the response (containing the JWT token and a success message)
class UserToken(BaseModel):
    token: str  # JWT token generated upon successful login
    message: str  # Success message

    class Config:
        orm_mode = True