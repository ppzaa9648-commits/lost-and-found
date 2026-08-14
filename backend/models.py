from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class SuperAdminLogin(BaseModel):
    email: str
    password: str

class PostCreate(BaseModel):
    type: str # 'lost' or 'found'
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    location: str
    lost_found_date: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[str] = "pending" # 'pending', 'published', 'claimed'

class PostUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    reason: Optional[str] = None

class MessageCreate(BaseModel):
    receiver_id: str
    post_id: Optional[str] = None
    message: str
