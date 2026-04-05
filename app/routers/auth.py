from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth_rate_limit import enforce_login_rate, enforce_register_rate
from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.auth import TokenResponse, UserCreate, UserLogin, UserPublic
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(
    request: Request,
    user: UserCreate,
    db: Session = Depends(get_db),
) -> TokenResponse:
    enforce_register_rate(request)
    row = User(
        email=user.email.lower().strip(),
        full_name=user.full_name,
        hashed_password=hash_password(user.password)
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    token = create_access_token(row.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    body: UserLogin,
    db: Session = Depends(get_db),
) -> TokenResponse:
    enforce_login_rate(request)
    stmt = select(User).where(User.email == body.email.lower().strip())
    u = db.scalars(stmt).first()
    if u is None or not verify_password(body.password, u.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return TokenResponse(access_token=create_access_token(u.id))


@router.get("/me", response_model=UserPublic)
def me(current: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(current)
