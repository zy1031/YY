# 数据库文档

**数据库**：MySQL 8.0

**库名**：`animal_health_detection`

---

## 📋 数据表总览

| 表名 | 说明 |
|------|------|
| users | 用户表 |
| animal_types | 动物类型表 |
| animals | 动物档案表 |
| detection_models | 检测模型表 |
| detection_records | 检测记录表 |
| detection_results | 检测结果表 |
| tracking_records | 跟踪记录表 |
| llm_reports | LLM 报告表 |
| system_config | 系统配置表 |
| operation_logs | 操作日志表 |

---

## 表结构详情

### users — 用户表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO_INCREMENT | 用户 ID |
| username | VARCHAR(50) UNIQUE | 用户名 |
| password | VARCHAR(255) | 加密密码 |
| email | VARCHAR(100) | 邮箱 |
| role | ENUM('admin','user') | 角色 |
| status | ENUM('active','disabled') | 状态 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |
| last_login | DATETIME | 最后登录时间 |

---

### animal_types — 动物类型表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 类型 ID |
| name | VARCHAR(50) | 类型名称（牛/猪/羊）|
| description | VARCHAR(200) | 描述 |
| status | ENUM('active','disabled') | 状态 |
| created_at | DATETIME | 创建时间 |

---

### animals — 动物档案表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 动物 ID |
| animal_number | VARCHAR(50) UNIQUE | 编号 |
| animal_type_id | INT FK | 动物类型 ID |
| name | VARCHAR(100) | 名称/标识 |
| age_months | INT | 月龄 |
| gender | ENUM('male','female','unknown') | 性别 |
| weight_kg | DECIMAL(8,2) | 体重(kg) |
| notes | TEXT | 备注 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

---

### detection_models — 检测模型表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 模型 ID |
| model_name | VARCHAR(100) | 模型名称 |
| model_path | VARCHAR(500) | 模型文件路径 |
| model_version | VARCHAR(50) | 版本号 |
| framework | VARCHAR(50) | 框架（YOLOv8）|
| animal_type_id | INT FK | 适用动物类型 |
| confidence_threshold | FLOAT | 置信度阈值 |
| iou_threshold | FLOAT | IOU 阈值 |
| status | ENUM('active','disabled') | 状态 |
| created_at | DATETIME | 创建时间 |

---

### detection_records — 检测记录表（核心表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 记录 ID |
| user_id | INT FK | 用户 ID |
| animal_type_id | INT FK | 动物类型 ID |
| model_id | INT FK NULL | 使用的模型 ID |
| detection_type | ENUM('image','video','camera') | 检测类型 |
| detection_status | ENUM('pending','processing','completed','failed') | 状态 |
| file_path | VARCHAR(500) | 原始文件路径 |
| result_file_path | VARCHAR(500) | 结果文件路径 |
| total_targets | INT | 检测目标总数 |
| normal_count | INT | 正常数量 |
| abnormal_count | INT | 异常数量 |
| suspicious_count | INT | 可疑数量 |
| detection_duration | FLOAT | 检测耗时(秒) |
| notes | TEXT | 备注 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

**关键索引：**
```sql
idx_dr_user_created  (user_id, created_at)
idx_dr_user_type     (user_id, detection_type)
idx_dr_user_status   (user_id, detection_status)
```

---

### detection_results — 检测结果表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 结果 ID |
| detection_record_id | INT FK | 检测记录 ID |
| track_id | INT | 目标跟踪 ID |
| health_status | ENUM('normal','suspicious','abnormal') | 健康状态 |
| confidence | FLOAT | 置信度 |
| bbox_x1 | INT | 边界框左上角 X |
| bbox_y1 | INT | 边界框左上角 Y |
| bbox_x2 | INT | 边界框右下角 X |
| bbox_y2 | INT | 边界框右下角 Y |
| disease_type | VARCHAR(100) | 疾病类型（如检测到）|
| created_at | DATETIME | 创建时间 |

---

### tracking_records — 跟踪记录表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | ID |
| detection_record_id | INT FK | 检测记录 ID |
| track_id | INT | 跟踪目标 ID |
| frame_id | INT | 帧编号 |
| health_status | VARCHAR(50) | 健康状态 |
| confidence | FLOAT | 置信度 |
| bbox | JSON | 边界框坐标 |
| created_at | DATETIME | 创建时间 |

---

### llm_reports — LLM 报告表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 报告 ID |
| detection_record_id | INT FK | 检测记录 ID |
| report_type | VARCHAR(50) | 报告类型 |
| report_title | VARCHAR(200) | 报告标题 |
| report_content | LONGTEXT | 报告正文（Markdown）|
| report_file_path | VARCHAR(500) | Markdown 文件路径 |
| summary | VARCHAR(500) | 摘要 |
| health_assessment | VARCHAR(50) | 健康评估（正常/需关注/警告）|
| generation_status | ENUM('pending','generating','completed','failed') | 生成状态 |
| llm_model_used | VARCHAR(100) | 使用的 LLM 模型 |
| error_message | TEXT | 错误信息 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

---

### system_config — 系统配置表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | ID |
| config_key | VARCHAR(100) UNIQUE | 配置键 |
| config_value | TEXT | 配置值 |
| config_type | VARCHAR(50) | 配置类型 |
| description | VARCHAR(200) | 描述 |
| updated_at | DATETIME | 更新时间 |

**预置配置项：**

| config_key | 说明 | 默认值 |
|------------|------|--------|
| current_model_id | 当前检测模型 ID | - |
| confidence_threshold | 全局置信度阈值 | 0.5 |
| iou_threshold | 全局 IOU 阈值 | 0.45 |
| max_upload_size_mb | 最大上传文件大小 | 100 |
| report_auto_generate | 是否自动生成报告 | false |

---

### operation_logs — 操作日志表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | ID |
| user_id | INT FK | 用户 ID |
| operation_type | VARCHAR(50) | 操作类型 |
| operation_detail | TEXT | 操作详情 |
| ip_address | VARCHAR(50) | IP 地址 |
| created_at | DATETIME | 创建时间 |

---

## 🔗 表关系图

```
users
  └─> detection_records
          ├─> detection_results
          ├─> tracking_records
          └─> llm_reports

animal_types
  ├─> animals
  ├─> detection_models
  └─> detection_records

detection_models
  └─> detection_records
```

---

## 🗄️ 初始化与维护

```sql
-- 初始化数据库
mysql -u root -p < init_database.sql

-- 执行索引优化
mysql -u root -p animal_health_detection < optimize_indexes.sql

-- 备份数据库
mysqldump -u root -p animal_health_detection > backup_$(date +%Y%m%d).sql

-- 恢复数据库
mysql -u root -p animal_health_detection < backup_20260101.sql
```
