"""
图片检测服务
模型未训练时使用 mock 模式，训练后替换 model_path 即可自动切换到真实推理
"""
import os
import uuid
import random
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


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
        """生成模拟检测结果"""
        health_statuses = ["normal", "normal", "normal", "suspicious", "abnormal"]
        classes = {
            "猪": ["pig", "pig_skin_disease", "pig_lameness"],
            "牛": ["cow", "cow_foot_disease", "cow_eye_disease"],
            "羊": ["sheep", "sheep_scab", "sheep_bloat"],
        }
        class_list = classes.get(animal_type_name, ["animal", "animal_abnormal"])
        num_targets = random.randint(1, 4)
        results = []
        for i in range(num_targets):
            confidence = round(random.uniform(confidence_threshold, 0.99), 3)
            health = random.choice(health_statuses)
            class_name = class_list[0] if health == "normal" else random.choice(class_list[1:])
            results.append({
                "target_index": i,
                "class_name": class_name,
                "confidence": confidence,
                "health_status": health,
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
                    # 简单健康状态判断：类名包含 disease/abnormal/sick 则异常
                    if any(kw in cls_name.lower() for kw in ["disease", "abnormal", "sick", "lameness", "scab"]):
                        health = "abnormal" if conf > 0.7 else "suspicious"
                    else:
                        health = "normal"
                    detections.append({
                        "target_index": i,
                        "class_name": cls_name,
                        "confidence": round(conf, 3),
                        "health_status": health,
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

        if self._is_mock_mode(model_path):
            detections = self._mock_detect(animal_type_name, confidence_threshold)
            is_mock = True
        else:
            detections = self._real_detect(
                image_path, model_path, confidence_threshold, iou_threshold
            )
            is_mock = False

        # 统计健康状态
        normal = sum(1 for d in detections if d["health_status"] == "normal")
        suspicious = sum(1 for d in detections if d["health_status"] == "suspicious")
        abnormal = sum(1 for d in detections if d["health_status"] == "abnormal")

        elapsed = (datetime.now() - start_time).total_seconds()

        return {
            "detections": detections,
            "total_targets": len(detections),
            "normal_count": normal,
            "suspicious_count": suspicious,
            "abnormal_count": abnormal,
            "processing_time": round(elapsed, 3),
            "is_mock": is_mock,
        }


# 全局单例
detection_service = DetectionService(upload_dir="uploads")
