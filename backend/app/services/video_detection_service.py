"""
视频检测服务
- mock 模式：不依赖模型，生成模拟逐帧检测结果
- real 模式：YOLO 逐帧推理 + BoT-SORT 跟踪
支持进度回调，供异步任务使用
"""
import os
import uuid
import random
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime

from app.services.tracker_service import BotSortTracker

RESULT_VIDEO_DIR = Path("uploads/results/videos")
RESULT_VIDEO_DIR.mkdir(parents=True, exist_ok=True)


class VideoDetectionService:
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)

    # ------------------------------------------------------------------ #
    #  Mock 逐帧检测
    # ------------------------------------------------------------------ #
    def _mock_detect_frame(
        self,
        frame_idx: int,
        animal_type_name: str,
        confidence_threshold: float,
        width: int = 640,
        height: int = 480,
    ) -> List[Dict]:
        """生成单帧的模拟检测结果"""
        # 每隔几帧随机出现检测目标（模拟真实视频稀疏性）
        if random.random() < 0.3:  # 30% 帧无目标
            return []
        health_statuses = ["normal", "normal", "normal", "suspicious", "abnormal"]
        class_map = {
            "猪": ["pig", "pig_skin_disease"],
            "牛": ["cow", "cow_foot_disease"],
            "羊": ["sheep", "sheep_scab"],
        }
        classes = class_map.get(animal_type_name, ["animal", "animal_abnormal"])
        num = random.randint(1, 3)
        detections = []
        for i in range(num):
            status = random.choice(health_statuses)
            conf = round(random.uniform(confidence_threshold, 0.99), 3)
            x1 = random.randint(10, width // 2)
            y1 = random.randint(10, height // 2)
            x2 = x1 + random.randint(80, width // 3)
            y2 = y1 + random.randint(80, height // 3)
            detections.append({
                "target_index": i,
                "class_name": classes[0] if status == "normal" else classes[-1],
                "confidence": conf,
                "health_status": status,
                "bbox_x1": min(x1, width - 10),
                "bbox_y1": min(y1, height - 10),
                "bbox_x2": min(x2, width),
                "bbox_y2": min(y2, height),
            })
        return detections

    # ------------------------------------------------------------------ #
    #  真实逐帧检测（YOLO + BoT-SORT）
    # ------------------------------------------------------------------ #
    def _real_detect_frame(
        self, frame, model, confidence_threshold: float, iou_threshold: float, names: dict
    ) -> List[Dict]:
        results = model(frame, conf=confidence_threshold, iou=iou_threshold, verbose=False)
        detections = []
        for r in results:
            for i, box in enumerate(r.boxes):
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = names[cls_id]
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                status = "abnormal" if any(
                    kw in cls_name.lower()
                    for kw in ["disease", "abnormal", "sick", "lameness", "scab"]
                ) and conf > 0.7 else (
                    "suspicious" if any(
                        kw in cls_name.lower()
                        for kw in ["disease", "abnormal", "sick"]
                    ) else "normal"
                )
                detections.append({
                    "target_index": i, "class_name": cls_name,
                    "confidence": round(conf, 3), "health_status": status,
                    "bbox_x1": x1, "bbox_y1": y1, "bbox_x2": x2, "bbox_y2": y2,
                })
        return detections

    # ------------------------------------------------------------------ #
    #  主检测流程
    # ------------------------------------------------------------------ #
    def detect_video(
        self,
        video_path: str,
        model_path: str,
        animal_type_name: str,
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        sample_interval: int = 5,  # 每隔N帧采样一次
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[str, Any]:
        """
        对视频进行检测，返回逐帧结果和跟踪摘要
        sample_interval: 采样间隔帧数（减少处理量）
        """
        is_mock = not os.path.exists(model_path)
        tracker = BotSortTracker()

        all_frame_results: List[Dict] = []   # 每帧检测结果
        track_data: Dict[int, Dict] = {}      # track_id -> 轨迹数据

        start_time = datetime.now()

        if is_mock:
            # Mock 模式：模拟 100 帧视频
            total_frames = 100
            width, height = 640, 480
            for frame_idx in range(0, total_frames, sample_interval):
                dets = self._mock_detect_frame(
                    frame_idx, animal_type_name, confidence_threshold, width, height
                )
                tracked = tracker.update_mock(dets, frame_idx)
                for t in tracked:
                    tid = t["track_id"]
                    if tid not in track_data:
                        track_data[tid] = {
                            "track_id": tid,
                            "frames": [],
                            "health_statuses": [],
                            "confidences": [],
                        }
                    track_data[tid]["frames"].append(frame_idx)
                    track_data[tid]["health_statuses"].append(t["health_status"])
                    track_data[tid]["confidences"].append(t["confidence"])
                    all_frame_results.append(t)
                if progress_callback:
                    progress_callback(frame_idx + 1, total_frames)
            result_video_path = None
        else:
            # 真实模式
            try:
                import cv2
                from ultralytics import YOLO
                model = YOLO(model_path)
                cap = cv2.VideoCapture(video_path)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS) or 25
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                # 输出视频
                result_name = f"result_{uuid.uuid4().hex}.mp4"
                result_video_path = str(RESULT_VIDEO_DIR / result_name)
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                out = cv2.VideoWriter(result_video_path, fourcc, fps, (width, height))

                frame_idx = 0
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break
                    if frame_idx % sample_interval == 0:
                        dets = self._real_detect_frame(
                            frame, model, confidence_threshold, iou_threshold, model.names
                        )
                        tracked = tracker.update_mock(dets, frame_idx)
                        for t in tracked:
                            tid = t["track_id"]
                            if tid not in track_data:
                                track_data[tid] = {
                                    "track_id": tid, "frames": [],
                                    "health_statuses": [], "confidences": [],
                                }
                            track_data[tid]["frames"].append(frame_idx)
                            track_data[tid]["health_statuses"].append(t["health_status"])
                            track_data[tid]["confidences"].append(t["confidence"])
                            all_frame_results.append(t)
                        # 绘制检测框到输出视频
                        from app.services.draw_service import HEALTH_COLORS
                        import numpy as np
                        for t in tracked:
                            color = HEALTH_COLORS.get(t["health_status"], (128, 128, 128))
                            cv2.rectangle(frame, (t["bbox_x1"], t["bbox_y1"]),
                                          (t["bbox_x2"], t["bbox_y2"]), color, 2)
                            cv2.putText(frame, f"ID:{t['track_id']} {t['confidence']:.0%}",
                                        (t["bbox_x1"], t["bbox_y1"] - 5),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                    out.write(frame)
                    frame_idx += 1
                    if progress_callback:
                        progress_callback(frame_idx, total_frames)
                cap.release()
                out.release()
            except ImportError as e:
                raise RuntimeError(f"缺少依赖: {e}，请运行 pip install opencv-python ultralytics")

        elapsed = (datetime.now() - start_time).total_seconds()

        # 汇总轨迹摘要
        track_summaries = []
        for tid, data in track_data.items():
            statuses = data["health_statuses"]
            abnormal = statuses.count("abnormal")
            suspicious = statuses.count("suspicious")
            overall = "abnormal" if abnormal > 0 else ("suspicious" if suspicious > 0 else "normal")
            avg_conf = round(sum(data["confidences"]) / len(data["confidences"]), 3) if data["confidences"] else 0
            frames = data["frames"]
            track_summaries.append({
                "track_id": tid,
                "start_frame": frames[0] if frames else 0,
                "end_frame": frames[-1] if frames else 0,
                "total_frames": len(frames),
                "health_status_summary": overall,
                "avg_confidence": avg_conf,
                "abnormal_frames": abnormal,
                "suspicious_frames": suspicious,
            })

        # 统计
        unique_targets = len(track_data)
        all_statuses = [t["health_status"] for t in all_frame_results]
        # 按目标统计（以整体轨迹状态为准）
        track_statuses = [s["health_status_summary"] for s in track_summaries]
        total_targets = unique_targets
        normal_count = sum(1 for s in track_statuses if s == "normal")
        suspicious_count = sum(1 for s in track_statuses if s == "suspicious")
        abnormal_count = sum(1 for s in track_statuses if s == "abnormal")

        return {
            "is_mock": is_mock,
            "total_frames": total_frames if is_mock else frame_idx,
            "sampled_frames": len(set(t["frame_idx"] for t in all_frame_results)),
            "total_targets": total_targets,
            "normal_count": normal_count,
            "suspicious_count": suspicious_count,
            "abnormal_count": abnormal_count,
            "processing_time": round(elapsed, 3),
            "track_summaries": track_summaries,
            "result_video_path": result_video_path,
        }


video_detection_service = VideoDetectionService()
