"""
摄像头实时检测 API
使用 WebSocket 推送实时检测结果
前端发送 base64 编码的帧图像，后端检测后返回结果
"""
import json
import base64
import uuid
import random
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user, verify_token
from jose import JWTError
from app.models.models import DetectionRecord, DetectionResult, AnimalType, SystemConfig, DetectionModel
from app.services.camera_service import camera_manager
from app.services.detection_service import detection_service, resolve_model_path
from app.services.health_rule_service import merge_health_and_behavior

router = APIRouter()
from app.services.health_rule_service import merge_health_and_behavior, summarize_track_health

SCREENSHOT_DIR = Path("uploads/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def get_model_info(db: Session):
    config = db.query(SystemConfig).filter(
        SystemConfig.config_key == "current_model_id"
    ).first()
    if not config:
        return None, None
    model = db.query(DetectionModel).filter(DetectionModel.id == int(config.config_value)).first()
    animal_type = db.query(AnimalType).filter(AnimalType.id == model.animal_type_id).first() if model else None
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


# ==================== 会话管理 ====================

class CreateSessionRequest(BaseModel):
    animal_type_id: Optional[int] = None


@router.post("/session")
async def create_camera_session(
    data: CreateSessionRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建摄像头检测会话，返回 session_id"""
    # 优先使用本次选择的动物类型对应模型
    model, animal_type = get_model_for_animal_type(db, data.animal_type_id)

    # 未选择或未匹配到时，再使用当前激活模型
    if not model:
        model, animal_type = get_model_info(db)

    raw_model_path = model.model_path if model else None
    model_path = resolve_model_path(raw_model_path)
    animal_type_name = animal_type.name if animal_type else "未知"
    confidence = model.confidence_threshold if model else 0.5
    iou = model.iou_threshold if model else 0.45

    session = camera_manager.create_session(
        user_id=current_user["user_id"],
        animal_type_name=animal_type_name,
        model_path=model_path,
        confidence=confidence,
        iou=iou,
    )
    return {
        "session_id": session.session_id,
        "is_mock": session.is_mock(),
        "animal_type": animal_type_name,
        "model_name": model.model_name if model else Path(model_path).name,
    }


@router.get("/session/{session_id}")
async def get_session_status(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """获取会话状态"""
    session = camera_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {
        "session_id": session_id,
        "status": session.status,
        "frame_count": session.frame_count,
        "total_targets": session.total_targets,
        "normal_count": session.normal_count,
        "suspicious_count": session.suspicious_count,
        "abnormal_count": session.abnormal_count,
        "is_mock": session.is_mock(),
        "screenshots": session.screenshots,
    }


@router.delete("/session/{session_id}")
async def stop_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """停止并保存会话检测记录"""
    session = camera_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 保存检测记录
    if session.frame_count > 0:
        record = DetectionRecord(
            user_id=session.user_id,
            animal_type_id=None,
            model_id=None,
            detection_type="camera",
            input_source=f"camera_session_{session_id}",
            detection_status="completed",
            total_targets=session.total_targets,
            normal_count=session.normal_count,
            suspicious_count=session.suspicious_count,
            abnormal_count=session.abnormal_count,
        )
        db.add(record)
        db.commit()

    camera_manager.remove_session(session_id)
    return {"message": "会话已停止"}


# ==================== 截图保存 ====================

@router.post("/session/{session_id}/screenshot")
async def save_screenshot(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """保存当前帧截图路径（由 WebSocket 端保存，此接口记录元数据）"""
    session = camera_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"message": "截图已记录", "count": len(session.screenshots)}


# ==================== WebSocket 实时检测 ====================

@router.websocket("/ws/{session_id}")
async def camera_websocket(
    websocket: WebSocket,
    session_id: str,
):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    try:
        verify_token(token)
    except (HTTPException, JWTError, Exception):
        await websocket.accept()
        await websocket.send_text(json.dumps({"type": "error", "message": "WebSocket 鉴权失败，请重新登录后重试"}))
        await websocket.close(code=1008)
        return
    """
    WebSocket 实时检测接口
    消息格式（前端发送）:
      { "type": "frame", "data": "<base64 JPEG>" }
      { "type": "control", "action": "pause" | "resume" | "stop" }

    消息格式（后端推送）:
      { "type": "result", "frame_id": N, "detections": [...], "stats": {...} }
      { "type": "error", "message": "..." }
    """
    await websocket.accept()
    session = camera_manager.get_session(session_id)
    if not session:
        await websocket.send_text(json.dumps({"type": "error", "message": "会话不存在"}))
        await websocket.close()
        return

    session.status = "running"

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            # 控制指令
            if msg.get("type") == "control":
                action = msg.get("action")
                if action == "pause":
                    session.status = "paused"
                    await websocket.send_text(json.dumps({"type": "status", "status": "paused"}))
                elif action == "resume":
                    session.status = "running"
                    await websocket.send_text(json.dumps({"type": "status", "status": "running"}))
                elif action == "stop":
                    session.status = "stopped"
                    await websocket.send_text(json.dumps({"type": "status", "status": "stopped"}))
                    break
                elif action == "screenshot":
                    # 保存最后一帧的 base64 为截图
                    frame_data = msg.get("frame_data", "")
                    if frame_data:
                        fname = f"screenshot_{session_id}_{session.frame_count}.jpg"
                        fpath = str(SCREENSHOT_DIR / fname)
                        img_bytes = base64.b64decode(frame_data)
                        with open(fpath, "wb") as f:
                            f.write(img_bytes)
                        session.screenshots.append(fpath)
                        await websocket.send_text(json.dumps({
                            "type": "screenshot", "path": fpath, "filename": fname
                        }))
                continue

            # 帧检测
            if msg.get("type") == "frame" and session.status == "running":
                session.frame_count += 1
                frame_data = msg.get("data", "")

                if session.is_mock():
                    # Mock 检测：生成随机结果
                    detections = _mock_detect_frame(session)
                else:
                    # 真实检测
                    try:
                        detections = await _real_detect_frame(session, frame_data)
                    except Exception as e:
                        detections = _mock_detect_frame(session)

                # 更新统计
                frame_track_status: dict[int, str] = {}
                for det in detections:
                    track_id = det.get("track_id", det["target_index"])
                    history = session.track_health_history.setdefault(track_id, [])
                    history.append(det["health_status"])
                    final_status = summarize_track_health(history[-12:])
                    det["health_status"] = final_status
                    frame_track_status[track_id] = final_status

                session.total_targets = len(session.track_health_history)
                session.normal_count = sum(1 for status in frame_track_status.values() if status == "normal")
                session.suspicious_count = sum(1 for status in frame_track_status.values() if status == "suspicious")
                session.abnormal_count = sum(1 for status in frame_track_status.values() if status == "abnormal")

                await websocket.send_text(json.dumps({
                    "type": "result",
                    "frame_id": session.frame_count,
                    "is_mock": session.is_mock(),
                    "detections": detections,
                    "stats": {
                        "frame_count": session.frame_count,
                        "total_targets": session.total_targets,
                        "normal_count": session.normal_count,
                        "suspicious_count": session.suspicious_count,
                        "abnormal_count": session.abnormal_count,
                    }
                }))

    except WebSocketDisconnect:
        session.status = "stopped"
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except:
            pass
    finally:
        session.status = "stopped"


def _mock_detect_frame(session: "CameraSession") -> list:
    """Mock 帧检测：随机生成检测结果"""
    if random.random() < 0.25:  # 25% 帧无目标
        return []
    health_statuses = ["normal", "normal", "normal", "suspicious", "abnormal"]
    class_map = {
        "猪": ["pig", "pig_skin_disease"],
        "牛": ["cow", "cow_foot_disease"],
        "羊": ["sheep", "sheep_scab"],
    }
    classes = class_map.get(session.animal_type_name, ["animal", "animal_abnormal"])
    detections = []
    for i in range(random.randint(1, 3)):
        status = random.choice(health_statuses)
        detections.append({
            "target_index": i,
            "track_id": random.randint(1, 10),
            "class_name": classes[0] if status == "normal" else classes[-1],
            "confidence": round(random.uniform(0.5, 0.99), 3),
            "health_status": status,
            "bbox_x1": random.randint(10, 200),
            "bbox_y1": random.randint(10, 150),
            "bbox_x2": random.randint(250, 500),
            "bbox_y2": random.randint(200, 400),
        })
    return detections


async def _real_detect_frame(session, frame_data: str) -> list:
    """真实帧检测：解码 base64 图片，调用 YOLO 推理"""
    import cv2
    import numpy as np
    from ultralytics import YOLO

    img_bytes = base64.b64decode(frame_data)
    nparr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        return []

    model = YOLO(session.model_path)
    results = model(frame, conf=session.confidence, iou=session.iou, verbose=False)
    detections = []
    for r in results:
        for i, box in enumerate(r.boxes):
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = r.names[cls_id]
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            status = merge_health_and_behavior(cls_name, conf, session.animal_type_name)
            detections.append({
                "target_index": i, "track_id": i,
                "class_name": cls_name, "confidence": round(conf, 3),
                "health_status": status,
                "bbox_x1": x1, "bbox_y1": y1, "bbox_x2": x2, "bbox_y2": y2,
            })
    return detections
