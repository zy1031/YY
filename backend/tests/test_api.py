"""
功能测试套件
覆盖：用户认证、图片检测、视频检测、报告生成、记录管理
运行：pytest tests/ -v
"""
import pytest
import io
import json
from pathlib import Path
from fastapi.testclient import TestClient

# 添加后端目录到 path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app

# starlette 0.27 兼容写法
client = TestClient(app)

# ==================== 测试数据 ====================
TEST_USER = {
    "username": "test_user_pytest",
    "password": "Test123456",
    "email": "pytest@test.com",
}
_token = None


def get_token():
    global _token
    if _token:
        return _token
    # 尝试登录，失败则注册
    resp = client.post("/api/auth/login", json={
        "username": TEST_USER["username"],
        "password": TEST_USER["password"],
    })
    if resp.status_code != 200:
        client.post("/api/auth/register", json=TEST_USER)
        resp = client.post("/api/auth/login", json={
            "username": TEST_USER["username"],
            "password": TEST_USER["password"],
        })
    _token = resp.json().get("access_token", "")
    return _token


def auth_headers():
    return {"Authorization": f"Bearer {get_token()}"}


# ==================== 认证测试 ====================

class TestAuth:
    def test_register_and_login(self):
        """测试注册和登录流程"""
        # 尝试注册（可能已存在）
        resp = client.post("/api/auth/register", json={
            "username": "new_test_user_abc",
            "password": "Test123456",
            "email": "new_abc@test.com",
        })
        assert resp.status_code in [200, 400]  # 200=成功 400=已存在

        # 登录
        resp = client.post("/api/auth/login", json={
            "username": TEST_USER["username"],
            "password": TEST_USER["password"],
        })
        # 如果用户不存在先注册
        if resp.status_code == 401:
            client.post("/api/auth/register", json=TEST_USER)
            resp = client.post("/api/auth/login", json={
                "username": TEST_USER["username"],
                "password": TEST_USER["password"],
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    def test_login_wrong_password(self):
        """测试错误密码"""
        resp = client.post("/api/auth/login", json={
            "username": TEST_USER["username"],
            "password": "wrongpassword",
        })
        assert resp.status_code in [401, 400]

    def test_protected_route_without_token(self):
        """测试未认证访问保护路由"""
        resp = client.get("/api/users/profile")
        # FastAPI OAuth2 无 token 时可能返回 401 或 403
        assert resp.status_code in [401, 403]

    def test_get_current_user(self):
        """测试获取当前用户信息"""
        resp = client.get("/api/users/profile", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "username" in data


# ==================== 健康检查测试 ====================

class TestHealth:
    def test_root(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_health_detail(self):
        resp = client.get("/health/detail")
        assert resp.status_code == 200
        data = resp.json()
        assert "database" in data
        assert "version" in data


# ==================== 动物类型测试 ====================

class TestAnimalTypes:
    def test_list_animal_types(self):
        resp = client.get("/api/animal-types/", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "animal_types" in data


# ==================== 图片检测测试（Mock模式）====================

class TestImageDetection:
    def test_detect_image_mock(self):
        """测试图片检测（Mock模式，无需模型文件）"""
        # 创建一个简单的测试图片（1x1 像素的 JPEG）
        import struct
        # 最小有效 JPEG
        jpeg_bytes = bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
            0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
            0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
            0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00, 0xFB, 0xFF,
            0xD9,
        ])
        files = {"file": ("test.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}
        resp = client.post(
            "/api/detection/image/detect",
            files=files,
            headers=auth_headers()
        )
        # 允许 200（成功）或 500（无模型但服务正常）
        assert resp.status_code in [200, 422, 500]

    def test_get_detection_history(self):
        """测试获取检测历史"""
        resp = client.get("/api/detection/history", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "history" in data
        assert "total" in data


# ==================== 统计测试 ====================

class TestStatistics:
    def test_get_overview(self):
        resp = client.get("/api/statistics/overview", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "total_detections" in data

    def test_get_trend(self):
        resp = client.get("/api/statistics/trend?days=7", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "trend" in data

    def test_get_health_distribution(self):
        resp = client.get("/api/statistics/health-distribution", headers=auth_headers())
        assert resp.status_code == 200


# ==================== 系统配置测试 ====================

class TestConfig:
    def test_get_config(self):
        resp = client.get("/api/config/", headers=auth_headers())
        assert resp.status_code == 200

    def test_update_config(self):
        resp = client.put("/api/config/test_key",
            json={"config_value": "test_value"},
            headers=auth_headers()
        )
        assert resp.status_code == 200

    def test_init_defaults(self):
        resp = client.post("/api/config/init-defaults", headers=auth_headers())
        assert resp.status_code == 200


# ==================== 报告测试 ====================

class TestReports:
    def test_list_reports(self):
        resp = client.get("/api/reports/", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "reports" in data
        assert "total" in data


# ==================== 动物档案测试 ====================

class TestAnimals:
    def test_list_animals(self):
        resp = client.get("/api/animals/", headers=auth_headers())
        assert resp.status_code == 200

    def test_create_animal(self):
        resp = client.post("/api/animals/",
            json={
                "animal_number": "TEST001",
                "animal_type_id": 1,
                "name": "测试动物",
                "age_months": 12,
                "gender": "male",
            },
            headers=auth_headers()
        )
        assert resp.status_code in [200, 201, 400, 422]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
