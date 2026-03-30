from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1 import auth, users, animals, models, detection, reports, config, animal_types, statistics, video_detection, camera_detection
from app.core.database import engine, Base
import logging
import traceback

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# --- 1. 定义生命周期管理器 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：创建数据库表
    Base.metadata.create_all(bind=engine)
    print("应用启动...")
    yield
    # 关闭时
    print("应用关闭...")

# --- 2. 只创建一次 FastAPI 实例 ---
app = FastAPI(
    title="动物健康检测系统 API",
    description="基于深度学习的动物健康检测系统",
    version="1.0.0",
    lifespan=lifespan
)

# --- 3. 配置一次 CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3.5 全局异常处理 ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {request.method} {request.url}\n{traceback.format_exc()}") 
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {str(exc)}"},
    )

from fastapi import HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code >= 500:
        logger.error(f"HTTP {exc.status_code}: {request.method} {request.url} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# --- 4. 注册路由 ---
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(animals.router, prefix="/api/animals", tags=["动物档案"])
app.include_router(animal_types.router, prefix="/api/animal-types", tags=["动物类型"])
app.include_router(models.router, prefix="/api/models", tags=["模型管理"])
app.include_router(detection.router, prefix="/api/detection", tags=["图片检测"])
app.include_router(video_detection.router, prefix="/api/video", tags=["视频检测"])
app.include_router(camera_detection.router, prefix="/api/camera", tags=["摄像头检测"])
app.include_router(statistics.router, prefix="/api/statistics", tags=["统计"])
app.include_router(reports.router, prefix="/api/reports", tags=["报告"])
app.include_router(config.router, prefix="/api/config", tags=["配置"])

# --- 5. 根路由与健康检查 ---
@app.get("/")
async def root():
    return {
        "message": "欢迎使用动物健康检测系统 API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """基础健康检查"""
    return {"status": "ok", "version": "1.0.0"}

@app.get("/health/detail")
async def health_check_detail():
    """详细系统状态检查"""
    import platform
    import psutil
    import time
    from app.core.database import SessionLocal

    # 数据库连接检查
    db_status = "ok"
    db_error = None
    try:
        db = SessionLocal()
        db.execute(__import__('sqlalchemy').text("SELECT 1"))
        db.close()
    except Exception as e:
        db_status = "error"
        db_error = str(e)[:100]

    # 系统资源
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        system_info = {
            "cpu_percent": cpu_percent,
            "memory_total_mb": round(mem.total / 1024 / 1024),
            "memory_used_mb": round(mem.used / 1024 / 1024),
            "memory_percent": mem.percent,
            "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 1),
            "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 1),
            "disk_percent": disk.percent,
        }
    except Exception:
        system_info = {"error": "psutil not available"}

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": "1.0.0",
        "python": platform.python_version(),
        "platform": platform.system(),
        "database": {"status": db_status, "error": db_error},
        "system": system_info,
        "uploads_dir": __import__('os').path.exists("uploads"),
    }

# --- 6. 启动 ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )