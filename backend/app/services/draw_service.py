"""
检测结果绘制服务
在图片上绘制检测框和标签，返回标注后的图片路径
"""
import os
import uuid
from pathlib import Path
from typing import List, Dict

RESULT_DIR = Path("uploads/results")
RESULT_DIR.mkdir(parents=True, exist_ok=True)

# 健康状态对应颜色 (BGR)
HEALTH_COLORS = {
    "normal": (56, 187, 120),      # 绿色
    "suspicious": (0, 165, 255),   # 橙色
    "abnormal": (60, 60, 245),     # 红色
}
HEALTH_LABELS_ZH = {
    "normal": "正常",
    "suspicious": "可疑",
    "abnormal": "异常",
}


def draw_detection_result(image_path: str, detections: List[Dict]) -> str:
    """
    在图片上绘制检测框，返回标注图片的保存路径。
    如果 opencv 未安装，返回原图路径（降级处理）。
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        # opencv 未安装时直接返回原图
        return image_path

    if not os.path.exists(image_path):
        return image_path

    img = cv2.imread(image_path)
    if img is None:
        return image_path

    h, w = img.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.5, min(w, h) / 800)
    thickness = max(2, int(min(w, h) / 300))

    for det in detections:
        x1 = det.get("bbox_x1", 0)
        y1 = det.get("bbox_y1", 0)
        x2 = det.get("bbox_x2", 100)
        y2 = det.get("bbox_y2", 100)
        status = det.get("health_status", "normal")
        class_name = det.get("class_name", "")
        confidence = det.get("confidence", 0.0)

        color = HEALTH_COLORS.get(status, (128, 128, 128))
        label = f"{class_name} {confidence:.0%} [{HEALTH_LABELS_ZH.get(status, status)}]"

        # 绘制边界框
        cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)

        # 绘制标签背景
        (tw, th), baseline = cv2.getTextSize(label, font, font_scale, thickness)
        label_y = max(y1 - 4, th + 4)
        cv2.rectangle(img, (x1, label_y - th - baseline - 4), (x1 + tw + 4, label_y), color, -1)

        # 绘制标签文字
        cv2.putText(img, label, (x1 + 2, label_y - baseline - 2), font, font_scale, (255, 255, 255), thickness)

    # 保存结果图片
    result_name = f"result_{uuid.uuid4().hex}.jpg"
    result_path = str(RESULT_DIR / result_name)
    cv2.imwrite(result_path, img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return result_path
