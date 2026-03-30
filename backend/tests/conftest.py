"""
pytest 配置文件
"""
import pytest
import sys
from pathlib import Path

# 确保后端根目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent.parent))
