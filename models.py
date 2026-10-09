from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
)
from sqlalchemy.sql import func
from database import Base


# ================= USER =================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(
        String,
        unique=True,
        nullable=False,
    )
    email = Column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password = Column(
        String,
        nullable=False,
    )

    # USER / ORGANIZER / ADMIN
    role = Column(
        String,
        nullable=False,
        default="USER",
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
    )


# ================= EVENT =================

class Event(Base):
    __tablename__ = "events"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    title = Column(
        String,
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    category = Column(
        String,
        nullable=False,
    )

    location = Column(
        String,
        nullable=False,
    )

    event_date = Column(
        DateTime,
        nullable=False,
    )

    ticket_price = Column(
        Float,
        nullable=False,
    )

    banner_image = Column(
        String,
        nullable=True,
    )

    # Organizer who created the event
    organizer_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
    )


# ================= BOOKING =================

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    event_id = Column(
        Integer,
        ForeignKey("events.id"),
        nullable=False,
    )

    ticket_quantity = Column(
        Integer,
        nullable=False,
    )

    total_price = Column(
        Float,
        nullable=False,
    )

    booking_status = Column(
        String,
        default="PENDING",
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
    )


# ================= TICKET =================

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    booking_id = Column(
        Integer,
        ForeignKey("bookings.id"),
        nullable=False,
    )

    ticket_code = Column(
        String,
        unique=True,
        nullable=False,
    )

    qr_code_url = Column(
        String,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
    )


# ================= NOTIFICATION =================

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    title = Column(
        String,
        nullable=False,
    )

    message = Column(
        Text,
        nullable=False,
    )

    type = Column(
        String,
        nullable=False,
    )

    is_read = Column(
        Boolean,
        default=False,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
    )