from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


# ================= USER =================

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "USER"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


# ================= EVENT =================

class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: str
    location: str
    event_date: datetime
    ticket_price: float = Field(ge=0)
    banner_image: Optional[str] = None


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    event_date: Optional[datetime] = None
    ticket_price: Optional[float] = Field(
        default=None,
        ge=0,
    )
    banner_image: Optional[str] = None


class EventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    category: str
    location: str
    event_date: datetime
    ticket_price: float
    banner_image: Optional[str] = None
    organizer_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ================= BOOKING =================

class BookingCreate(BaseModel):
    event_id: int
    ticket_quantity: int = Field(gt=0)


class BookingResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    ticket_quantity: int
    total_price: float
    booking_status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ================= ROLE UPDATE =================

class UserRoleUpdate(BaseModel):
    role: str