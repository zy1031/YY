"""
系统配置相关的 API 路由
带内存缓存机制，避免频繁数据库查询
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.models import SystemConfig

router = APIRouter()

# ==================== 内存缓存 ====================
_config_cache: dict = {}
_cache_expires_at: Optional[datetime] = None
CACHE_TTL_SECONDS = 60  # 缓存有效期60秒


def _is_cache_valid() -> bool:
    return _cache_expires_at is not None and datetime.now() < _cache_expires_at


def _load_cache(db: Session):
    global _config_cache, _cache_expires_at
    configs = db.query(SystemConfig).all()
    _config_cache = {item.config_key: item.config_value for item in configs}
    _cache_expires_at = datetime.now() + timedelta(seconds=CACHE_TTL_SECONDS)
    return _config_cache


def _invalidate_cache():
    global _cache_expires_at
    _cache_expires_at = None


def get_config_value(key: str, default: str = "", db: Session = None) -> str:
    """获取单个配置值（优先走缓存）"""
    if not _is_cache_valid() and db is not None:
        _load_cache(db)
    return _config_cache.get(key, default)


# ==================== 默认配置 ====================
DEFAULT_CONFIGS = {
    "confidence_threshold": "0.5",
    "iou_threshold": "0.45",
    "max_upload_size_mb": "500",
    "result_save_days": "30",
    "llm_api_url": "",
    "llm_api_key": "",
    "llm_model_name": "deepseek-chat",
}


class ConfigUpdate(BaseModel):
    config_value: str


# ==================== 接口 ====================

@router.get("/")
async def get_config(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取全部系统配置（带缓存）"""
    if _is_cache_valid():
        result = dict(_config_cache)
    else:
        result = _load_cache(db)
    # 补充默认值
    for k, v in DEFAULT_CONFIGS.items():
        if k not in result:
            result[k] = v
    return result


@router.put("/{config_key}")
async def update_config(
    config_key: str,
    data: ConfigUpdate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """更新单个配置项，同时使缓存失效"""
    config = db.query(SystemConfig).filter(
        SystemConfig.config_key == config_key
    ).first()
    if not config:
        config = SystemConfig(
            config_key=config_key,
            config_value=data.config_value,
            config_type="system",
        )
        db.add(config)
    else:
        config.config_value = data.config_value
    db.commit()
    _invalidate_cache()  # 使缓存失效
    return {"message": "更新成功", "key": config_key, "value": data.config_value}


@router.post("/batch")
async def batch_update_config(
    data: dict,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """批量更新配置项"""
    updated = []
    for key, value in data.items():
        config = db.query(SystemConfig).filter(
            SystemConfig.config_key == key
        ).first()
        if not config:
            config = SystemConfig(
                config_key=key,
                config_value=str(value),
                config_type="system",
            )
            db.add(config)
        else:
            config.config_value = str(value)
        updated.append(key)
    db.commit()
    _invalidate_cache()
    return {"message": f"成功更新 {len(updated)} 项配置", "updated": updated}


@router.post("/init-defaults")
async def init_default_configs(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """初始化默认配置（仅写入不存在的项）"""
    added = []
    for key, value in DEFAULT_CONFIGS.items():
        existing = db.query(SystemConfig).filter(
            SystemConfig.config_key == key
        ).first()
        if not existing:
            db.add(SystemConfig(
                config_key=key,
                config_value=value,
                config_type="system",
                description=key,
            ))
            added.append(key)
    db.commit()
    _invalidate_cache()
    return {"message": f"初始化了 {len(added)} 项默认配置", "added": added}
