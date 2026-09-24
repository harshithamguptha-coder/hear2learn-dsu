"""Account registration, login, and role-aware current-user endpoints."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .database import get_db
from .models import AuthResponse, UserCreate, UserLogin, UserResponse
from .services.auth_service import AuthenticationError, AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])
bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Please log in to continue.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: sqlite3.Connection = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()
    try:
        user_id = auth_service.decode_token(credentials.credentials)
    except AuthenticationError as exc:
        raise unauthorized() from exc
    user = auth_service.get_user(db, user_id)
    if user is None:
        raise unauthorized()
    return user


def require_teacher(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access is required.")
    return current_user


def require_student(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Student access is required.")
    return current_user



@router.post("/register", response_model=AuthResponse, status_code=201)
def register_user(
    payload: UserCreate,
    db: sqlite3.Connection = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    try:
        return auth_service.register(
            db,
            name=payload.name,
            email=payload.email,
            password=payload.password,
            role=payload.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/login", response_model=AuthResponse)
def login_user(
    payload: UserLogin,
    db: sqlite3.Connection = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    try:
        return auth_service.login(db, email=payload.email, password=payload.password)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/me", response_model=UserResponse)
def current_user(current_user: dict = Depends(get_current_user)) -> dict:
    return current_user
