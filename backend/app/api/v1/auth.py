"""
认证相关的 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from pydantic import BaseModel, EmailStr
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.models.models import User
from app.core.config import settings

router = APIRouter()

# Pydantic 模型
class UserRegister(BaseModel):
    """用户注册模型"""
    username: str
    password: str
    email: str = None

class UserLogin(BaseModel):
    """用户登录模型"""
    username: str
    password: str

class TokenResponse(BaseModel):
    """Token 响应模型"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str

class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    username: str
    email: str = None
    role: str
    status: str
    
    class Config:
        from_attributes = True

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    用户注册
    
    - **username**: 用户名（必填）
    - **password**: 密码（必填）
    - **email**: 邮箱（可选）
    """
    # 检查用户是否已存在
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 创建新用户
    hashed_password = hash_password(user_data.password)
    new_user = User(
        username=user_data.username,
        password=hashed_password,
        email=user_data.email,
        role="user",
        status="active"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录
    
    - **username**: 用户名（必填）
    - **password**: 密码（必填）
    """
    # 查询用户
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 兼容明文密码（初始 admin 账号）和 bcrypt 哈希密码
    password_ok = False
    if user.password.startswith("$2b$") or user.password.startswith("$2a$"):
        # bcrypt 哈希密码
        password_ok = verify_password(user_data.password, user.password)
    else:
        # 明文密码（兼容初始账号），验证后自动升级为 bcrypt
        if user_data.password == user.password:
            password_ok = True
            user.password = hash_password(user_data.password)
            db.commit()
    
    if not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )
    
    # 创建 Token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "username": user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username
    }

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    用户登出
    """
    return {"message": "登出成功"}

@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    获取当前用户信息
    """
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user
