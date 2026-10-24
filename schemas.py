
from datetime import datetime
from pydantic import BaseModel, EmailStr, conint , Field
from typing import Annotated, Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: Optional[int] = None


class UserOut(BaseModel):
    id: int
    email: EmailStr  
    created_at: datetime

    class Config:
        orm_mode = True  