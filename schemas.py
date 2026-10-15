from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from datetime import datetime, timezone
from typing import Optional, Literal
class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
class UserRegister(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: str = 'USER'
class UserLogin(BaseModel):
    email: EmailStr
    password: str
class UserResponse(ORM):
    id: int
    username: str
    email: EmailStr
    role: str
    created_at: datetime
class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    category: str = Field(min_length=1, max_length=80)
    location: str = Field(min_length=1, max_length=150)
    event_date: datetime
    ticket_price: float = Field(ge=0, allow_inf_nan=False)
    banner_image: Optional[str] = None
    total_tickets: int = Field(gt=0, le=1000000)
    @field_validator('event_date')
    @classmethod
    def utc_date(cls, v):
        return v.astimezone(timezone.utc).replace(tzinfo=None) if v.tzinfo else v
class EventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, min_length=1, max_length=80)
    location: Optional[str] = Field(default=None, min_length=1, max_length=150)
    event_date: Optional[datetime] = None
    ticket_price: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    banner_image: Optional[str] = None
class EventResponse(ORM):
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
    total_tickets: Optional[int] = None
    reserved_tickets: int = 0
class BookingCreate(BaseModel):
    event_id: int = Field(gt=0)
    ticket_quantity: int = Field(gt=0, le=10000)
class BookingResponse(ORM):
    id: int
    user_id: int
    event_id: int
    ticket_quantity: int
    total_price: float
    booking_status: str
    created_at: datetime
class UserRoleUpdate(BaseModel):
    role: str
class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)
class ReviewUpdate(ReviewCreate):
    pass
class ReviewResponse(ORM):
    id: int
    user_id: int
    event_id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime
class PaymentCreate(BaseModel):
    booking_id: int = Field(gt=0)
    payment_method: str = Field(min_length=2, max_length=30)
    simulate_success: bool = True
class PaymentResponse(ORM):
    id: int
    booking_id: int
    payment_method: str
    payment_status: str
    transaction_id: Optional[str] = None
    amount: float
    created_at: datetime
class CouponCreate(BaseModel):
    coupon_code: str = Field(min_length=3, max_length=30, pattern=r'^[A-Za-z0-9_-]+$')
    discount_type: str = Field(pattern=r'^(PERCENTAGE|FIXED)$')
    discount_value: float = Field(gt=0, allow_inf_nan=False)
    minimum_booking_amount: float = Field(default=0, ge=0, allow_inf_nan=False)
    expiry_date: datetime
    usage_limit: int = Field(gt=0)
    is_active: bool = True
class CouponApply(BaseModel):
    booking_id: int = Field(gt=0)
    coupon_code: str = Field(min_length=3, max_length=30)
class CouponResponse(ORM):
    id: int
    coupon_code: str
    discount_type: str
    discount_value: float
    minimum_booking_amount: float
    expiry_date: datetime
    usage_limit: int
    used_count: int
    is_active: bool
    created_at: datetime
class ProfileEdit(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    email: EmailStr
class CapacityEdit(BaseModel):
    total_tickets: int = Field(gt=0, le=1000000)
class AnnouncementCreate(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    important: bool = False
    @field_validator('message')
    @classmethod
    def nonblank(cls, v):
        if not v.strip(): raise ValueError('Message is required')
        return v.strip()
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    location: Optional[str] = Field(default=None, max_length=150)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=12)
