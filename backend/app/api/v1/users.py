"""
用户相关的 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User

router = APIRouter()

class UserUpdate(BaseModel):
    """用户更新模型"""
    email: str = None
    password: str = None

@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取用户信息"""
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "status": user.status
    }

@router.put("/profile")
async def update_profile(
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if user_data.email:
        user.email = user_data.email
    
    db.commit()
    db.refresh(user)
    return {"message": "更新成功"}
