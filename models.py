from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, UniqueConstraint
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default='USER')
    created_at = Column(DateTime, server_default=func.now())

class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String, nullable=False)
    location = Column(String, nullable=False)
    event_date = Column(DateTime, nullable=False)
    ticket_price = Column(Float, nullable=False)
    banner_image = Column(String)
    organizer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    # NULL on existing events: organizer must configure the actual capacity.
    total_tickets = Column(Integer, nullable=True)
    reserved_tickets = Column(Integer, nullable=False, default=0, server_default='0')

class Booking(Base):
    __tablename__ = 'bookings'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    ticket_quantity = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    booking_status = Column(String, default='PENDING')
    created_at = Column(DateTime, server_default=func.now())

class Ticket(Base):
    __tablename__ = 'tickets'
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False)
    ticket_code = Column(String, unique=True, nullable=False)
    qr_code_url = Column(String)
    created_at = Column(DateTime, server_default=func.now())

class Notification(Base):
    __tablename__ = 'notifications'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

class Review(Base):
    __tablename__ = 'reviews'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class Payment(Base):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), unique=True, nullable=False)
    payment_method = Column(String, nullable=False)
    payment_status = Column(String, nullable=False, default='PENDING')
    transaction_id = Column(String, unique=True)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class Coupon(Base):
    __tablename__ = 'coupons'
    id = Column(Integer, primary_key=True, index=True)
    coupon_code = Column(String, unique=True, index=True, nullable=False)
    discount_type = Column(String, nullable=False)
    discount_value = Column(Float, nullable=False)
    minimum_booking_amount = Column(Float, nullable=False, default=0)
    expiry_date = Column(DateTime, nullable=False)
    usage_limit = Column(Integer, nullable=False)
    used_count = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class CouponRedemption(Base):
    __tablename__ = 'coupon_redemptions'
    id = Column(Integer, primary_key=True, index=True)
    coupon_id = Column(Integer, ForeignKey('coupons.id'), nullable=False)
    booking_id = Column(Integer, ForeignKey('bookings.id'), unique=True, nullable=False)
    discount_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class Wishlist(Base):
    __tablename__ = 'wishlist'
    __table_args__ = (UniqueConstraint('user_id', 'event_id'),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class EventUpdate(Base):
    __tablename__ = 'event_updates'
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False, index=True)
    message = Column(Text, nullable=False)
    important = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class EventView(Base):
    __tablename__ = 'event_views'
    __table_args__ = (UniqueConstraint('user_id', 'event_id'),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
