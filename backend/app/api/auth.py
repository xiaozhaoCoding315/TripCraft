"""
TripCraft Authentication API Routes

JWT 认证路由，用户数据持久化到 PostgreSQL。
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.services.auth import (
    User,
    create_access_token,
    get_current_user,
    hash_password,
    require_user,
    verify_password,
)
from app.core.config import get_settings
from app.services.persistence import get_persistence

router = APIRouter(prefix="/auth", tags=["authentication"])


# ==================== 请求模型 ====================

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400


class UserResponse(BaseModel):
    user_id: str
    username: str
    email: Optional[str] = None


# ==================== 端点 ====================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """注册新用户"""
    if len(request.username) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be at least 3 characters",
        )

    if len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters",
        )

    persistence = get_persistence()

    # 检查用户名是否已存在
    existing = await persistence.get_user_by_username(request.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    import uuid
    user_id = str(uuid.uuid4())
    password_hash = hash_password(request.password)

    user = await persistence.create_user(
        user_id=user_id,
        username=request.username,
        email=request.email,
        password_hash=password_hash,
    )

    return UserResponse(user_id=user.id, username=user.username, email=user.email)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """登录并获取访问令牌"""
    persistence = get_persistence()
    user = await persistence.get_user_by_username(request.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    settings = get_settings()
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        settings=settings,
    )

    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(require_user)):
    """获取当前认证用户信息"""
    persistence = get_persistence()
    db_user = await persistence.get_user_by_id(user.user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(user_id=db_user.id, username=db_user.username, email=db_user.email)


@router.get("/optional", response_model=UserResponse)
async def get_optional_user(user: Optional[User] = Depends(get_current_user)):
    """获取用户信息（如果已认证），否则返回访客"""
    if user:
        persistence = get_persistence()
        db_user = await persistence.get_user_by_id(user.user_id)
        if db_user:
            return UserResponse(user_id=db_user.id, username=db_user.username)
    return UserResponse(user_id="guest", username="guest")
