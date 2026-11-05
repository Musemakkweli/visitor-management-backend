
from contextlib import asynccontextmanager
from datetime import date, datetime
from uuid import uuid4

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app import models, schemas
from app.auth import router as auth_router, get_current_user
from app.models import User
from app.security import hash_password


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Visitor Management System API",
    description="Backend API for managing visitors and appointments.",
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://visitor-management-hsyd.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)


# =====================================================
# GENERAL ENDPOINTS
# =====================================================

@app.get("/")
def home():
    return {
        "message": "Visitor Management System API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "Visitor Management System",
    }


# =====================================================
# APPOINTMENT ENDPOINTS
# =====================================================

# Create an appointment request (Visitor only)
@app.post(
    "/appointments",
    response_model=schemas.AppointmentResponse,
    status_code=201,
    tags=["Appointments"],
)
def create_appointment(
    appointment_data: schemas.AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "visitor":
        raise HTTPException(
            status_code=403,
            detail="Only visitors can create appointment requests.",
        )

    if appointment_data.visit_date < date.today():
        raise HTTPException(
            status_code=400,
            detail="Visit date cannot be in the past.",
        )

    appointment = models.Appointment(
        request_number=f"VIS-{uuid4().hex[:8].upper()}",
        visitor_id=current_user.id,
        destination=appointment_data.destination,
        purpose=appointment_data.purpose,
        visit_date=appointment_data.visit_date,
        visit_time=appointment_data.visit_time,
        status="pending",
    )

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return appointment


# Get the logged-in visitor's appointment requests
@app.get(
    "/appointments/my-requests",
    response_model=list[schemas.AppointmentResponse],
    tags=["Appointments"],
)
def get_my_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "visitor":
        raise HTTPException(
            status_code=403,
            detail="Only visitors can view their appointment requests.",
        )

    appointments = (
        db.query(models.Appointment)
        .filter(models.Appointment.visitor_id == current_user.id)
        .order_by(models.Appointment.created_at.desc())
        .all()
    )

    return appointments
# =====================================================
# APPOINTMENT REVIEW ENDPOINTS
# =====================================================

@app.patch(
    "/appointments/{appointment_id}/review",
    response_model=schemas.AppointmentResponse,
    tags=["Appointments"],
)
def review_appointment(
    appointment_id: int,
    review_data: schemas.AppointmentReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only receptionists and administrators can review requests.
    if current_user.role not in ["receptionist", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only receptionists and administrators can review appointments.",
        )

    appointment = db.get(models.Appointment, appointment_id)

    if appointment is None:
        raise HTTPException(
            status_code=404,
            detail="Appointment request not found.",
        )

    # Prevent reviewing an already processed request.
    if appointment.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="This appointment has already been reviewed.",
        )

    appointment.status = review_data.status
    appointment.response_message = review_data.response_message
    appointment.reviewed_at = datetime.now().astimezone()
    appointment.reviewed_by = current_user.id

    db.commit()
    db.refresh(appointment)

    return appointment


@app.get("/appointments/all", tags=["Appointments"])
def get_all_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["receptionist", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only receptionists and administrators can view all appointments.",
        )

    appointments = (
        db.query(models.Appointment, User)
        .join(User, models.Appointment.visitor_id == User.id)
        .order_by(models.Appointment.created_at.desc())
        .all()
    )

    return [
        {
            "id": appointment.id,
            "request_number": appointment.request_number,
            "visitor_id": visitor.id,
            "visitor_name": visitor.full_name,
            "visitor_email": visitor.email,
            "visitor_phone": visitor.phone,
            "destination": appointment.destination,
            "purpose": appointment.purpose,
            "visit_date": appointment.visit_date,
            "visit_time": appointment.visit_time,
            "status": appointment.status,
            "response_message": appointment.response_message,
            "created_at": appointment.created_at,
        }
        for appointment, visitor in appointments
    ]


# =====================================================
# VISITOR APPOINTMENT RESPONSES
# =====================================================

@app.get(
    "/appointments/my-responses",
    response_model=list[schemas.AppointmentResponse],
    tags=["Appointments"],
)
def get_my_responses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "visitor":
        raise HTTPException(
            status_code=403,
            detail="Only visitors can view appointment responses.",
        )

    responses = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.visitor_id == current_user.id,
            models.Appointment.status.in_(["approved", "rejected"]),
        )
        .order_by(models.Appointment.reviewed_at.desc())
        .all()
    )

    return responses


# =====================================================
# VISITOR DASHBOARD ENDPOINTS
# =====================================================

