"""
动物类型相关的 API 路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import AnimalType

router = APIRouter()

@router.get("/")
async def list_animal_types(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有动物类型列表"""
    types = db.query(AnimalType).filter(AnimalType.status == "active").all()
    return {
        "animal_types": [
            {"id": t.id, "name": t.name, "description": t.description}
            for t in types
        ]
    }
