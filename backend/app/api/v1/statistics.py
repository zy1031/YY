"""
检测统计相关的 API 路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import DetectionRecord, DetectionResult, AnimalType

router = APIRouter()


@router.get("/overview")
async def get_overview(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取总体统计概览"""
    uid = current_user["user_id"]

    total = db.query(func.count(DetectionRecord.id)).filter(
        DetectionRecord.user_id == uid
    ).scalar() or 0

    today = datetime.now().date()
    today_count = db.query(func.count(DetectionRecord.id)).filter(
        DetectionRecord.user_id == uid,
        func.date(DetectionRecord.created_at) == today
    ).scalar() or 0

    total_targets = db.query(func.sum(DetectionRecord.total_targets)).filter(
        DetectionRecord.user_id == uid
    ).scalar() or 0

    total_abnormal = db.query(func.sum(DetectionRecord.abnormal_count)).filter(
        DetectionRecord.user_id == uid
    ).scalar() or 0

    total_suspicious = db.query(func.sum(DetectionRecord.suspicious_count)).filter(
        DetectionRecord.user_id == uid
    ).scalar() or 0

    # 按类型统计
    type_stats = db.query(
        DetectionRecord.detection_type,
        func.count(DetectionRecord.id).label("count")
    ).filter(
        DetectionRecord.user_id == uid
    ).group_by(DetectionRecord.detection_type).all()

    return {
        "total_detections": total,
        "today_detections": today_count,
        "total_targets": int(total_targets),
        "total_abnormal": int(total_abnormal),
        "total_suspicious": int(total_suspicious),
        "type_stats": [
            {"type": t.detection_type, "count": t.count}
            for t in type_stats
        ]
    }


@router.get("/trend")
async def get_trend(
    days: int = 7,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取近N天检测趋势"""
    uid = current_user["user_id"]
    result = []
    for i in range(days - 1, -1, -1):
        day = datetime.now().date() - timedelta(days=i)
        count = db.query(func.count(DetectionRecord.id)).filter(
            DetectionRecord.user_id == uid,
            func.date(DetectionRecord.created_at) == day
        ).scalar() or 0
        abnormal = db.query(func.sum(DetectionRecord.abnormal_count)).filter(
            DetectionRecord.user_id == uid,
            func.date(DetectionRecord.created_at) == day
        ).scalar() or 0
        result.append({
            "date": str(day),
            "count": count,
            "abnormal": int(abnormal)
        })
    return {"trend": result}


@router.get("/by-animal-type")
async def get_stats_by_animal_type(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """按动物类型统计检测数量和异常数"""
    uid = current_user["user_id"]
    rows = db.query(
        AnimalType.name,
        func.count(DetectionRecord.id).label("total"),
        func.sum(DetectionRecord.abnormal_count).label("abnormal"),
        func.sum(DetectionRecord.normal_count).label("normal"),
    ).join(
        DetectionRecord, DetectionRecord.animal_type_id == AnimalType.id
    ).filter(
        DetectionRecord.user_id == uid
    ).group_by(AnimalType.name).all()

    return {
        "stats": [
            {
                "animal_type": r.name,
                "total": r.total,
                "abnormal": int(r.abnormal or 0),
                "normal": int(r.normal or 0),
            }
            for r in rows
        ]
    }


@router.get("/health-distribution")
async def get_health_distribution(
    animal_type_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取健康状态分布"""
    uid = current_user["user_id"]
    query = db.query(
        DetectionResult.health_status,
        func.count(DetectionResult.id).label("count")
    ).join(
        DetectionRecord, DetectionRecord.id == DetectionResult.detection_record_id
    ).filter(DetectionRecord.user_id == uid)

    if animal_type_id:
        query = query.filter(DetectionRecord.animal_type_id == animal_type_id)

    rows = query.group_by(DetectionResult.health_status).all()
    return {
        "distribution": [
            {"status": r.health_status, "count": r.count}
            for r in rows
        ]
    }
