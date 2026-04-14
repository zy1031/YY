"""
视频检测相关的 API 路由
支持异步检测（后台线程）+ 进度轮询 + 跟踪数据查询
"""
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import DetectionRecord, TrackingRecord, DetectionModel, AnimalType, SystemConfig
from app.services.video_detection_service import video_detection_service
from app.services.detection_service import resolve_model_path
from app.services.task_manager import task_manager

router = APIRouter()
UPLOAD_DIR = "uploads"


def get_current_model_info(db: Session):
    config = db.query(SystemConfig).filter(
        SystemConfig.config_key == "current_model_id"
    ).first()
    if not config:
        return None, None
    model = db.query(DetectionModel).filter(DetectionModel.id == int(config.config_value)).first()
    if not model:
        return None, None
    animal_type = db.query(AnimalType).filter(AnimalType.id == model.animal_type_id).first()
    return model, animal_type


def get_model_for_animal_type(db: Session, animal_type_id: Optional[int]):
    if not animal_type_id:
        return None, None
    model = db.query(DetectionModel).filter(
        DetectionModel.animal_type_id == animal_type_id,
        DetectionModel.status == "active"
    ).first()
    if not model:
        return None, None
    animal_type = db.query(AnimalType).filter(AnimalType.id == model.animal_type_id).first()
    return model, animal_type


# ==================== 视频上传 ====================

@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """上传视频文件，返回文件路径"""
    allowed = {"video/mp4", "video/avi", "video/x-msvideo", "video/quicktime", "video/x-matroska"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="只支持 MP4、AVI、MKV 格式")

    ext = os.path.splitext(file.filename)[-1].lower() or ".mp4"
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
        "file_size": len(content),
    }


# ==================== 视频检测（异步）====================

