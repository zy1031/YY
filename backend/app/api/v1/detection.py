"""
检测相关的 API 路由
"""
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import DetectionRecord, DetectionResult, DetectionModel, AnimalType, SystemConfig
from app.services.detection_service import detection_service, resolve_model_path
from app.services.draw_service import draw_detection_result

router = APIRouter()

UPLOAD_DIR = "uploads"


def get_current_model_info(db: Session):
    """从 system_config 获取当前模型信息"""
    config = db.query(SystemConfig).filter(
        SystemConfig.config_key == "current_model_id"
    ).first()
    if not config:
        return None, None
    model = db.query(DetectionModel).filter(
        DetectionModel.id == int(config.config_value)
    ).first()
    if not model:
        return None, None
    animal_type = db.query(AnimalType).filter(
        AnimalType.id == model.animal_type_id
    ).first()
    return model, animal_type


def get_model_for_animal_type(db: Session, animal_type_id: Optional[int]):
    """优先按本次选择的动物类型匹配模型"""
    if not animal_type_id:
        return None, None
    model = db.query(DetectionModel).filter(
        DetectionModel.animal_type_id == animal_type_id,
        DetectionModel.status == "active"
    ).first()
    if not model:
        return None, None
    animal_type = db.query(AnimalType).filter(
        AnimalType.id == model.animal_type_id
    ).first()
    return model, animal_type


# ==================== 图片检测 ====================

@router.post("/image/upload")
async def upload_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """上传图片，返回文件路径"""
    allowed_types = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="只支持 JPG、PNG、JPEG、WEBP 格式")

    ext = os.path.splitext(file.filename)[-1].lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(UPLOAD_DIR, "images", filename)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return {
        "message": "上传成功",
        "filename": filename,
        "file_path": save_path,
        "original_name": file.filename,
    }


