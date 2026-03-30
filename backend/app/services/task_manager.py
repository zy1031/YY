"""
简单的后台任务管理器
使用 Python threading 实现异步视频检测（无需 Celery）
"""
import threading
from typing import Dict, Any, Optional
from datetime import datetime


class TaskManager:
    """
    内存中维护任务状态
    key: task_id (str) -> task info dict
    """
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_task(self, task_id: str, meta: dict = None) -> dict:
        task = {
            "task_id": task_id,
            "status": "pending",   # pending / running / completed / failed
            "progress": 0,
            "total": 100,
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            **(meta or {}),
        }
        with self._lock:
            self._tasks[task_id] = task
        return task

    def update_progress(self, task_id: str, progress: int, total: int = 100):
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["progress"] = progress
                self._tasks[task_id]["total"] = total
                self._tasks[task_id]["status"] = "running"
                self._tasks[task_id]["updated_at"] = datetime.now().isoformat()

    def complete_task(self, task_id: str, result: dict):
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["status"] = "completed"
                self._tasks[task_id]["progress"] = self._tasks[task_id]["total"]
                self._tasks[task_id]["result"] = result
                self._tasks[task_id]["updated_at"] = datetime.now().isoformat()

    def fail_task(self, task_id: str, error: str):
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["status"] = "failed"
                self._tasks[task_id]["error"] = error
                self._tasks[task_id]["updated_at"] = datetime.now().isoformat()

    def get_task(self, task_id: str) -> Optional[dict]:
        with self._lock:
            return self._tasks.get(task_id)

    def run_in_background(self, task_id: str, func, *args, **kwargs):
        """在后台线程中运行函数"""
        def wrapper():
            try:
                self._tasks[task_id]["status"] = "running"
                result = func(*args, **kwargs)
                self.complete_task(task_id, result)
            except Exception as e:
                self.fail_task(task_id, str(e))
        t = threading.Thread(target=wrapper, daemon=True)
        t.start()


# 全局单例
task_manager = TaskManager()