# Get visitor dashboard statistics and recent requests
@app.get(
    "/visitors/me/dashboard",
    response_model=schemas.DashboardResponse,
    tags=["Visitors"],
)
def get_visitor_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "visitor":
        raise HTTPException(
            status_code=403,
            detail="Only visitors can access this dashboard.",
        )

    appointments = (
        db.query(models.Appointment)
        .filter(models.Appointment.visitor_id == current_user.id)
        .all()
    )

    total_requests = len(appointments)
    pending = sum(1 for item in appointments if item.status == "pending")
    approved = sum(1 for item in appointments if item.status == "approved")
    rejected = sum(1 for item in appointments if item.status == "rejected")

    recent_requests = (
        db.query(models.Appointment)
        .filter(models.Appointment.visitor_id == current_user.id)
        .order_by(models.Appointment.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "statistics": {
            "total_requests": total_requests,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
        },
        "recent_requests": recent_requests,
    }


# =====================================================
# USER MANAGEMENT ENDPOINTS (ADMIN ONLY)
# =====================================================

# Get all registered users
@app.get("/users", tags=["Users"])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can view all users.",
        )

    users = (
        db.query(User)
        .order_by(User.created_at.desc())
        .all()
    )

    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "employee_number": user.employee_number,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
        }
        for user in users
    ]

# =====================================================
# RECEPTIONIST - GET REGISTERED VISITORS
# =====================================================

@app.get("/receptionist/visitors", tags=["Receptionist - Visitors"])
def get_registered_visitors(
    search: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["receptionist", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to view registered visitors.",
        )

    query = db.query(User).filter(
        User.role == "visitor",
        User.is_active == True,
    )

    if search.strip():
        search_term = f"%{search.strip()}%"

        query = query.filter(
            (User.full_name.ilike(search_term))
            | (User.email.ilike(search_term))
            | (User.phone.ilike(search_term))
        )

    visitors = query.order_by(User.created_at.desc()).all()

    return [
        {
            "id": visitor.id,
            "full_name": visitor.full_name,
            "email": visitor.email,
            "phone": visitor.phone,
            "organization": visitor.organization,
            "address": visitor.address,
        }
        for visitor in visitors
    ]

@app.get("/visits/inside", tags=["Visits"])
def get_visitors_inside(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["receptionist", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to view visitors inside.",
        )

    visits = (
        db.query(models.Visit, User)
        .join(User, models.Visit.visitor_id == User.id)
        .filter(models.Visit.status == "inside")
        .order_by(models.Visit.check_in_time.desc())
        .all()
    )

    return [
        {
            "id": visit.id,
            "visitor_id": visitor.id,
            "visitor_name": visitor.full_name,
            "email": visitor.email,
            "phone": visitor.phone,
            "destination": visit.destination,
            "purpose": visit.purpose,
            "check_in_time": visit.check_in_time,
            "status": visit.status,
        }
        for visit, visitor in visits
    ]

@app.get("/visits/history", tags=["Visits"])
def get_visit_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["receptionist", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to view visit history.",
        )

    visits = (
        db.query(models.Visit, User)
        .join(User, models.Visit.visitor_id == User.id)
        .order_by(models.Visit.check_in_time.desc())
        .all()
    )

    return [
        {
            "id": visit.id,
            "visitor_id": visitor.id,
            "visitor_name": visitor.full_name,
            "email": visitor.email,
            "phone": visitor.phone,
            "destination": visit.destination,
            "purpose": visit.purpose,
            "check_in_time": visit.check_in_time,
            "check_out_time": visit.check_out_time,
            "status": visit.status,
        }
        for visit, visitor in visits
    ]

# Promote a receptionist to administrator
@app.patch("/users/{user_id}/promote-to-admin", tags=["Users"])
def promote_to_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can promote employees.",
        )

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    if user.role != "receptionist":
        raise HTTPException(
            status_code=400,
            detail="Only receptionists can be promoted.",
        )

    user.role = "admin"
    db.commit()
    db.refresh(user)

    return {
        "message": "Employee promoted to administrator successfully.",
        "user_id": user.id,
        "full_name": user.full_name,
        "role": user.role,
    }


# Demote an administrator to receptionist
@app.patch("/users/{user_id}/demote-to-receptionist", tags=["Users"])
def demote_to_receptionist(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can demote employees.",
        )

    if current_user.id == user_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot demote your own account.",
        )

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    if user.role != "admin":
        raise HTTPException(
            status_code=400,
            detail="This user is not an administrator.",
        )

    # Do not allow the last administrator to be demoted.
    admin_count = db.query(User).filter(
        User.role == "admin",
        User.is_active == True,
    ).count()

    if admin_count <= 1:
        raise HTTPException(
            status_code=400,
            detail="The last active administrator cannot be demoted.",
        )

    user.role = "receptionist"
    db.commit()
    db.refresh(user)

    return {
        "message": "Administrator demoted to receptionist successfully.",
        "user_id": user.id,
        "full_name": user.full_name,
        "role": user.role,
    }


# Delete a user (Admin only)
@app.delete("/users/{user_id}", tags=["Users"])
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can delete users.",
        )

    if current_user.id == user_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot delete your own account.",
        )

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    # Protect the last active administrator.
    if user.role == "admin" and user.is_active:
        admin_count = db.query(User).filter(
            User.role == "admin",
            User.is_active == True,
        ).count()

        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="The last active administrator cannot be deleted.",
            )

    db.delete(user)
    db.commit()

    return {
        "message": "User deleted successfully.",
        "user_id": user_id,
    }


