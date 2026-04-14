"""
摄像头实时检测服务
管理 WebSocket 连接和实时检测状态
"""
import uuid
import base64
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

SCREENSHOT_DIR = Path("uploads/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


class CameraSession:
    """单个摄像头检测会话"""
    def __init__(self, session_id: str, user_id: int, animal_type_name: str,
                 model_path: str, confidence: float, iou: float):
        self.session_id = session_id
        self.user_id = user_id
        self.animal_type_name = animal_type_name
        self.model_path = model_path
        self.confidence = confidence
        self.iou = iou
        self.status = "idle"  # idle / running / paused / stopped
        self.frame_count = 0
        self.total_targets = 0
        self.abnormal_count = 0
        self.suspicious_count = 0
        self.normal_count = 0
        self.created_at = datetime.now()
        self.screenshots: list = []
        self.track_health_history: Dict[int, list] = {}
        self._is_mock = not Path(model_path).exists()

    def is_mock(self) -> bool:
        return self._is_mock


class CameraSessionManager:
    """全局摄像头会话管理器"""
    def __init__(self):
        self._sessions: Dict[str, CameraSession] = {}

    def create_session(
        self, user_id: int, animal_type_name: str = "未知",
        model_path: str = "models/default.pt",
        confidence: float = 0.5, iou: float = 0.45
    ) -> CameraSession:
        session_id = f"cam_{uuid.uuid4().hex[:12]}"
        session = CameraSession(
            session_id, user_id, animal_type_name, model_path, confidence, iou
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[CameraSession]:
        return self._sessions.get(session_id)

    def remove_session(self, session_id: str):
        self._sessions.pop(session_id, None)

    def list_user_sessions(self, user_id: int) -> list:
        return [
            s for s in self._sessions.values()
            if s.user_id == user_id
        ]


camera_manager = CameraSessionManager()
