"""
数据库模型定义
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, Float, JSON, Boolean
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    email = Column(String(100), nullable=True)
    role = Column(Enum('admin', 'user'), default='user')
    status = Column(Enum('active', 'inactive'), default='active')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)

class AnimalType(Base):
    """动物类型表"""
    __tablename__ = "animal_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(Enum('active', 'inactive'), default='active')
    created_at = Column(DateTime, server_default=func.now())

class DetectionModel(Base):
    """检测模型表"""
    __tablename__ = "detection_models"
    
    id = Column(Integer, primary_key=True, index=True)
    animal_type_id = Column(Integer, nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    model_path = Column(String(255), nullable=False)
    model_version = Column(String(50), nullable=True)
    framework = Column(String(50), nullable=True)
    confidence_threshold = Column(Float, default=0.5)
    iou_threshold = Column(Float, default=0.45)
    status = Column(Enum('active', 'inactive'), default='active')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Animal(Base):
    """动物档案表"""
    __tablename__ = "animals"
    
    id = Column(Integer, primary_key=True, index=True)
    animal_type_id = Column(Integer, nullable=False, index=True)
    animal_number = Column(String(100), unique=True, nullable=False, index=True)
    breed = Column(String(100), nullable=True)
    age = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class DetectionRecord(Base):
    """检测记录表"""
    __tablename__ = "detection_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    animal_type_id = Column(Integer, nullable=True, index=True)  # 允许NULL
    model_id = Column(Integer, nullable=True)  # 允许NULL，无模型时为空
    detection_type = Column(Enum('image', 'video', 'camera'), nullable=False)
    input_source = Column(String(255), nullable=False)
    input_file_path = Column(String(255), nullable=True)
    output_file_path = Column(String(255), nullable=True)
    detection_status = Column(Enum('pending', 'processing', 'completed', 'failed'), default='pending')
    error_message = Column(Text, nullable=True)
    total_targets = Column(Integer, default=0)
    normal_count = Column(Integer, default=0)
    suspicious_count = Column(Integer, default=0)
    abnormal_count = Column(Integer, default=0)
    processing_time = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class DetectionResult(Base):
    """检测结果表"""
    __tablename__ = "detection_results"
    
    id = Column(Integer, primary_key=True, index=True)
    detection_record_id = Column(Integer, nullable=False, index=True)
    target_index = Column(Integer, nullable=False)
    class_name = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)
    health_status = Column(Enum('normal', 'suspicious', 'abnormal'), default='normal')
    bbox_x1 = Column(Integer, nullable=True)
    bbox_y1 = Column(Integer, nullable=True)
    bbox_x2 = Column(Integer, nullable=True)
    bbox_y2 = Column(Integer, nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class TrackingRecord(Base):
    """BoT-SORT跟踪记录表"""
    __tablename__ = "tracking_records"
    
    id = Column(Integer, primary_key=True, index=True)
    detection_record_id = Column(Integer, nullable=False, index=True)
    track_id = Column(Integer, nullable=False)
    animal_id = Column(Integer, nullable=True)
    start_frame = Column(Integer, nullable=True)
    end_frame = Column(Integer, nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    total_frames = Column(Integer, nullable=True)
    trajectory_data = Column(JSON, nullable=True)
    avg_confidence = Column(Float, nullable=True)
    health_status_summary = Column(String(50), nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class LLMReport(Base):
    """LLM报告表"""
    __tablename__ = "llm_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    detection_record_id = Column(Integer, nullable=False, index=True)
    report_type = Column(Enum('image', 'video', 'camera'), nullable=False)
    report_title = Column(String(255), nullable=True)
    report_content = Column(Text, nullable=False)
    report_format = Column(Enum('text', 'pdf'), default='text')
    report_file_path = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    health_assessment = Column(String(100), nullable=True)
    abnormal_details = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    llm_model_used = Column(String(100), nullable=True)
    generation_status = Column(Enum('pending', 'generating', 'completed', 'failed'), default='pending')
    error_message = Column(Text, nullable=True)
    generation_time = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(Text, nullable=False)
    config_type = Column(Enum('detection', 'tracking', 'llm', 'system'), default='system')
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class OperationLog(Base):
    """操作日志表"""
    __tablename__ = "operation_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    operation_type = Column(String(100), nullable=False)
    operation_detail = Column(Text, nullable=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(Integer, nullable=True)
    status = Column(Enum('success', 'failed'), default='success')
    error_message = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
