from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import engine, Base, get_db
import models
import schemas

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


# ================= DATABASE =================

Base.metadata.create_all(bind=engine)


# ================= APP =================

app = FastAPI(
    title="SmartEvent API",
    version="2.0.0"
)

security = HTTPBearer()


# ================= HOME =================

@app.get("/")
def home():
    return {
        "message": "SmartEvent Phase 2 Backend is running"
    }


# =========================================================
# AUTH - REGISTER
# =========================================================

@app.post(
    "/auth/register",
    response_model=schemas.UserResponse,
    status_code=201,
)
def register_user(
    user: schemas.UserRegister,
    db: Session = Depends(get_db),
):
    existing_email = (
        db.query(models.User)
        .filter(models.User.email == user.email)
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    existing_username = (
        db.query(models.User)
        .filter(models.User.username == user.username)
        .first()
    )

    if existing_username:
        raise HTTPException(
            status_code=400,
            detail="Username already registered",
        )

    role = user.role.upper()

    if role not in ["USER", "ORGANIZER", "ADMIN"]:
        raise HTTPException(
            status_code=400,
            detail="Role must be USER, ORGANIZER or ADMIN",
        )

    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hash_password(user.password),
        role=role,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# =========================================================
# AUTH - LOGIN
# =========================================================

@app.post("/auth/login")
def login_user(
    user: schemas.UserLogin,
    db: Session = Depends(get_db),
):
    db_user = (
        db.query(models.User)
        .filter(models.User.email == user.email)
        .first()
    )

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not verify_password(
        user.password,
        db_user.hashed_password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    access_token = create_access_token(
        {
            "sub": str(db_user.id),
            "email": db_user.email,
            "role": db_user.role,
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": db_user.role,
    }


# =========================================================
# CURRENT USER
# =========================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    try:
        user_id = int(user_id)

    except (TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    user = (
        db.query(models.User)
        .filter(models.User.id == user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return user


# =========================================================
# ROLE DEPENDENCY
# =========================================================

def require_roles(*allowed_roles):

    def role_checker(
        current_user: models.User = Depends(get_current_user),
    ):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission",
            )

        return current_user

    return role_checker


# =========================================================
# PROFILE
# =========================================================

@app.get(
    "/auth/profile",
    response_model=schemas.UserResponse,
)
def get_profile(
    current_user: models.User = Depends(get_current_user),
):
    return current_user


# =========================================================
# PUBLIC EVENTS
# =========================================================

@app.get(
    "/events",
    response_model=list[schemas.EventResponse],
)
def get_events(
    category: str = None,
    location: str = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Event)

    if category:
        query = query.filter(
            models.Event.category == category
        )

    if location:
        query = query.filter(
            models.Event.location == location
        )

    return query.all()


@app.get(
    "/events/{event_id}",
    response_model=schemas.EventResponse,
)
def get_event_by_id(
    event_id: int,
    db: Session = Depends(get_db),
):
    event = (
        db.query(models.Event)
        .filter(models.Event.id == event_id)
        .first()
    )

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Event not found",
        )

    return event


# =========================================================
# ORGANIZER - CREATE EVENT
# =========================================================

@app.post(
    "/organizer/events",
    response_model=schemas.EventResponse,
    status_code=201,
)
def organizer_create_event(
    event: schemas.EventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles("ORGANIZER", "ADMIN")
    ),
):
    new_event = models.Event(
        title=event.title,
        description=event.description,
        category=event.category,
        location=event.location,
        event_date=event.event_date,
        ticket_price=event.ticket_price,
        banner_image=event.banner_image,
        organizer_id=current_user.id,
    )

    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    return new_event


# =========================================================
# ORGANIZER - MY EVENTS
# =========================================================

@app.get(
    "/organizer/events/my",
    response_model=list[schemas.EventResponse],
)
def organizer_get_my_events(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles("ORGANIZER")
    ),
):
    return (
        db.query(models.Event)
        .filter(
            models.Event.organizer_id == current_user.id
        )
        .all()
    )


# =========================================================
# ORGANIZER - UPDATE OWN EVENT
# =========================================================

@app.put(
    "/organizer/events/{event_id}",
    response_model=schemas.EventResponse,
)
def organizer_update_event(
    event_id: int,
    event_data: schemas.EventUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles("ORGANIZER")
    ),
):
    event = (
        db.query(models.Event)
        .filter(
            models.Event.id == event_id,
            models.Event.organizer_id == current_user.id,
        )
        .first()
    )

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Event not found or not owned by organizer",
        )

    update_data = event_data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(event, key, value)

    db.commit()
    db.refresh(event)

    return event


# =========================================================
# ORGANIZER - DELETE OWN EVENT
# =========================================================

@app.delete("/organizer/events/{event_id}")
def organizer_delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles("ORGANIZER")
    ),
):
    event = (
        db.query(models.Event)
        .filter(
            models.Event.id == event_id,
            models.Event.organizer_id == current_user.id,
        )
        .first()
    )

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Event not found or not owned by organizer",
        )

    db.delete(event)
    db.commit()

    return {
        "message": "Event deleted successfully"
    }


# =========================================================
# USER - CREATE BOOKING
# =========================================================

@app.post(
    "/bookings",
    response_model=schemas.BookingResponse,
    status_code=201,
)
def create_booking(
    booking: schemas.BookingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles("USER")
    ),
):
    event = (
        db.query(models.Event)
        .filter(
            models.Event.id == booking.event_id
        )
        .first()
    )

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Event not found",
        )

    total_price = (
        event.ticket_price *
        booking.ticket_quantity
    )

    new_booking = models.Booking(
        user_id=current_user.id,
        event_id=event.id,
        ticket_quantity=booking.ticket_quantity,
        total_price=total_price,
        booking_status="CONFIRMED",
    )

    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    return new_booking


