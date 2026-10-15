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
import phase4
phase4.install(app, get_current_user, require_roles)

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
        total_tickets=event.total_tickets,
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
    return phase4.reserve_booking(db, current_user, booking)


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
    return phase4.cancel_reserved_booking(db, current_user, booking_id)


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
# ================= REVIEWS =================

@app.post(
    "/events/{event_id}/reviews",
    response_model=schemas.ReviewResponse,
    status_code=201,
)
def create_review(
    event_id: int,
    data: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    event = db.query(models.Event).filter(
        models.Event.id == event_id
    ).first()

    if not event:
        raise HTTPException(404, "Event not found")

    existing = db.query(models.Review).filter(
        models.Review.user_id == current_user.id,
        models.Review.event_id == event_id,
    ).first()

    if existing:
        raise HTTPException(
            409,
            "You already reviewed this event",
        )

    review = models.Review(
        user_id=current_user.id,
        event_id=event_id,
        rating=data.rating,
        comment=data.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@app.get(
    "/events/{event_id}/reviews",
    response_model=list[schemas.ReviewResponse],
)
def get_event_reviews(
    event_id: int,
    db: Session = Depends(get_db),
):
    event = db.query(models.Event).filter(
        models.Event.id == event_id
    ).first()

    if not event:
        raise HTTPException(404, "Event not found")

    return db.query(models.Review).filter(
        models.Review.event_id == event_id
    ).order_by(
        models.Review.created_at.desc(),
        models.Review.id.desc(),
    ).all()


@app.get("/events/{event_id}/rating")
def get_event_rating(
    event_id: int,
    db: Session = Depends(get_db),
):
    event = db.query(models.Event).filter(
        models.Event.id == event_id
    ).first()

    if not event:
        raise HTTPException(404, "Event not found")

    average, count = db.query(
        func.avg(models.Review.rating),
        func.count(models.Review.id),
    ).filter(
        models.Review.event_id == event_id
    ).one()

    return {
        "event_id": event_id,
        "average_rating": round(float(average or 0), 2),
        "total_reviews": count,
    }


@app.put(
    "/reviews/{review_id}",
    response_model=schemas.ReviewResponse,
)
def update_review(
    review_id: int,
    data: schemas.ReviewUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    review = db.query(models.Review).filter(
        models.Review.id == review_id,
        models.Review.user_id == current_user.id,
    ).first()

    if not review:
        raise HTTPException(404, "Review not found")

    review.rating = data.rating
    review.comment = data.comment
    db.commit()
    db.refresh(review)
    return review


@app.delete("/reviews/{review_id}")
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    review = db.query(models.Review).filter(
        models.Review.id == review_id,
        models.Review.user_id == current_user.id,
    ).first()

    if not review:
        raise HTTPException(404, "Review not found")

    db.delete(review)
    db.commit()
    return {"message": "Review deleted successfully"}
# ================= PAYMENTS & COUPONS =================

from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError


@app.post(
    "/payments",
    response_model=schemas.PaymentResponse,
    status_code=201,
)
def make_payment(
    data: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        # Atomic status change prevents duplicate concurrent payments.
        claimed = db.execute(
            update(models.Booking)
            .where(
                models.Booking.id == data.booking_id,
                models.Booking.user_id == current_user.id,
                models.Booking.booking_status == "PENDING",
            )
            .values(booking_status="PROCESSING")
            .execution_options(synchronize_session=False)
        )

        if claimed.rowcount != 1:
            raise HTTPException(
                409,
                "Booking unavailable or not pending",
            )

        booking = db.query(models.Booking).filter(
            models.Booking.id == data.booking_id
        ).first()

        payment = db.query(models.Payment).filter(
            models.Payment.booking_id == booking.id
        ).first()

        if payment and payment.payment_status == "SUCCESS":
            raise HTTPException(409, "Already paid")

        if not payment:
            payment = models.Payment(booking_id=booking.id)
            db.add(payment)

        payment.payment_method = data.payment_method.strip()
        payment.amount = booking.total_price
        payment.transaction_id = f"SIM-{uuid4().hex}"
        payment.payment_status = (
            "SUCCESS" if data.simulate_success else "FAILED"
        )
        booking.booking_status = (
            "CONFIRMED" if data.simulate_success else "PENDING"
        )

        db.commit()
        db.refresh(payment)
        return payment

    except Exception:
        db.rollback()
        raise


@app.get(
    "/payments/my",
    response_model=list[schemas.PaymentResponse],
)
def my_payments(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Payment)
        .join(
            models.Booking,
            models.Payment.booking_id == models.Booking.id,
        )
        .filter(models.Booking.user_id == current_user.id)
        .order_by(models.Payment.id.desc())
        .all()
    )


@app.post(
    "/admin/coupons",
    response_model=schemas.CouponResponse,
    status_code=201,
)
def create_coupon(
    data: schemas.CouponCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("ADMIN")),
):
    expiry = data.expiry_date
    if expiry.tzinfo is not None:
        expiry = expiry.astimezone(timezone.utc).replace(
            tzinfo=None
        )

    if expiry <= datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(400, "Expiry must be in the future")

    if (
        data.discount_type == "PERCENTAGE"
        and data.discount_value > 100
    ):
        raise HTTPException(
            400, "Percentage cannot exceed 100"
        )

    coupon = models.Coupon(
        coupon_code=data.coupon_code.upper(),
        discount_type=data.discount_type,
        discount_value=data.discount_value,
        minimum_booking_amount=data.minimum_booking_amount,
        expiry_date=expiry,
        usage_limit=data.usage_limit,
        is_active=data.is_active,
    )

    try:
        db.add(coupon)
        db.commit()
        db.refresh(coupon)
        return coupon
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Coupon code already exists")


@app.get(
    "/admin/coupons",
    response_model=list[schemas.CouponResponse],
)
def list_coupons(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("ADMIN")),
):
    return db.query(models.Coupon).order_by(
        models.Coupon.id.desc()
    ).all()


@app.post("/coupons/apply")
def apply_coupon(
    data: schemas.CouponApply,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        # Payment and coupon application use the same booking lock.
        claimed = db.execute(
            update(models.Booking)
            .where(
                models.Booking.id == data.booking_id,
                models.Booking.user_id == current_user.id,
                models.Booking.booking_status == "PENDING",
            )
            .values(booking_status="PROCESSING")
            .execution_options(synchronize_session=False)
        )

        if claimed.rowcount != 1:
            raise HTTPException(
                409, "Booking unavailable or not pending"
            )

        booking = db.query(models.Booking).filter(
            models.Booking.id == data.booking_id
        ).first()

        already_used = db.query(models.CouponRedemption).filter(
            models.CouponRedemption.booking_id == booking.id
        ).first()

        if already_used:
            raise HTTPException(
                409, "A coupon is already applied to this booking"
            )

        coupon = db.query(models.Coupon).filter(
            models.Coupon.coupon_code
            == data.coupon_code.strip().upper()
        ).first()

        if not coupon:
            raise HTTPException(404, "Coupon not found")

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Reserve usage atomically, including all eligibility checks.
        reserved = db.execute(
            update(models.Coupon)
            .where(
                models.Coupon.id == coupon.id,
                models.Coupon.is_active.is_(True),
                models.Coupon.expiry_date > now,
                models.Coupon.used_count
                < models.Coupon.usage_limit,
                models.Coupon.minimum_booking_amount
                <= booking.total_price,
            )
            .values(used_count=models.Coupon.used_count + 1)
            .execution_options(synchronize_session=False)
        )

        if reserved.rowcount != 1:
            raise HTTPException(
                400,
                "Coupon expired, inactive, exhausted, "
                "or minimum amount not met",
            )

        original_total = booking.total_price

        if coupon.discount_type == "PERCENTAGE":
            discount = (
                original_total * coupon.discount_value / 100
            )
        elif coupon.discount_type == "FIXED":
            discount = coupon.discount_value
        else:
            raise HTTPException(400, "Invalid coupon type")

        discount = round(min(discount, original_total), 2)
        booking.total_price = round(
            original_total - discount, 2
        )
        booking.booking_status = "PENDING"

        db.add(models.CouponRedemption(
            coupon_id=coupon.id,
            booking_id=booking.id,
            discount_amount=discount,
        ))

        result = {
            "booking_id": booking.id,
            "coupon_code": coupon.coupon_code,
            "original_total": original_total,
            "discount_amount": discount,
            "total_price": booking.total_price,
        }
        db.commit()
        return result

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Coupon already applied to this booking"
        )
    except Exception:
        db.rollback()
        raise
