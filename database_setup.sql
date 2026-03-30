-- ============================================================
-- 动物健康检测系统 - 数据库完整初始化脚本
-- 版本：v1.0（合并版）
-- 包含：建表、初始化数据、视图、存储过程、触发器、性能索引
-- 兼容：MySQL 8.0+
-- 使用：mysql -u root -p < database_setup.sql
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS animal_health_detection
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE animal_health_detection;

-- ============================================================
-- SECTION 1：数据表
-- ============================================================

-- 1.1 用户表
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
    password VARCHAR(255) NOT NULL COMMENT '密码（bcrypt加密）',
    email VARCHAR(100) COMMENT '邮箱',
    role ENUM('admin', 'user') DEFAULT 'user',
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    password_expire_at TIMESTAMP NULL,
    INDEX idx_username (username),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 1.2 动物类型表
DROP TABLE IF EXISTS animal_types;
CREATE TABLE animal_types (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='动物类型表';

-- 1.3 检测模型表
DROP TABLE IF EXISTS detection_models;
CREATE TABLE detection_models (
    id INT PRIMARY KEY AUTO_INCREMENT,
    animal_type_id INT NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    model_path VARCHAR(255) NOT NULL,
    model_version VARCHAR(50),
    framework VARCHAR(50),
    confidence_threshold FLOAT DEFAULT 0.5,
    iou_threshold FLOAT DEFAULT 0.45,
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_type_id) REFERENCES animal_types(id) ON DELETE RESTRICT,
    INDEX idx_animal_type (animal_type_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='检测模型表';

-- 1.4 动物档案表
DROP TABLE IF EXISTS animals;
CREATE TABLE animals (
    id INT PRIMARY KEY AUTO_INCREMENT,
    animal_type_id INT NOT NULL,
    animal_number VARCHAR(100) UNIQUE NOT NULL,
    breed VARCHAR(100),
    age INT,
    weight FLOAT,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_type_id) REFERENCES animal_types(id) ON DELETE RESTRICT,
    INDEX idx_animal_number (animal_number),
    INDEX idx_an_type_number (animal_type_id, animal_number),
    INDEX idx_an_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='动物档案表';

-- 1.5 检测记录表
-- model_id 和 animal_type_id 均允许 NULL（已合并 fix_detection_records.sql）
DROP TABLE IF EXISTS detection_records;
CREATE TABLE detection_records (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    animal_type_id INT NULL COMMENT '可为空',
    model_id INT NULL COMMENT '可为空，无模型时为NULL',
    detection_type ENUM('image', 'video', 'camera') NOT NULL,
    input_source VARCHAR(255) NOT NULL,
    input_file_path VARCHAR(255),
    output_file_path VARCHAR(255),
    detection_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    error_message TEXT,
    total_targets INT DEFAULT 0,
    normal_count INT DEFAULT 0,
    suspicious_count INT DEFAULT 0,
    abnormal_count INT DEFAULT 0,
    processing_time INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (animal_type_id) REFERENCES animal_types(id) ON DELETE SET NULL,
    FOREIGN KEY (model_id) REFERENCES detection_models(id) ON DELETE SET NULL,
    INDEX idx_user (user_id),
    INDEX idx_animal_type (animal_type_id),
    INDEX idx_detection_type (detection_type),
    INDEX idx_status (detection_status),
    INDEX idx_created_at (created_at),
    INDEX idx_dr_user_created (user_id, created_at),
    INDEX idx_dr_user_type (user_id, detection_type),
    INDEX idx_dr_user_status (user_id, detection_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='检测记录表';

-- 1.6 检测结果表
DROP TABLE IF EXISTS detection_results;
CREATE TABLE detection_results (
    id INT PRIMARY KEY AUTO_INCREMENT,
    detection_record_id INT NOT NULL,
    target_index INT NOT NULL,
    class_name VARCHAR(100) NOT NULL,
    confidence FLOAT NOT NULL,
    health_status ENUM('normal', 'suspicious', 'abnormal') DEFAULT 'normal',
    bbox_x1 INT, bbox_y1 INT, bbox_x2 INT, bbox_y2 INT,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (detection_record_id) REFERENCES detection_records(id) ON DELETE CASCADE,
    INDEX idx_dres_record_id (detection_record_id),
    INDEX idx_dres_health_status (health_status),
    INDEX idx_dres_record_health (detection_record_id, health_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='检测结果表';

-- 1.7 BoT-SORT 跟踪记录表
DROP TABLE IF EXISTS tracking_records;
CREATE TABLE tracking_records (
    id INT PRIMARY KEY AUTO_INCREMENT,
    detection_record_id INT NOT NULL,
    track_id INT NOT NULL,
    animal_id INT NULL,
    start_frame INT, end_frame INT,
    start_time DATETIME, end_time DATETIME,
    duration_seconds INT,
    total_frames INT,
    trajectory_data JSON,
    avg_confidence FLOAT,
    health_status_summary VARCHAR(50),
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (detection_record_id) REFERENCES detection_records(id) ON DELETE CASCADE,
    FOREIGN KEY (animal_id) REFERENCES animals(id) ON DELETE SET NULL,
    INDEX idx_tr_record_id (detection_record_id),
    INDEX idx_tr_track_id (track_id),
    INDEX idx_animal_id (animal_id),
    INDEX idx_tracking_detection_track (detection_record_id, track_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='BoT-SORT跟踪记录表';

-- 1.8 轨迹点表
DROP TABLE IF EXISTS trajectory_points;
CREATE TABLE trajectory_points (
    id INT PRIMARY KEY AUTO_INCREMENT,
    tracking_record_id INT NOT NULL,
    frame_number INT NOT NULL,
    timestamp DATETIME,
    center_x FLOAT NOT NULL, center_y FLOAT NOT NULL,
    bbox_x1 INT, bbox_y1 INT, bbox_x2 INT, bbox_y2 INT,
    confidence FLOAT,
    health_status ENUM('normal', 'suspicious', 'abnormal'),
    velocity_x FLOAT, velocity_y FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tracking_record_id) REFERENCES tracking_records(id) ON DELETE CASCADE,
    INDEX idx_tracking_record (tracking_record_id),
    INDEX idx_frame_number (frame_number),
    INDEX idx_trajectory_tracking_frame (tracking_record_id, frame_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='轨迹点表';

-- 1.9 LLM 报告表
DROP TABLE IF EXISTS llm_reports;
CREATE TABLE llm_reports (
    id INT PRIMARY KEY AUTO_INCREMENT,
    detection_record_id INT NOT NULL,
    report_type ENUM('image', 'video', 'camera') NOT NULL,
    report_title VARCHAR(255),
    report_content LONGTEXT NOT NULL,
    report_format ENUM('text', 'pdf') DEFAULT 'text',
    report_file_path VARCHAR(255),
    summary TEXT,
    health_assessment VARCHAR(100),
    abnormal_details TEXT,
    recommendations TEXT,
    llm_model_used VARCHAR(100),
    generation_status ENUM('pending', 'generating', 'completed', 'failed') DEFAULT 'pending',
    error_message TEXT,
    generation_time INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (detection_record_id) REFERENCES detection_records(id) ON DELETE CASCADE,
    INDEX idx_lr_record_id (detection_record_id),
    INDEX idx_lr_status (generation_status),
    INDEX idx_lr_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='LLM报告表';

-- 1.10 系统配置表
DROP TABLE IF EXISTS system_config;
CREATE TABLE system_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    config_type ENUM('detection', 'tracking', 'llm', 'system') DEFAULT 'system',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_config_key (config_key),
    INDEX idx_config_type (config_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';

-- 1.11 用户个性化配置表
DROP TABLE IF EXISTS user_config;
CREATE TABLE user_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    config_key VARCHAR(100) NOT NULL,
    config_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_config (user_id, config_key),
    INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户个性化配置表';

-- 1.12 操作日志表
DROP TABLE IF EXISTS operation_logs;
CREATE TABLE operation_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NULL,
    operation_type VARCHAR(100) NOT NULL,
    operation_detail TEXT,
    resource_type VARCHAR(100),
    resource_id INT,
    status ENUM('success', 'failed') DEFAULT 'success',
    error_message TEXT,
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_ol_user_created (user_id, created_at),
    INDEX idx_ol_operation_type (operation_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作日志表';

-- ============================================================
-- SECTION 2：初始化数据
-- ============================================================

INSERT INTO animal_types (name, description, status) VALUES
  ('猪', '家猪，常见养殖动物', 'active'),
  ('牛', '家牛，常见养殖动物', 'active'),
  ('羊', '绵羊，常见养殖动物', 'active')
ON DUPLICATE KEY UPDATE description=VALUES(description), status=VALUES(status);

INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
  ('default_confidence_threshold', '0.5',      'detection', '默认置信度阈值'),
  ('default_iou_threshold',        '0.45',     'detection', '默认IoU阈值'),
  ('bot_sort_track_threshold',     '0.5',      'tracking',  'BoT-SORT跟踪阈值'),
  ('bot_sort_max_age',             '30',       'tracking',  'BoT-SORT目标最大消失帧数'),
  ('bot_sort_min_hits',            '3',        'tracking',  'BoT-SORT最小检测次数'),
  ('llm_report_template',         'detailed', 'llm',       'LLM报告模板类型'),
  ('llm_model_name',              'chatglm',  'llm',       '使用的LLM模型名称'),
  ('camera_fps',                  '10',       'system',    '摄像头检测帧率'),
  ('video_process_interval',      '1',        'system',    '视频处理间隔帧数'),
  ('max_upload_size',             '500',      'system',    '最大上传文件大小（MB）'),
  ('detection_timeout',           '300',      'system',    '检测超时时间（秒）'),
  ('enable_trajectory_visualization', 'true', 'system',    '是否启用轨迹可视化'),
  ('trajectory_color_normal',     '#00FF00',  'system',    '正常轨迹颜色'),
  ('trajectory_color_suspicious', '#FFFF00',  'system',    '可疑轨迹颜色'),
  ('trajectory_color_abnormal',   '#FF0000',  'system',    '异常轨迹颜色')
ON DUPLICATE KEY UPDATE config_value=VALUES(config_value);

INSERT INTO users (username, password, email, role, status) VALUES
  ('admin', 'admin123', 'admin@example.com', 'admin', 'active')
ON DUPLICATE KEY UPDATE email=VALUES(email), status=VALUES(status);

UPDATE users
SET password_expire_at = DATE_ADD(NOW(), INTERVAL 90 DAY)
WHERE password_expire_at IS NULL;
-- ============================================================

-- ============================================================
-- SECTION 3: Views
-- ============================================================

DROP VIEW IF EXISTS v_detection_statistics;
CREATE VIEW v_detection_statistics AS
SELECT at.id AS animal_type_id, at.name AS animal_type,
    COUNT(dr.id) AS total_detections,
    SUM(dr.total_targets) AS total_targets,
    SUM(dr.normal_count) AS normal_count,
    SUM(dr.suspicious_count) AS suspicious_count,
    SUM(dr.abnormal_count) AS abnormal_count,
    ROUND(AVG(dr.processing_time), 2) AS avg_processing_time,
    DATE(dr.created_at) AS detection_date
FROM detection_records dr
JOIN animal_types at ON dr.animal_type_id = at.id
WHERE dr.detection_status = 'completed'
GROUP BY at.id, at.name, DATE(dr.created_at);

DROP VIEW IF EXISTS v_tracking_statistics;
CREATE VIEW v_tracking_statistics AS
SELECT tr.detection_record_id,
    COUNT(tr.id) AS total_tracks,
    SUM(tr.duration_seconds) AS total_duration_seconds,
    ROUND(AVG(tr.avg_confidence), 4) AS avg_confidence,
    MAX(tr.end_frame) AS max_frame,
    MIN(tr.start_frame) AS min_frame
FROM tracking_records tr
GROUP BY tr.detection_record_id;

DROP VIEW IF EXISTS v_user_detection_activity;
CREATE VIEW v_user_detection_activity AS
SELECT u.id AS user_id, u.username,
    COUNT(dr.id) AS total_detections,
    COUNT(DISTINCT dr.animal_type_id) AS animal_types_used,
    COUNT(DISTINCT DATE(dr.created_at)) AS active_days,
    MAX(dr.created_at) AS last_detection_time
FROM users u
LEFT JOIN detection_records dr ON u.id = dr.user_id
GROUP BY u.id, u.username;

DROP VIEW IF EXISTS v_abnormal_detection_summary;
CREATE VIEW v_abnormal_detection_summary AS
SELECT dr.id AS detection_record_id, dr.detection_type,
    at.name AS animal_type, u.username,
    dr.abnormal_count, dr.suspicious_count, dr.total_targets,
    ROUND(100*(dr.abnormal_count+dr.suspicious_count)/NULLIF(dr.total_targets,0),2) AS abnormal_rate,
    dr.created_at
FROM detection_records dr
JOIN animal_types at ON dr.animal_type_id = at.id
JOIN users u ON dr.user_id = u.id
WHERE dr.detection_status = 'completed'
  AND (dr.abnormal_count > 0 OR dr.suspicious_count > 0)
ORDER BY dr.created_at DESC;

DROP VIEW IF EXISTS v_report_generation_statistics;
CREATE VIEW v_report_generation_statistics AS
SELECT lr.report_type,
    COUNT(lr.id) AS total_reports,
    SUM(CASE WHEN lr.generation_status = 'completed' THEN 1 ELSE 0 END) AS completed_reports,
    SUM(CASE WHEN lr.generation_status = 'failed' THEN 1 ELSE 0 END) AS failed_reports,
    ROUND(AVG(lr.generation_time), 2) AS avg_generation_time,
    DATE(lr.created_at) AS report_date
FROM llm_reports lr
GROUP BY lr.report_type, DATE(lr.created_at);

-- ============================================================
-- SECTION 4: Stored Procedures
-- ============================================================

DROP PROCEDURE IF EXISTS sp_get_user_detection_stats;
DELIMITER //
CREATE PROCEDURE sp_get_user_detection_stats(IN p_user_id INT, IN p_days INT)
BEGIN
    SELECT at.name AS animal_type, COUNT(dr.id) AS detection_count,
        SUM(dr.total_targets) AS total_targets,
        SUM(dr.abnormal_count) AS abnormal_count,
        ROUND(AVG(dr.processing_time), 2) AS avg_processing_time
    FROM detection_records dr
    JOIN animal_types at ON dr.animal_type_id = at.id
    WHERE dr.user_id = p_user_id
      AND dr.detection_status = 'completed'
      AND dr.created_at >= DATE_SUB(NOW(), INTERVAL p_days DAY)
    GROUP BY at.id, at.name;
END //
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_update_detection_stats;
DELIMITER //
CREATE PROCEDURE sp_update_detection_stats(IN p_detection_record_id INT)
BEGIN
    UPDATE detection_records SET
        total_targets    = (SELECT COUNT(*) FROM detection_results WHERE detection_record_id = p_detection_record_id),
        normal_count     = (SELECT COUNT(*) FROM detection_results WHERE detection_record_id = p_detection_record_id AND health_status = 'normal'),
        suspicious_count = (SELECT COUNT(*) FROM detection_results WHERE detection_record_id = p_detection_record_id AND health_status = 'suspicious'),
        abnormal_count   = (SELECT COUNT(*) FROM detection_results WHERE detection_record_id = p_detection_record_id AND health_status = 'abnormal')
    WHERE id = p_detection_record_id;
END //
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_get_detection_statistics;
DELIMITER //
CREATE PROCEDURE sp_get_detection_statistics(IN p_start_date DATE, IN p_end_date DATE)
BEGIN
    SELECT DATE(dr.created_at) AS stat_date, at.name AS animal_type, dr.detection_type,
        COUNT(dr.id) AS detection_count, SUM(dr.total_targets) AS total_targets,
        SUM(dr.abnormal_count) AS abnormal_count,
        ROUND(AVG(dr.processing_time), 2) AS avg_processing_time
    FROM detection_records dr
    JOIN animal_types at ON dr.animal_type_id = at.id
    WHERE dr.detection_status = 'completed'
      AND DATE(dr.created_at) BETWEEN p_start_date AND p_end_date
    GROUP BY DATE(dr.created_at), at.id, at.name, dr.detection_type
    ORDER BY stat_date DESC, animal_type;
END //
DELIMITER ;

-- ============================================================
-- SECTION 5: Triggers
-- ============================================================

DROP TRIGGER IF EXISTS tr_update_detection_records_timestamp;
DELIMITER //
CREATE TRIGGER tr_update_detection_records_timestamp
BEFORE UPDATE ON detection_records
FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END //
DELIMITER ;

-- ============================================================
-- SECTION 6: Performance Indexes (idempotent)
-- ============================================================

DROP PROCEDURE IF EXISTS _add_idx;
DELIMITER //
CREATE PROCEDURE _add_idx(IN t VARCHAR(64), IN n VARCHAR(64), IN c VARCHAR(256))
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.STATISTICS
    WHERE table_schema = DATABASE() AND table_name = t AND index_name = n
  ) THEN
    SET @s = CONCAT('CREATE INDEX ', n, ' ON ', t, ' (', c, ')'  );
    PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;
  END IF;
END //
DELIMITER ;

CALL _add_idx('animals',        'idx_an_type_number',    'animal_type_id, animal_number');
CALL _add_idx('animals',        'idx_an_created_at',     'created_at');
CALL _add_idx('llm_reports',    'idx_lr_record_id',      'detection_record_id');
CALL _add_idx('llm_reports',    'idx_lr_status',         'generation_status');
CALL _add_idx('llm_reports',    'idx_lr_created_at',     'created_at');
CALL _add_idx('operation_logs', 'idx_ol_user_created',   'user_id, created_at');
CALL _add_idx('operation_logs', 'idx_ol_operation_type', 'operation_type');

DROP PROCEDURE IF EXISTS _add_idx;

-- ============================================================
SET FOREIGN_KEY_CHECKS = 1;
SELECT '数据库初始化完成！' AS result;
