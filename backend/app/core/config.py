"""
应用配置文件
"""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """应用设置"""
    
    # 应用基本配置
    APP_NAME: str = "动物健康检测系统"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 数据库配置
    DATABASE_URL: str = "mysql+pymysql://root:root@localhost:3306/animal_health_detection"
    
    # JWT 配置
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS 配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    
    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 500 * 1024 * 1024  # 500MB
    UPLOAD_DIR: str = "uploads"
    
    # 模型配置
    MODELS_DIR: str = "models"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
