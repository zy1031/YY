"""
BoT-SORT 跟踪服务
- mock_mode: 模型未训练时生成模拟轨迹
- real_mode: 集成真实 BoT-SORT 算法（训练后启用）
"""
import random
import math
from typing import List, Dict, Any


class BotSortTracker:
    """
    BoT-SORT 目标跟踪器封装
    真实模式需要安装: pip install ultralytics (内置 BoT-SORT)
    """

    def __init__(self, track_thresh: float = 0.5, track_buffer: int = 30):
        self.track_thresh = track_thresh
        self.track_buffer = track_buffer
        self._next_id = 1
        self._tracks: Dict[int, Dict] = {}  # track_id -> track info

    def reset(self):
        self._next_id = 1
        self._tracks = {}

    def update_mock(self, detections: List[Dict], frame_idx: int) -> List[Dict]:
        """
        Mock 跟踪更新：为每个检测框分配/维持 track_id
        简单策略：IOU 匹配已有轨迹，否则新建
        """
        if not detections:
            # 标记所有轨迹为丢失
            for tid in list(self._tracks.keys()):
                self._tracks[tid]["lost"] += 1
                if self._tracks[tid]["lost"] > self.track_buffer:
                    del self._tracks[tid]
            return []

        assigned = {}  # det_idx -> track_id
        used_tracks = set()

        # 简单最近邻匹配
        for i, det in enumerate(detections):
            best_tid = None
            best_iou = 0.3  # 最小IOU阈值
            for tid, track in self._tracks.items():
                if tid in used_tracks:
                    continue
                iou = self._compute_iou(det, track["last_bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_tid = tid
            if best_tid is not None:
                assigned[i] = best_tid
                used_tracks.add(best_tid)
            else:
                # 新轨迹
                assigned[i] = self._next_id
                self._next_id += 1

        # 更新轨迹状态
        active_tids = set(assigned.values())
        for tid in list(self._tracks.keys()):
            if tid not in active_tids:
                self._tracks[tid]["lost"] += 1
                if self._tracks[tid]["lost"] > self.track_buffer:
                    del self._tracks[tid]

        results = []
        for i, det in enumerate(detections):
            tid = assigned[i]
            bbox = {
                "x1": det.get("bbox_x1", 0), "y1": det.get("bbox_y1", 0),
                "x2": det.get("bbox_x2", 100), "y2": det.get("bbox_y2", 100),
            }
            if tid not in self._tracks:
                self._tracks[tid] = {
                    "track_id": tid,
                    "last_bbox": bbox,
                    "lost": 0,
                    "start_frame": frame_idx,
                    "frames": [],
                }
            else:
                self._tracks[tid]["last_bbox"] = bbox
                self._tracks[tid]["lost"] = 0

            self._tracks[tid]["frames"].append(frame_idx)

            results.append({
                **det,
                "track_id": tid,
                "frame_idx": frame_idx,
                "bbox_x1": bbox["x1"],
                "bbox_y1": bbox["y1"],
                "bbox_x2": bbox["x2"],
                "bbox_y2": bbox["y2"],
            })
        return results

    def get_track_summary(self) -> List[Dict]:
        """获取所有轨迹摘要"""
        summaries = []
        for tid, track in self._tracks.items():
            frames = track.get("frames", [])
            summaries.append({
                "track_id": tid,
                "start_frame": track.get("start_frame", 0),
                "end_frame": frames[-1] if frames else 0,
                "total_frames": len(frames),
            })
        return summaries

    @staticmethod
    def _compute_iou(det: Dict, bbox: Dict) -> float:
        ax1, ay1 = det.get("bbox_x1", 0), det.get("bbox_y1", 0)
        ax2, ay2 = det.get("bbox_x2", 0), det.get("bbox_y2", 0)
        bx1, by1, bx2, by2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0
        inter = (ix2 - ix1) * (iy2 - iy1)
        area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
        area_b = max(1, (bx2 - bx1) * (by2 - by1))
        return inter / (area_a + area_b - inter)


# 全局单例
tracker = BotSortTracker()