@router.post("/image/detect")
async def detect_image(
    file_path: str = Form(...),
    animal_type_id: Optional[int] = Form(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """对已上传的图片执行行为识别，返回识别结果"""
    if not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="文件不存在，请重新上传")

    # 优先使用本次选择的动物类型对应模型
    model, animal_type = get_model_for_animal_type(db, animal_type_id)

    # 未选择或未匹配到时，再使用当前激活模型
    if not model:
        model, animal_type = get_current_model_info(db)

    # 仍无模型时自动回退到 backend/models/best.pt
    raw_model_path = model.model_path if model else None
    model_path = resolve_model_path(raw_model_path)
    animal_type_name = animal_type.name if animal_type else "未知"
    confidence_threshold = model.confidence_threshold if model else 0.5
    iou_threshold = model.iou_threshold if model else 0.45
    model_id = model.id if model else None   # 无模型时存 NULL，避免外键约束失败
    a_type_id = animal_type.id if animal_type else animal_type_id  # 可为 None

    # 执行检测
    result = detection_service.detect_image(
        image_path=file_path,
        model_path=model_path,
        animal_type_name=animal_type_name,
        confidence_threshold=confidence_threshold,
        iou_threshold=iou_threshold,
    )

    # 保存检测记录
    record = DetectionRecord(
        user_id=current_user["user_id"],
        animal_type_id=a_type_id,
        model_id=model_id,
        detection_type="image",
        input_source=file_path,
        input_file_path=file_path,
        detection_status="completed",
        total_targets=result["total_targets"],
        normal_count=0,
        suspicious_count=0,
        abnormal_count=0,
        processing_time=int(result["processing_time"] * 1000),
    )
    db.add(record)
    db.flush()

    # 保存检测结果
    for det in result["detections"]:
        det_result = DetectionResult(
            detection_record_id=record.id,
            target_index=det["target_index"],
            class_name=det["class_name"],
            confidence=det["confidence"],
            health_status="normal",
            bbox_x1=det["bbox_x1"],
            bbox_y1=det["bbox_y1"],
            bbox_x2=det["bbox_x2"],
            bbox_y2=det["bbox_y2"],
        )
        db.add(det_result)
    db.commit()

    return {
        "record_id": record.id,
        "animal_type": animal_type_name,
        "model_name": model.model_name if model else Path(model_path).name,
        "task_type": "behavior_recognition",
        "task_label": "图片行为识别",
        "is_mock": result["is_mock"],
        "total_targets": result["total_targets"],
        "normal_count": 0,
        "suspicious_count": 0,
        "abnormal_count": 0,
        "processing_time": result["processing_time"],
        "detections": result["detections"],
    }


# ==================== 视频检测（占位）====================

@router.post("/video/upload")
async def upload_video(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """上传视频"""
    allowed_types = {"video/mp4", "video/avi", "video/x-msvideo", "video/quicktime"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="只支持 MP4、AVI 格式")

    ext = os.path.splitext(file.filename)[-1].lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(UPLOAD_DIR, "videos", filename)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return {
        "message": "上传成功",
        "filename": filename,
        "file_path": save_path,
        "original_name": file.filename,
    }


@router.post("/video/detect")
async def detect_video(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """视频检测（第4周实现）"""
    return {"message": "视频检测功能将在第4周实现"}


# ==================== 静态路由（必须在动态路由前）====================

@router.get("/history")
async def get_detection_history(
    page: int = 1,
    page_size: int = 10,
    detection_type: Optional[str] = None,
    animal_type_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取检测历史（分页+过滤）"""
    query = db.query(DetectionRecord).filter(
        DetectionRecord.user_id == current_user["user_id"]
    )
    if detection_type:
        query = query.filter(DetectionRecord.detection_type == detection_type)
    if animal_type_id:
        query = query.filter(DetectionRecord.animal_type_id == animal_type_id)

    total = query.count()
    records = query.order_by(DetectionRecord.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "history": [
            {
                "id": r.id,
                "detection_type": r.detection_type,
                "detection_status": r.detection_status,
                "task_label": "图片行为识别" if r.detection_type == "image" else ("视频检测" if r.detection_type == "video" else "实时监控"),
                "animal_type_id": r.animal_type_id,
                "total_targets": r.total_targets,
                "normal_count": r.normal_count,
                "suspicious_count": r.suspicious_count,
                "abnormal_count": r.abnormal_count,
                "processing_time": r.processing_time,
                "created_at": str(r.created_at),
            }
            for r in records
        ],
    }


# ==================== 动态路由 ====================

@router.get("/{detection_id}/results")
async def get_detection_results(
    detection_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取某次检测的详细结果"""
    record = db.query(DetectionRecord).filter(
        DetectionRecord.id == detection_id,
        DetectionRecord.user_id == current_user["user_id"]
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="检测记录不存在")

    results = db.query(DetectionResult).filter(
        DetectionResult.detection_record_id == detection_id
    ).all()

    animal_type = db.query(AnimalType).filter(
        AnimalType.id == record.animal_type_id
    ).first()

    return {
        "record": {
            "id": record.id,
            "detection_type": record.detection_type,
            "task_label": "图片行为识别" if record.detection_type == "image" else ("视频检测" if record.detection_type == "video" else "实时监控"),
            "detection_status": record.detection_status,
            "animal_type": animal_type.name if animal_type else "",
            "input_file_path": record.input_file_path,
            "total_targets": record.total_targets,
            "normal_count": record.normal_count,
            "suspicious_count": record.suspicious_count,
            "abnormal_count": record.abnormal_count,
            "processing_time": record.processing_time,
            "created_at": str(record.created_at),
        },
        "results": [
            {
                "id": r.id,
                "target_index": r.target_index,
                "class_name": r.class_name,
                "confidence": r.confidence,
                "health_status": r.health_status,
                "bbox_x1": r.bbox_x1,
                "bbox_y1": r.bbox_y1,
                "bbox_x2": r.bbox_x2,
                "bbox_y2": r.bbox_y2,
            }
            for r in results
        ],
    }


@router.get("/{detection_id}/progress")
async def get_detection_progress(
    detection_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取检测进度"""
    record = db.query(DetectionRecord).filter(
        DetectionRecord.id == detection_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"status": record.detection_status, "progress": 100 if record.detection_status == "completed" else 0}


@router.delete("/{detection_id}")
async def delete_detection_record(
    detection_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除检测记录"""
    record = db.query(DetectionRecord).filter(
        DetectionRecord.id == detection_id,
        DetectionRecord.user_id == current_user["user_id"]
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.query(DetectionResult).filter(
        DetectionResult.detection_record_id == detection_id
    ).delete()
    db.delete(record)
    db.commit()
    return {"message": "删除成功"}


@router.get("/{detection_id}/download")
async def download_annotated_image(
    detection_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """下载标注后的检测结果图片"""
    record = db.query(DetectionRecord).filter(
        DetectionRecord.id == detection_id,
        DetectionRecord.user_id == current_user["user_id"]
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    if record.detection_type != "image":
        raise HTTPException(status_code=400, detail="仅支持图片检测结果下载")

    results = db.query(DetectionResult).filter(
        DetectionResult.detection_record_id == detection_id
    ).all()

    detections = [
        {
            "bbox_x1": r.bbox_x1, "bbox_y1": r.bbox_y1,
            "bbox_x2": r.bbox_x2, "bbox_y2": r.bbox_y2,
            "class_name": r.class_name,
            "confidence": r.confidence,
            "health_status": r.health_status,
        }
        for r in results
    ]

    # 如果已有标注图片则复用，否则重新绘制
    if record.output_file_path and os.path.exists(record.output_file_path):
        result_path = record.output_file_path
    else:
        result_path = draw_detection_result(record.input_file_path or "", detections)
        # 保存路径到记录
        record.output_file_path = result_path
        db.commit()

    if not os.path.exists(result_path):
        raise HTTPException(status_code=404, detail="结果文件不存在")

    return FileResponse(
        result_path,
        media_type="image/jpeg",
        filename=f"detection_{detection_id}_result.jpg"
    )


@router.delete("/batch")
async def batch_delete_detection_records(
    ids: List[int],
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """批量删除检测记录"""
    if not ids:
        raise HTTPException(status_code=400, detail="请提供要删除的记录ID列表")
    # 只能删除自己的记录
    records = db.query(DetectionRecord).filter(
        DetectionRecord.id.in_(ids),
        DetectionRecord.user_id == current_user["user_id"]
    ).all()
    if not records:
        raise HTTPException(status_code=404, detail="未找到可删除的记录")
    deleted_ids = [r.id for r in records]
    db.query(DetectionResult).filter(
        DetectionResult.detection_record_id.in_(deleted_ids)
    ).delete(synchronize_session=False)
    db.query(DetectionRecord).filter(
        DetectionRecord.id.in_(deleted_ids)
    ).delete(synchronize_session=False)
    db.commit()
    return {"message": f"成功删除 {len(deleted_ids)} 条记录", "deleted_ids": deleted_ids}