# =========================================================
# USER - BOOKING HISTORY
# =========================================================

@app.get(
    "/bookings/my",
    response_model=list[schemas.BookingResponse],
)
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles("USER")
    ),
):
    return (
        db.query(models.Booking)
        .filter(
            models.Booking.user_id == current_user.id
        )
        .all()
    )


# =========================================================
# USER - CANCEL BOOKING
# =========================================================

@app.put(
    "/bookings/{booking_id}/cancel",
    response_model=schemas.BookingResponse,
)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles("USER")
    ),
):
    booking = (
        db.query(models.Booking)
        .filter(
            models.Booking.id == booking_id,
            models.Booking.user_id == current_user.id,
        )
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    booking.booking_status = "CANCELLED"

    db.commit()
    db.refresh(booking)

    return booking


# =========================================================
# USER - GENERATE TICKET
# =========================================================

@app.post("/bookings/{booking_id}/ticket")
def generate_ticket(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles("USER")
    ),
):
    import uuid

    booking = (
        db.query(models.Booking)
        .filter(
            models.Booking.id == booking_id,
            models.Booking.user_id == current_user.id,
        )
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    if booking.booking_status == "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail="Cancelled booking cannot generate ticket",
        )

    existing_ticket = (
        db.query(models.Ticket)
        .filter(
            models.Ticket.booking_id == booking.id
        )
        .first()
    )

    if existing_ticket:
        return existing_ticket

    ticket = models.Ticket(
        booking_id=booking.id,
        ticket_code=str(uuid.uuid4()),
        qr_code_url=None,
    )

    notification = models.Notification(
        user_id=current_user.id,
        title="Ticket Generated",
        message=(
            f"Your ticket for booking "
            f"{booking.id} is ready."
        ),
        type="BOOKING",
        is_read=False,
    )

    db.add(ticket)
    db.add(notification)
    db.commit()
    db.refresh(ticket)

    return ticket


# =========================================================
# USER - MY TICKETS
# =========================================================

@app.get("/tickets/my")
def get_my_tickets(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles("USER")
    ),
):
    return (
        db.query(models.Ticket)
        .join(
            models.Booking,
            models.Ticket.booking_id ==
            models.Booking.id,
        )
        .filter(
            models.Booking.user_id ==
            current_user.id
        )
        .all()
    )


# =========================================================
# NOTIFICATIONS
# =========================================================

@app.get("/notifications")
def get_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user
    ),
):
    return (
        db.query(models.Notification)
        .filter(
            models.Notification.user_id ==
            current_user.id
        )
        .all()
    )


@app.put(
    "/notifications/{notification_id}/read"
)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        get_current_user
    ),
):
    notification = (
        db.query(models.Notification)
        .filter(
            models.Notification.id ==
            notification_id,
            models.Notification.user_id ==
            current_user.id,
        )
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    notification.is_read = True

    db.commit()
    db.refresh(notification)

    return notification


# =========================================================
# ADMIN - GET ALL USERS
# =========================================================

@app.get(
    "/admin/users",
    response_model=list[schemas.UserResponse],
)
def admin_get_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles("ADMIN")
    ),
):
    return db.query(models.User).all()


# =========================================================
# ADMIN - CHANGE USER ROLE
# =========================================================

@app.put(
    "/admin/users/{user_id}/role",
    response_model=schemas.UserResponse,
)
def admin_change_user_role(
    user_id: int,
    role_data: schemas.UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles("ADMIN")
    ),
):
    user = (
        db.query(models.User)
        .filter(models.User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    new_role = role_data.role.upper()

    if new_role not in [
        "USER",
        "ORGANIZER",
        "ADMIN",
    ]:
        raise HTTPException(
            status_code=400,
            detail="Invalid role",
        )

    user.role = new_role

    db.commit()
    db.refresh(user)

    return user


# =========================================================
# ADMIN - ALL EVENTS
# =========================================================

@app.get(
    "/admin/events",
    response_model=list[schemas.EventResponse],
)
def admin_get_events(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles("ADMIN")
    ),
):
    return db.query(models.Event).all()


# =========================================================
# ADMIN - DELETE EVENT
# =========================================================

@app.delete("/admin/events/{event_id}")
def admin_delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles("ADMIN")
    ),
):
    event = (
        db.query(models.Event)
        .filter(models.Event.id == event_id)
        .first()
    )

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Event not found",
        )

    db.delete(event)
    db.commit()

    return {
        "message": "Event deleted successfully"
    }


# =========================================================
# ADMIN - ALL BOOKINGS
# =========================================================

@app.get(
    "/admin/bookings",
    response_model=list[schemas.BookingResponse],
)
def admin_get_bookings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles("ADMIN")
    ),
):
    return db.query(models.Booking).all()


# =========================================================
# ADMIN - ANALYTICS
# =========================================================

@app.get("/admin/analytics")
def admin_analytics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles("ADMIN")
    ),
):
    total_users = (
        db.query(models.User).count()
    )

    total_organizers = (
        db.query(models.User)
        .filter(
            models.User.role == "ORGANIZER"
        )
        .count()
    )

    total_events = (
        db.query(models.Event).count()
    )

    total_bookings = (
        db.query(models.Booking).count()
    )

    total_revenue = (
        db.query(
            func.coalesce(
                func.sum(models.Booking.total_price),
                0
            )
        )
        .filter(
            models.Booking.booking_status ==
            "CONFIRMED"
        )
        .scalar()
    )

    return {
        "total_users": total_users,
        "total_organizers": total_organizers,
        "total_events": total_events,
        "total_bookings": total_bookings,
        "total_revenue": total_revenue,
    }