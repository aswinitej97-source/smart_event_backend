# SmartEvent – Event Discovery & Ticket Booking System

SmartEvent is a backend application developed using FastAPI for event discovery, ticket booking, role-based access control, organizer event management, and admin analytics.

## Technologies Used

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- JWT Authentication
- Bcrypt
- Uvicorn

## Features

### User Authentication
- User Registration
- User Login
- JWT Authentication
- Password Hashing
- Protected Routes
- User Profile
- Role-Based Access Control (RBAC)

### User Roles
- USER
- ORGANIZER
- ADMIN

### Event Management
- View All Events
- Get Event by ID
- Search and Filter Events
- Organizer Event Creation
- Organizer Event Update
- Organizer Event Delete
- Event Ownership Validation

### Booking Management
- Create Booking
- View My Bookings
- Cancel Booking
- Automatic Total Price Calculation

### Ticket Management
- Generate Ticket
- Unique Ticket Code
- View My Tickets

### Notifications
- View Notifications
- Mark Notification as Read

### Organizer Management
- Create Events
- View Own Events
- Update Own Events
- Delete Own Events

### Admin Management
- View All Users
- Update User Roles
- View All Events
- Delete Events
- View All Bookings
- View Platform Analytics

## Role-Based Access Control

- USER can browse events, create bookings, view booking history, and manage tickets.
- ORGANIZER can create and manage their own events.
- ADMIN can manage users, events, bookings, and access analytics.

Unauthorized role access is restricted using FastAPI role dependencies.

## Run the Project

Install dependencies:

```bash
pip install -r requirements.txt