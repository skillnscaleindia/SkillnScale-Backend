from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core import security
from app.core.config import settings
from app.models.user import (
    Token, UserResponse, UserCreate, UserLogin, 
    CustomerCreate, ProfessionalCreate, AuthResponse, OTPVerify
)
from app.db.database import get_db
from app.db.db_models import User, UserRole
from app.core import security, otp
from jose import jwt, JWTError

router = APIRouter()


def _get_auth_response(user: User) -> AuthResponse:
    """Helper to create AuthResponse with user and tokens."""
    return AuthResponse(
        user=UserResponse.from_orm(user),
        tokens=Token(
            access_token=security.create_access_token(user.id),
            refresh_token=security.create_refresh_token(user.id),
            token_type="bearer",
        )
    )


@router.post("/login/json", response_model=Token)
async def login_json(
    user_in: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """JSON login – phone + password."""
    result = await db.execute(
        select(User).where(User.phone == user_in.phone)
    )
    user = result.scalar_one_or_none()

    if not user or not security.verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect phone number or password")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account not verified. Please complete OTP verification.")

    return {
        "access_token": security.create_access_token(user.id),
        "refresh_token": security.create_refresh_token(user.id),
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get new access token using refresh token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = security.decode_token(refresh_token)
        if payload is None:
            raise credentials_exception
        
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "refresh":
            raise credentials_exception
            
    except (JWTError, AttributeError):
        raise credentials_exception

    # Verify user still exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    return {
        "access_token": security.create_access_token(user.id),
        "refresh_token": security.create_refresh_token(user.id),  # Rotate refresh token
        "token_type": "bearer",
    }


@router.post("/signup/customer")
async def signup_customer(
    user_in: CustomerCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create new customer user (inactive) and send OTP."""
    # Check phone uniqueness
    result = await db.execute(select(User).where(User.phone == user_in.phone))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="This phone number is already registered.")

    # Check email uniqueness only if provided
    if user_in.email:
        result = await db.execute(select(User).where(User.email == user_in.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="This email is already registered.")

    new_user = User(
        phone=user_in.phone,
        email=user_in.email,
        password_hash=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=UserRole.CUSTOMER.value,
        is_active=False  # Must verify OTP
    )
    db.add(new_user)
    await db.commit()

    await otp.send_otp(db, user_in.phone, delivery_method=user_in.delivery_method)

    return {"message": f"OTP sent to your {user_in.delivery_method}. Please verify to complete registration."}


@router.post("/signup/professional")
async def signup_professional(
    user_in: ProfessionalCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create new professional user (inactive) and send OTP."""
    # Check phone uniqueness
    result = await db.execute(select(User).where(User.phone == user_in.phone))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="This phone number is already registered.")

    # Check email uniqueness only if provided
    if user_in.email:
        result = await db.execute(select(User).where(User.email == user_in.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="This email is already registered.")

    new_user = User(
        phone=user_in.phone,
        email=user_in.email,
        password_hash=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
        service_category=user_in.service_category,
        bio=user_in.bio,
        role=UserRole.PRO.value,
        is_active=False  # Must verify OTP
    )
    db.add(new_user)
    await db.commit()

    await otp.send_otp(db, user_in.phone, delivery_method=user_in.delivery_method)

    return {"message": f"OTP sent to your {user_in.delivery_method}. Please verify to complete registration."}


@router.post("/verify-otp", response_model=AuthResponse)
async def verify_otp(
    data: OTPVerify,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Verify OTP, activate user, and return tokens."""
    is_valid = await otp.verify_otp_code(db, data.phone, data.otp_code)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    await db.commit()
    await db.refresh(user)

    return _get_auth_response(user)
