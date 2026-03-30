# 部署指南

## 环境要求

| 组件 | 版本要求 |
|------|----------|
| Python | 3.8+ |
| Node.js | 16+ |
| MySQL | 8.0+ |
| 操作系统 | Windows 10 / Ubuntu 20.04+ |
| 内存 | ≥ 8GB（推荐 16GB）|
| 磁盘 | ≥ 20GB |

---

## 一、开发环境部署

### 1.1 克隆项目

```bash
git clone <项目地址>
cd "Animal Health Monitoring System"
```

### 1.2 数据库初始化

```sql
-- 登录 MySQL
mysql -u root -p

-- 执行初始化脚本
SOURCE init_database.sql;

-- 执行索引优化
SOURCE optimize_indexes.sql;
```

### 1.3 后端配置

```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 可选依赖
pip install reportlab      # PDF 生成
pip install psutil         # 系统监控
```

**配置数据库连接**（`backend/app/core/config.py`）：

```python
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "your_password"
DB_NAME = "animal_health_detection"
```

或通过环境变量配置：

```bash
# Windows PowerShell
$env:DB_PASSWORD = "your_password"

# Linux/Mac
export DB_PASSWORD="your_password"
```

### 1.4 启动后端

```bash
cd backend
python main.py
```

后端默认运行在 `http://localhost:8000`

API 文档访问：`http://localhost:8000/docs`

### 1.5 前端配置

```bash
cd frontend/my-vue-app
npm install
```

**配置后端地址**（如需修改）：

在各 `src/api/*.ts` 文件中修改 `http://localhost:8000` 为实际后端地址。

### 1.6 启动前端

```bash
npm run dev
```

前端默认运行在 `http://localhost:5173`

---

## 二、生产环境部署

### 2.1 后端生产启动

```bash
# 安装 gunicorn（Linux 推荐）
pip install gunicorn

# 启动（4 个 worker）
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log

# Windows 使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

### 2.2 前端生产构建

```bash
cd frontend/my-vue-app
npm run build
# 产物在 dist/ 目录
```

### 2.3 Nginx 配置（推荐）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    root /path/to/frontend/my-vue-app/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
    }

    # WebSocket 代理
    location /api/camera/ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 上传文件访问
    location /uploads/ {
        alias /path/to/backend/uploads/;
    }
}
```

### 2.4 systemd 服务（Linux）

```ini
# /etc/systemd/system/animal-health.service
[Unit]
Description=Animal Health Detection System
After=network.target mysql.service

[Service]
Type=simple
User=www
WorkingDirectory=/path/to/backend
ExecStart=/path/to/venv/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable animal-health
systemctl start animal-health
systemctl status animal-health
```

---

## 三、数据库备份方案

### 3.1 手动备份

```bash
# 备份
mysqldump -u root -p animal_health_detection > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复
mysql -u root -p animal_health_detection < backup_20260101_120000.sql
```

### 3.2 自动备份脚本

```bash
#!/bin/bash
# backup.sh - 每天凌晨 2 点自动备份，保留最近 7 天

BACKUP_DIR="/backup/mysql"
DATE=$(date +%Y%m%d)
DB_NAME="animal_health_detection"

mkdir -p $BACKUP_DIR
mysqldump -u root -p"$DB_PASSWORD" $DB_NAME | gzip > "$BACKUP_DIR/${DB_NAME}_${DATE}.sql.gz"

# 删除 7 天前的备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "备份完成：${DB_NAME}_${DATE}.sql.gz"
```

```bash
# 添加 cron 任务
crontab -e
# 0 2 * * * /path/to/backup.sh
```

---

## 四、日志管理

### 4.1 后端日志

应用日志通过 Python `logging` 模块输出，格式：

```
2026-03-22 10:00:00,000 [INFO] main: 应用启动...
2026-03-22 10:01:00,000 [ERROR] main: Unhandled exception: ...
```

建议配置日志文件：

```python
# 在 main.py 中添加
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
```

### 4.2 日志轮转

```bash
# /etc/logrotate.d/animal-health
/path/to/backend/logs/*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
    postrotate
        systemctl reload animal-health
    endscript
}
```

---

## 五、监控告警

### 5.1 健康检查监控

使用 `/health/detail` 接口进行定期健康检查：

```bash
# 简单监控脚本
while true; do
  STATUS=$(curl -s http://localhost:8000/health | python -c "import sys,json; print(json.load(sys.stdin)['status'])")
  if [ "$STATUS" != "ok" ]; then
    echo "[ALERT] 系统异常！状态：$STATUS" | mail -s "系统告警" admin@example.com
  fi
  sleep 60
done
```

### 5.2 磁盘空间监控

```bash
# 检查 uploads 目录大小
du -sh backend/uploads/

# 当磁盘使用超过 80% 时告警
df -h | awk '$5 > 80 {print "磁盘告警：" $0}'
```

---

## 六、常见问题

### Q1：后端启动报数据库连接错误

检查 MySQL 服务是否启动，密码是否正确，数据库是否已创建。

```bash
mysql -u root -p -e "SHOW DATABASES;" | grep animal
```

### Q2：图片检测返回 mock 结果

系统在无模型文件时自动进入 mock 模式。请在模型管理页面配置 YOLO 模型文件路径。

### Q3：WebSocket 连接失败

检查 Nginx 是否配置了 WebSocket 代理（`Upgrade` 和 `Connection` 头）。

### Q4：PDF 下载为 HTML 格式

安装 reportlab：`pip install reportlab`，确保系统中有中文字体（Windows 默认有 simhei.ttf）。

### Q5：前端无法访问后端接口（CORS 错误）

在 `main.py` 的 CORS 配置中添加前端地址：

```python
allow_origins=[
    "http://localhost:5173",
    "http://your-frontend-domain.com",
]
```
