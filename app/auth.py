
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.config import settings
from app.schemas import (
    SignupRequest,
    UserResponse,
    LoginRequest,
    LoginResponse,
)
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(data: SignupRequest, db: Session = Depends(get_db)):

    email = str(data.email).lower()
    employee_number = None
    role = "visitor"

    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match.",
        )

    # Check whether the email is already registered.
    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    # Employee registration.
    if data.account_type == "employee":

        employee_number = data.employee_number.strip().upper()

        if employee_number not in settings.authorized_employee_numbers:
            raise HTTPException(
                status_code=403,
                detail="This employee number is not authorized for registration.",
            )

        existing_employee = db.scalar(
            select(User).where(
                User.employee_number == employee_number
            )
        )

        if existing_employee:
            raise HTTPException(
                status_code=409,
                detail="This employee number is already registered.",
            )

        role = "receptionist"

    # Create the account.
    user = User(
        full_name=data.full_name.strip(),
        email=email,
        employee_number=employee_number,
        hashed_password=hash_password(data.password),
        role=role,
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to create account. Please try again.",
        )

    return user


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):

    identifier = data.identifier.strip()

    # First, search by email.
    user = db.scalar(
        select(User).where(
            User.email == identifier.lower()
        )
    )

    # If no email matches, search by employee number.
    if user is None:
        user = db.scalar(
            select(User).where(
                User.employee_number == identifier.upper()
            )
        )

    if user is None or not verify_password(
        data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/employee number or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive. Contact the administrator.",
        )

    token = create_access_token(
        {
            "sub": str(user.id),
            "role": user.role,
        }
    )

    return LoginResponse(
        access_token=token,
        user=user,
    )
