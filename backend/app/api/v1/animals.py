"""
动物档案相关的 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Animal, AnimalType

router = APIRouter()


class AnimalCreate(BaseModel):
    animal_type_id: int
    animal_number: str
    breed: Optional[str] = None
    age: Optional[int] = None
    weight: Optional[float] = None
    remarks: Optional[str] = None


class AnimalUpdate(BaseModel):
    breed: Optional[str] = None
    age: Optional[int] = None
    weight: Optional[float] = None
    remarks: Optional[str] = None


def animal_to_dict(a: Animal, animal_type_name: str = "") -> dict:
    return {
        "id": a.id,
        "animal_type_id": a.animal_type_id,
        "animal_type_name": animal_type_name,
        "animal_number": a.animal_number,
        "breed": a.breed,
        "age": a.age,
        "weight": a.weight,
        "remarks": a.remarks,
        "created_at": str(a.created_at),
        "updated_at": str(a.updated_at),
    }


@router.get("/")
async def list_animals(
    page: int = 1,
    page_size: int = 10,
    animal_type_id: Optional[int] = None,
    keyword: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取动物档案列表（分页+过滤）"""
    query = db.query(Animal)
    if animal_type_id:
        query = query.filter(Animal.animal_type_id == animal_type_id)
    if keyword:
        query = query.filter(Animal.animal_number.like(f"%{keyword}%"))

    total = query.count()
    animals = query.order_by(Animal.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    # 获取类型名称
    type_map = {t.id: t.name for t in db.query(AnimalType).all()}

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "animals": [animal_to_dict(a, type_map.get(a.animal_type_id, "")) for a in animals]
    }


@router.post("/")
async def create_animal(
    data: AnimalCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建动物档案"""
    # 检查编号唯一
    existing = db.query(Animal).filter(Animal.animal_number == data.animal_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="动物编号已存在")

    animal_type = db.query(AnimalType).filter(AnimalType.id == data.animal_type_id).first()
    if not animal_type:
        raise HTTPException(status_code=400, detail="动物类型不存在")

    animal = Animal(
        animal_type_id=data.animal_type_id,
        animal_number=data.animal_number,
        breed=data.breed,
        age=data.age,
        weight=data.weight,
        remarks=data.remarks,
    )
    db.add(animal)
    db.commit()
    db.refresh(animal)
    return animal_to_dict(animal, animal_type.name)


@router.get("/{animal_id}")
async def get_animal(
    animal_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取动物档案详情"""
    animal = db.query(Animal).filter(Animal.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="动物档案不存在")
    animal_type = db.query(AnimalType).filter(AnimalType.id == animal.animal_type_id).first()
    return animal_to_dict(animal, animal_type.name if animal_type else "")


@router.put("/{animal_id}")
async def update_animal(
    animal_id: int,
    data: AnimalUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新动物档案"""
    animal = db.query(Animal).filter(Animal.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="动物档案不存在")
    if data.breed is not None:
        animal.breed = data.breed
    if data.age is not None:
        animal.age = data.age
    if data.weight is not None:
        animal.weight = data.weight
    if data.remarks is not None:
        animal.remarks = data.remarks
    db.commit()
    animal_type = db.query(AnimalType).filter(AnimalType.id == animal.animal_type_id).first()
    return animal_to_dict(animal, animal_type.name if animal_type else "")


@router.delete("/{animal_id}")
async def delete_animal(
    animal_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除动物档案"""
    animal = db.query(Animal).filter(Animal.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="动物档案不存在")
    db.delete(animal)
    db.commit()
    return {"message": "删除成功"}