@router.post("/detect")
async def detect_video(
    file_path: str = Form(...),
    animal_type_id: Optional[int] = Form(None),
    sample_interval: int = Form(5),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """提交视频检测任务（后台异步执行），立即返回 task_id"""
    if not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="视频文件不存在，请重新上传")

    # 优先使用本次选择的动物类型对应模型
    model, animal_type = get_model_for_animal_type(db, animal_type_id)

    # 未选择或未匹配到时，再使用当前激活模型
    if not model:
        model, animal_type = get_current_model_info(db)

    raw_model_path = model.model_path if model else None
    model_path = resolve_model_path(raw_model_path)
    animal_type_name = animal_type.name if animal_type else "未知"
    confidence_threshold = model.confidence_threshold if model else 0.5
    iou_threshold = model.iou_threshold if model else 0.45
    model_id = model.id if model else None
    a_type_id = animal_type.id if animal_type else animal_type_id

    # 在数据库中创建检测记录（pending状态）
    record = DetectionRecord(
        user_id=current_user["user_id"],
        animal_type_id=a_type_id,
        model_id=model_id,
        detection_type="video",
        input_source=file_path,
        input_file_path=file_path,
        detection_status="pending",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    record_id = record.id

    # 生成任务ID
    task_id = f"video_{record_id}_{uuid.uuid4().hex[:8]}"
    task_manager.create_task(task_id, {"record_id": record_id})

    # 定义后台任务函数
    def run_detection():
        from app.core.database import SessionLocal
        session = SessionLocal()
        try:
            def progress_cb(current, total):
                task_manager.update_progress(task_id, current, total)

            result = video_detection_service.detect_video(
                video_path=file_path,
                model_path=model_path,
                animal_type_name=animal_type_name,
                confidence_threshold=confidence_threshold,
                iou_threshold=iou_threshold,
                sample_interval=sample_interval,
                progress_callback=progress_cb,
            )

            # 更新检测记录
            rec = session.query(DetectionRecord).filter(DetectionRecord.id == record_id).first()
            if rec:
                rec.detection_status = "completed"
                rec.total_targets = result["total_targets"]
                rec.normal_count = result["normal_count"]
                rec.suspicious_count = result["suspicious_count"]
                rec.abnormal_count = result["abnormal_count"]
                rec.processing_time = int(result["processing_time"] * 1000)
                rec.output_file_path = result.get("result_video_path")
                session.commit()

            # 保存跟踪记录
            for ts in result.get("track_summaries", []):
                tracking = TrackingRecord(
                    detection_record_id=record_id,
                    track_id=ts["track_id"],
                    start_frame=ts["start_frame"],
                    end_frame=ts["end_frame"],
                    total_frames=ts["total_frames"],
                    avg_confidence=ts["avg_confidence"],
                    health_status_summary=ts["health_status_summary"],
                )
                session.add(tracking)
            session.commit()

            return {
                "record_id": record_id,
                "total_targets": result["total_targets"],
                "normal_count": result["normal_count"],
                "suspicious_count": result["suspicious_count"],
                "abnormal_count": result["abnormal_count"],
                "processing_time": result["processing_time"],
                "is_mock": result["is_mock"],
                "track_count": len(result["track_summaries"]),
            }
        except Exception as e:
            session.query(DetectionRecord).filter(
                DetectionRecord.id == record_id
            ).update({"detection_status": "failed", "error_message": str(e)})
            session.commit()
            raise
        finally:
            session.close()

    # 启动后台任务
    task_manager.run_in_background(task_id, run_detection)

    return {
        "message": "检测任务已提交",
        "task_id": task_id,
        "record_id": record_id,
    }


# ==================== 任务进度查询 ====================

@router.get("/task/{task_id}")
async def get_task_progress(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """轮询检测任务进度"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    percent = int(task["progress"] / max(task["total"], 1) * 100)
    return {
        "task_id": task_id,
        "status": task["status"],
        "progress": percent,
        "result": task.get("result"),
        "error": task.get("error"),
    }


# ==================== 视频记录详情和跟踪数据 ====================

@router.get("/records")
async def list_video_records(
    page: int = 1,
    page_size: int = 10,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取视频检测记录列表"""
    query = db.query(DetectionRecord).filter(
        DetectionRecord.user_id == current_user["user_id"],
        DetectionRecord.detection_type == "video"
    )
    total = query.count()
    records = query.order_by(DetectionRecord.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return {
        "total": total,
        "records": [
            {
                "id": r.id,
                "detection_status": r.detection_status,
                "animal_type_id": r.animal_type_id,
                "total_targets": r.total_targets,
                "normal_count": r.normal_count,
                "suspicious_count": r.suspicious_count,
                "abnormal_count": r.abnormal_count,
                "processing_time": r.processing_time,
                "has_result_video": bool(r.output_file_path),
                "created_at": str(r.created_at),
            }
            for r in records
        ],
    }


@router.get("/{record_id}/tracks")
async def get_tracking_records(
    record_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取某次视频检测的跟踪轨迹数据"""
    record = db.query(DetectionRecord).filter(
        DetectionRecord.id == record_id,
        DetectionRecord.user_id == current_user["user_id"]
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    tracks = db.query(TrackingRecord).filter(
        TrackingRecord.detection_record_id == record_id
    ).all()

    return {
        "record_id": record_id,
        "total_tracks": len(tracks),
        "tracks": [
            {
                "id": t.id,
                "track_id": t.track_id,
                "start_frame": t.start_frame,
                "end_frame": t.end_frame,
                "total_frames": t.total_frames,
                "avg_confidence": t.avg_confidence,
                "health_status_summary": t.health_status_summary,
            }
            for t in tracks
        ],
    }


@router.get("/{record_id}/download")
async def download_result_video(
    record_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """下载标注后的结果视频"""
    record = db.query(DetectionRecord).filter(
        DetectionRecord.id == record_id,
        DetectionRecord.user_id == current_user["user_id"]
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    if not record.output_file_path or not os.path.exists(record.output_file_path):
        raise HTTPException(status_code=404, detail="结果视频不存在（Mock模式不生成结果视频）")
    return FileResponse(
        record.output_file_path,
        media_type="video/x-msvideo" if record.output_file_path.lower().endswith('.avi') else "video/mp4",
        filename=f"video_detection_{record_id}{Path(record.output_file_path).suffix}"
    )
