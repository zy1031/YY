"""
模型管理相关的 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import AnimalType, DetectionModel

router = APIRouter()


# ==================== 动物类型接口 ====================

@router.get("/animal-types")
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


# ==================== 模型管理接口 ====================

class ModelConfigUpdate(BaseModel):
    confidence_threshold: Optional[float] = None
    iou_threshold: Optional[float] = None


@router.get("/")
async def list_models(
    animal_type_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取模型列表，可按动物类型过滤"""
    query = db.query(DetectionModel).filter(DetectionModel.status == "active")
    if animal_type_id:
        query = query.filter(DetectionModel.animal_type_id == animal_type_id)
    models = query.all()
    return {
        "models": [
            {
                "id": m.id,
                "model_name": m.model_name,
                "model_version": m.model_version,
                "framework": m.framework,
                "animal_type_id": m.animal_type_id,
                "confidence_threshold": m.confidence_threshold,
                "iou_threshold": m.iou_threshold,
            }
            for m in models
        ]
    }


@router.get("/switch")
async def get_current_model(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前激活的模型信息（从 system_config 读取）"""
    from app.models.models import SystemConfig
    config = db.query(SystemConfig).filter(
        SystemConfig.config_key == "current_model_id"
    ).first()
    if not config:
        return {"current_model": None}
    model = db.query(DetectionModel).filter(
        DetectionModel.id == int(config.config_value)
    ).first()
    if not model:
        return {"current_model": None}
    animal_type = db.query(AnimalType).filter(
        AnimalType.id == model.animal_type_id
    ).first()
    return {
        "current_model": {
            "id": model.id,
            "model_name": model.model_name,
            "framework": model.framework,
            "animal_type_id": model.animal_type_id,
            "animal_type_name": animal_type.name if animal_type else "",
            "confidence_threshold": model.confidence_threshold,
            "iou_threshold": model.iou_threshold,
        }
    }


class SwitchModelRequest(BaseModel):
    model_id: int


@router.post("/switch")
async def switch_model(
    data: SwitchModelRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """切换当前使用的模型"""
    model = db.query(DetectionModel).filter(
        DetectionModel.id == data.model_id,
        DetectionModel.status == "active"
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")

    from app.models.models import SystemConfig
    config = db.query(SystemConfig).filter(
        SystemConfig.config_key == "current_model_id"
    ).first()
    if config:
        config.config_value = str(data.model_id)
    else:
        config = SystemConfig(
            config_key="current_model_id",
            config_value=str(data.model_id),
            config_type="detection",
            description="当前使用的检测模型ID"
        )
        db.add(config)
    db.commit()
    return {"message": "切换成功", "model_id": data.model_id}


@router.get("/{model_id}")
async def get_model(
    model_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取模型详情"""
    model = db.query(DetectionModel).filter(DetectionModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    animal_type = db.query(AnimalType).filter(
        AnimalType.id == model.animal_type_id
    ).first()
    return {
        "id": model.id,
        "model_name": model.model_name,
        "model_path": model.model_path,
        "model_version": model.model_version,
        "framework": model.framework,
        "animal_type_id": model.animal_type_id,
        "animal_type_name": animal_type.name if animal_type else "",
        "confidence_threshold": model.confidence_threshold,
        "iou_threshold": model.iou_threshold,
    }


@router.put("/{model_id}/config")
async def update_model_config(
    model_id: int,
    data: ModelConfigUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新模型参数配置"""
    model = db.query(DetectionModel).filter(DetectionModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    if data.confidence_threshold is not None:
        model.confidence_threshold = data.confidence_threshold
    if data.iou_threshold is not None:
        model.iou_threshold = data.iou_threshold
    db.commit()
    return {"message": "更新成功"}
