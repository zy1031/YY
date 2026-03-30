"""
性能基准测试脚本
测试各接口响应时间是否满足性能要求：
  - 图片检测：< 3秒（mock模式）
  - 列表查询：< 500ms
  - 统计接口：< 1秒
运行：python tests/test_performance.py
"""
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# 颜色输出
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

_token = None


def get_token():
    global _token
    if _token:
        return _token
    resp = client.post("/api/auth/login", json={"username": "test_user_pytest", "password": "Test123456"})
    if resp.status_code != 200:
        client.post("/api/auth/register", json={"username": "test_user_pytest", "password": "Test123456", "email": "perf@test.com"})
        resp = client.post("/api/auth/login", json={"username": "test_user_pytest", "password": "Test123456"})
    _token = resp.json().get("access_token", "")
    return _token


def headers():
    return {"Authorization": f"Bearer {get_token()}"}


def benchmark(name: str, func, threshold_ms: float, runs: int = 5):
    """运行基准测试，输出平均/最大/最小耗时"""
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        func()
        times.append((time.perf_counter() - t0) * 1000)

    avg = sum(times) / len(times)
    mn = min(times)
    mx = max(times)
    ok = avg < threshold_ms
    status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
    print(f"  [{status}] {name}")
    print(f"         avg={avg:.0f}ms  min={mn:.0f}ms  max={mx:.0f}ms  threshold={threshold_ms:.0f}ms")
    return ok


def run_benchmarks():
    print(f"\n{YELLOW}{'='*60}{RESET}")
    print(f"{YELLOW}  动物健康检测系统 - 性能基准测试{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}\n")

    results = []

    # 1. 根路由
    results.append(benchmark(
        "GET / (根路由)",
        lambda: client.get("/"),
        threshold_ms=100
    ))

    # 2. 健康检查
    results.append(benchmark(
        "GET /health",
        lambda: client.get("/health"),
        threshold_ms=100
    ))

    # 3. 详细健康检查（含DB）
    results.append(benchmark(
        "GET /health/detail (含DB查询)",
        lambda: client.get("/health/detail"),
        threshold_ms=500
    ))

    # 4. 统计概览
    results.append(benchmark(
        "GET /api/statistics/overview",
        lambda: client.get("/api/statistics/overview", headers=headers()),
        threshold_ms=1000
    ))

    # 5. 检测历史（分页）
    results.append(benchmark(
        "GET /api/detection/image/history (分页)",
        lambda: client.get("/api/detection/image/history?page=1&page_size=10", headers=headers()),
        threshold_ms=500
    ))

    # 6. 报告列表
    results.append(benchmark(
        "GET /api/reports/ (分页)",
        lambda: client.get("/api/reports/", headers=headers()),
        threshold_ms=500
    ))

    # 7. 动物列表
    results.append(benchmark(
        "GET /api/animals/ (分页)",
        lambda: client.get("/api/animals/", headers=headers()),
        threshold_ms=500
    ))

    # 8. 系统配置（缓存）
    results.append(benchmark(
        "GET /api/config/ (带缓存)",
        lambda: client.get("/api/config/", headers=headers()),
        threshold_ms=200
    ))

    # 9. 趋势统计
    results.append(benchmark(
        "GET /api/statistics/trend?days=7",
        lambda: client.get("/api/statistics/trend?days=7", headers=headers()),
        threshold_ms=1000
    ))

    # 10. 健康分布
    results.append(benchmark(
        "GET /api/statistics/health-distribution",
        lambda: client.get("/api/statistics/health-distribution", headers=headers()),
        threshold_ms=1000
    ))

    # 汇总
    passed = sum(results)
    total = len(results)
    print(f"\n{YELLOW}{'='*60}{RESET}")
    print(f"  结果: {GREEN}{passed}{RESET}/{total} 通过")
    if passed == total:
        print(f"  {GREEN}所有性能指标均达标 ✓{RESET}")
    else:
        print(f"  {RED}有 {total-passed} 项性能指标未达标，请检查数据库索引和查询优化{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}\n")
    return passed == total


if __name__ == "__main__":
    success = run_benchmarks()
    sys.exit(0 if success else 1)