# =====================================================
# VISITOR PROFILE ENDPOINTS
# =====================================================

# Get the logged-in visitor's profile
@app.get(
    "/visitors/me",
    response_model=schemas.VisitorProfileResponse,
    tags=["Visitors"],
)
def get_visitor_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "visitor":
        raise HTTPException(
            status_code=403,
            detail="Only visitors can access this profile.",
        )

    return current_user


# Update the logged-in visitor's profile
@app.put(
    "/visitors/me",
    response_model=schemas.VisitorProfileResponse,
    tags=["Visitors"],
)
def update_visitor_profile(
    profile_data: schemas.VisitorProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "visitor":
        raise HTTPException(
            status_code=403,
            detail="Only visitors can update this profile.",
        )

    # Check whether another user already uses this email.
    existing_user = (
        db.query(User)
        .filter(
            User.email == profile_data.email,
            User.id != current_user.id,
        )
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="This email address is already in use.",
        )

    current_user.full_name = profile_data.full_name
    current_user.email = profile_data.email
    current_user.phone = profile_data.phone
    current_user.organization = profile_data.organization
    current_user.address = profile_data.address

    db.commit()
    db.refresh(current_user)

    return current_user

# =====================================================
# RECEPTIONIST CHECK-IN / CHECK-OUT ENDPOINTS
# =====================================================

# Check in a visitor
@app.post(
    "/visits/check-in",
    response_model=schemas.VisitResponse,
    status_code=201,
    tags=["Receptionist - Visits"],
)
def check_in_visitor(
    visit_data: schemas.VisitCheckIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only receptionists and administrators can check in visitors.
    if current_user.role not in ["receptionist", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only receptionists and administrators can check in visitors.",
        )

    # Confirm that the visitor account exists and is active.
    visitor = db.get(User, visit_data.visitor_id)

    if visitor is None or visitor.role != "visitor" or not visitor.is_active:
        raise HTTPException(
            status_code=404,
            detail="Active visitor account not found.",
        )

    # If an appointment is provided, confirm that it belongs
    # to this visitor and has been approved.
    if visit_data.appointment_id is not None:
        appointment = db.get(
            models.Appointment,
            visit_data.appointment_id,
        )

        if appointment is None:
            raise HTTPException(
                status_code=404,
                detail="Appointment not found.",
            )

        if appointment.visitor_id != visitor.id:
            raise HTTPException(
                status_code=400,
                detail="This appointment does not belong to the selected visitor.",
            )

        if appointment.status != "approved":
            raise HTTPException(
                status_code=400,
                detail="Only approved appointments can be checked in.",
            )

    # Prevent a visitor from being checked in more than once
    # while an earlier visit is still active.
    active_visit = (
        db.query(models.Visit)
        .filter(
            models.Visit.visitor_id == visitor.id,
            models.Visit.status == "inside",
        )
        .first()
    )

    if active_visit:
        raise HTTPException(
            status_code=400,
            detail="This visitor is already checked in.",
        )

    # Create the visit record.
    visit = models.Visit(
        visitor_id=visitor.id,
        appointment_id=visit_data.appointment_id,
        destination=visit_data.destination,
        purpose=visit_data.purpose,
        checked_in_by=current_user.id,
        status="inside",
    )

    db.add(visit)
    db.commit()
    db.refresh(visit)

    return visit


# Check out a visitor
@app.patch(
    "/visits/{visit_id}/check-out",
    response_model=schemas.VisitResponse,
    tags=["Receptionist - Visits"],
)
def check_out_visitor(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only receptionists and administrators can check out visitors.
    if current_user.role not in ["receptionist", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only receptionists and administrators can check out visitors.",
        )

    visit = db.get(models.Visit, visit_id)

    if visit is None:
        raise HTTPException(
            status_code=404,
            detail="Visit record not found.",
        )

    if visit.status != "inside":
        raise HTTPException(
            status_code=400,
            detail="This visitor has already checked out.",
        )

    visit.check_out_time = datetime.now().astimezone()
    visit.checked_out_by = current_user.id
    visit.status = "checked_out"

    db.commit()
    db.refresh(visit)

    return visit

@app.post(
    "/receptionist/register-visitor",
    response_model=schemas.UserResponse,
    status_code=201,
    tags=["Receptionist - Visitors"],
)
def register_visitor(
    visitor_data: schemas.ReceptionistVisitorCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Only receptionists and admins can register visitors.
    if current_user.role not in ["receptionist", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to register visitors.",
        )

    email = str(visitor_data.email).lower().strip()

    # Check whether the email already exists.
    existing_user = db.query(models.User).filter(
        models.User.email == email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="A user with this email already exists.",
        )

    # Create the visitor account.
    new_visitor = models.User(
        full_name=visitor_data.full_name.strip(),
        email=email,
        hashed_password=hash_password(visitor_data.password),
        role="visitor",
        phone=visitor_data.phone,
        organization=visitor_data.organization,
        address=visitor_data.address,
    )

    db.add(new_visitor)

    try:
        db.commit()
        db.refresh(new_visitor)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to register visitor.",
        )

    return new_visitor