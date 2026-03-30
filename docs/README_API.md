# API 接口文档

**基础 URL**：`http://localhost:8000`

**认证方式**：Bearer Token（JWT）

所有需要认证的接口请在请求头中携带：
```
Authorization: Bearer <token>
```

---

## 📋 目录

- [认证接口](#认证接口)
- [用户接口](#用户接口)
- [动物类型接口](#动物类型接口)
- [动物档案接口](#动物档案接口)
- [模型管理接口](#模型管理接口)
- [图片检测接口](#图片检测接口)
- [视频检测接口](#视频检测接口)
- [摄像头检测接口](#摄像头检测接口)
- [统计接口](#统计接口)
- [报告接口](#报告接口)
- [系统配置接口](#系统配置接口)
- [健康检查接口](#健康检查接口)

---

## 认证接口

### POST `/api/auth/register` — 注册

**请求体：**
```json
{
  "username": "string",
  "password": "string",
  "email": "string"
}
```

**响应：**
```json
{
  "message": "注册成功",
  "user_id": 1
}
```

---

### POST `/api/auth/login` — 登录

**请求体：**
```json
{
  "username": "string",
  "password": "string"
}
```

**响应：**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "username": "string"
}
```

---

## 用户接口

### GET `/api/users/profile` — 获取当前用户信息 🔒

**响应：**
```json
{
  "id": 1,
  "username": "string",
  "email": "string",
  "role": "user",
  "status": "active"
}
```

### PUT `/api/users/profile` — 更新用户信息 🔒

**请求体：**
```json
{
  "email": "string",
  "password": "string"
}
```

---

## 动物类型接口

### GET `/api/animal-types/` — 获取动物类型列表 🔒

**响应：**
```json
{
  "animal_types": [
    { "id": 1, "name": "牛", "description": "肉牛/奶牛" }
  ]
}
```

---

## 动物档案接口

### GET `/api/animals/` — 获取动物列表 🔒

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码（默认 1）|
| page_size | int | 每页数量（默认 10）|
| animal_type_id | int | 按类型筛选 |

### POST `/api/animals/` — 创建动物档案 🔒

**请求体：**
```json
{
  "animal_number": "A001",
  "animal_type_id": 1,
  "name": "花花",
  "age_months": 24,
  "gender": "female",
  "weight_kg": 450.5,
  "notes": "备注"
}
```

### GET `/api/animals/{id}` — 获取动物详情 🔒

### PUT `/api/animals/{id}` — 更新动物信息 🔒

### DELETE `/api/animals/{id}` — 删除动物档案 🔒

---

## 模型管理接口

### GET `/api/models/` — 获取模型列表 🔒

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| animal_type_id | int | 按动物类型筛选 |

**响应：**
```json
{
  "models": [
    {
      "id": 1,
      "model_name": "YOLOv8-Cattle",
      "model_version": "v1.0",
      "framework": "YOLOv8",
      "animal_type_id": 1,
      "confidence_threshold": 0.5,
      "iou_threshold": 0.45
    }
  ]
}
```

### GET `/api/models/switch` — 获取当前激活模型 🔒

### POST `/api/models/switch` — 切换当前模型 🔒

**请求体：**
```json
{ "model_id": 1 }
```

### PUT `/api/models/{id}/config` — 更新模型参数 🔒

```json
{
  "confidence_threshold": 0.6,
  "iou_threshold": 0.5
}
```

---

## 图片检测接口

### POST `/api/detection/image/upload` — 上传图片 🔒

**请求：** `multipart/form-data`，字段名 `file`

**响应：**
```json
{
  "message": "上传成功",
  "filename": "abc123.jpg",
  "file_path": "uploads/images/abc123.jpg"
}
```

### POST `/api/detection/image/detect` — 执行检测 🔒

**请求：** `multipart/form-data`
| 字段 | 类型 | 说明 |
|------|------|------|
| file_path | string | 上传后的文件路径 |
| animal_type_id | int | 动物类型 ID（可选）|

**响应：**
```json
{
  "record_id": 1,
  "total_targets": 3,
  "normal_count": 2,
  "abnormal_count": 1,
  "suspicious_count": 0,
  "detections": [
    {
      "track_id": 1,
      "health_status": "abnormal",
      "confidence": 0.92,
      "bbox": [100, 200, 300, 400]
    }
  ],
  "annotated_image_url": "/api/detection/file/result_abc123.jpg"
}
```

### GET `/api/detection/history` — 获取检测历史 🔒

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码 |
| page_size | int | 每页数量 |
| detection_type | string | image/video/camera |
| start_date | string | 开始日期 YYYY-MM-DD |
| end_date | string | 结束日期 |

### GET `/api/detection/{id}` — 获取检测记录详情 🔒

### DELETE `/api/detection/{id}` — 删除检测记录 🔒

---

## 视频检测接口

### POST `/api/video/upload` — 上传视频 🔒

### POST `/api/video/detect` — 提交视频检测任务 🔒

### GET `/api/video/task/{task_id}` — 查询任务状态 🔒

**响应：**
```json
{
  "task_id": "uuid",
  "status": "running",  // pending/running/completed/failed
  "progress": 65,
  "result": null
}
```

---

## 摄像头检测接口

### POST `/api/camera/start` — 启动摄像头检测 🔒

### POST `/api/camera/stop` — 停止摄像头检测 🔒

### GET `/api/camera/status` — 获取检测状态 🔒

### WebSocket `/api/camera/ws/{session_id}` — 实时结果推送

**推送消息格式：**
```json
{
  "type": "detection_result",
  "frame_id": 100,
  "targets": [
    { "track_id": 1, "health_status": "normal", "confidence": 0.88 }
  ],
  "summary": { "total": 3, "normal": 2, "abnormal": 1 }
}
```

---

## 统计接口

### GET `/api/statistics/overview` — 总体统计概览 🔒

**响应：**
```json
{
  "total_detections": 128,
  "today_detections": 5,
  "total_targets": 384,
  "total_abnormal": 12,
  "total_suspicious": 8,
  "type_stats": [
    { "type": "image", "count": 100 }
  ]
}
```

### GET `/api/statistics/trend?days=7` — 检测趋势 🔒

### GET `/api/statistics/by-animal-type` — 按动物类型统计 🔒

### GET `/api/statistics/health-distribution` — 健康状态分布 🔒

---

## 报告接口

### POST `/api/reports/generate` — 生成检测报告 🔒

**请求体：**
```json
{ "detection_record_id": 1 }
```

**响应：**
```json
{
  "message": "报告生成任务已提交",
  "task_id": "uuid",
  "report_id": 1,
  "is_mock": true
}
```

### GET `/api/reports/` — 获取报告列表 🔒

**查询参数：** `page`, `page_size`

### GET `/api/reports/{id}` — 获取报告详情 🔒

### DELETE `/api/reports/{id}` — 删除报告 🔒

### GET `/api/reports/{id}/download` — 下载 Markdown 报告 🔒

### GET `/api/reports/{id}/download/pdf` — 下载 PDF 报告 🔒

---

## 系统配置接口

### GET `/api/config/` — 获取所有配置 🔒

### PUT `/api/config/{key}` — 更新配置项 🔒

**请求体：**
```json
{ "config_value": "0.6" }
```

### POST `/api/config/init-defaults` — 初始化默认配置 🔒

---

## 健康检查接口

### GET `/health` — 基础健康检查

```json
{ "status": "ok", "version": "1.0.0" }
```

### GET `/health/detail` — 详细系统状态

```json
{
  "status": "ok",
  "version": "1.0.0",
  "database": { "status": "ok" },
  "system": {
    "cpu_percent": 12.5,
    "memory_percent": 45.2,
    "disk_percent": 38.1
  }
}
```

---

## 错误码说明

| HTTP 状态码 | 说明 |
|------------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未认证（Token 无效或缺失）|
| 403 | 无权限访问 |
| 404 | 资源不存在 |
| 422 | 请求体格式错误 |
| 500 | 服务器内部错误 |

所有错误响应格式：
```json
{ "detail": "错误描述信息" }
```

---

> 交互式 API 文档：启动后端后访问 http://localhost:8000/docs
