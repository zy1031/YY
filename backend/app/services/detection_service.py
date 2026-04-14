"""
图片检测服务
模型未训练时使用 mock 模式，训练后替换 model_path 即可自动切换到真实推理
图片检测以行为识别展示为主，健康状态判断主要留给视频/实时监控模块
"""
import os
import uuid
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = BACKEND_DIR / "models" / "best.pt"


def resolve_model_path(model_path: Optional[str]) -> str:
    """优先使用传入路径，其次自动回退到 backend/models/best.pt"""
    candidates = []

    if model_path:
        path = Path(model_path)
        if path.is_absolute():
            candidates.append(path)
        else:
            candidates.append(BACKEND_DIR / path)
            candidates.append(path)

    candidates.append(DEFAULT_MODEL_PATH)

    seen = set()
    for candidate in candidates:
        normalized = str(candidate.resolve(strict=False))
        if normalized in seen:
            continue
        seen.add(normalized)
        if candidate.exists():
            return normalized

    if candidates:
        return str(candidates[0].resolve(strict=False))
    return str(DEFAULT_MODEL_PATH.resolve(strict=False))


class DetectionService:
    """
    检测服务
    - mock_mode=True：返回模拟检测结果（用于开发演示）
    - mock_mode=False：加载真实 YOLO 模型进行推理
    """

    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        (self.upload_dir / "images").mkdir(exist_ok=True)
        (self.upload_dir / "results").mkdir(exist_ok=True)
        self._model_cache: Dict[int, Any] = {}

    def _is_mock_mode(self, model_path: str) -> bool:
        """判断是否使用 mock 模式（模型文件不存在时自动降级）"""
        return not os.path.exists(model_path)

    def _mock_detect(self, animal_type_name: str, confidence_threshold: float) -> List[Dict]:
        """生成模拟行为识别结果"""
        classes = {
            "猪": ["Lying", "Sleeping", "Investigating", "Eating", "Walking", "Mounted"],
            "牛": ["Standing", "Eating", "Walking", "Lying"],
            "羊": ["Standing", "Eating", "Walking", "Resting"],
        }
        class_list = classes.get(animal_type_name, ["Standing", "Walking", "Eating"])
        num_targets = random.randint(1, 4)
        results = []
        for i in range(num_targets):
            confidence = round(random.uniform(confidence_threshold, 0.99), 3)
            class_name = random.choice(class_list)
            results.append({
                "target_index": i,
                "class_name": class_name,
                "confidence": confidence,
                "health_status": None,
                "bbox_x1": random.randint(10, 200),
                "bbox_y1": random.randint(10, 200),
                "bbox_x2": random.randint(250, 500),
                "bbox_y2": random.randint(250, 450),
            })
        return results

    def _real_detect(self, image_path: str, model_path: str,
                     confidence_threshold: float, iou_threshold: float) -> List[Dict]:
        """
        真实 YOLO 模型推理
        训练完模型后取消注释此方法
        """
        try:
            from ultralytics import YOLO
            model = YOLO(model_path)
            results = model(image_path, conf=confidence_threshold, iou=iou_threshold)
            detections = []
            for r in results:
                for i, box in enumerate(r.boxes):
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    cls_name = r.names[cls_id]
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    # 图片检测阶段仅做行为识别展示，不在此处输出健康结论
                    detections.append({
                        "target_index": i,
                        "class_name": cls_name,
                        "confidence": round(conf, 3),
                        "health_status": None,
                        "bbox_x1": x1,
                        "bbox_y1": y1,
                        "bbox_x2": x2,
                        "bbox_y2": y2,
                    })
            return detections
        except ImportError:
            raise RuntimeError("未安装 ultralytics，请运行: pip install ultralytics")

    def detect_image(
        self,
        image_path: str,
        model_path: str,
        animal_type_name: str,
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
    ) -> Dict[str, Any]:
        """
        对单张图片进行检测
        返回：检测结果列表 + 统计信息
        """
        start_time = datetime.now()

        resolved_model_path = resolve_model_path(model_path)

        if self._is_mock_mode(resolved_model_path):
            detections = self._mock_detect(animal_type_name, confidence_threshold)
            is_mock = True
        else:
            detections = self._real_detect(
                image_path, resolved_model_path, confidence_threshold, iou_threshold
            )
            is_mock = False

        # 图片检测阶段不输出健康状态统计，统计字段统一置 0，避免与视频/监控语义混淆
        elapsed = (datetime.now() - start_time).total_seconds()

        return {
            "detections": detections,
            "total_targets": len(detections),
            "normal_count": 0,
            "suspicious_count": 0,
            "abnormal_count": 0,
            "processing_time": round(elapsed, 3),
            "is_mock": is_mock,
        }


# 全局单例
detection_service = DetectionService(upload_dir="uploads")
