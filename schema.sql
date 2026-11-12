-- FlowGuard MySQL schema
-- Apply this file to a MySQL 8 database before running the application.

CREATE DATABASE IF NOT EXISTS flowguard_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE flowguard_db;

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id CHAR(36) NOT NULL,
    source_file VARCHAR(255) NOT NULL,
    status ENUM('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED') NOT NULL DEFAULT 'PENDING',
    started_at DATETIME(6) DEFAULT NULL,
    ended_at DATETIME(6) DEFAULT NULL,
    input_count INT UNSIGNED DEFAULT 0,
    accepted_count INT UNSIGNED DEFAULT 0,
    transformed_count INT UNSIGNED DEFAULT 0,
    published_count INT UNSIGNED DEFAULT 0,
    rejected_count INT UNSIGNED DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME DEFAULT NULL,
    PRIMARY KEY (run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS task_runs (
    task_run_id BIGINT NOT NULL AUTO_INCREMENT,
    run_id CHAR(36) NOT NULL,
    task_name VARCHAR(100) NOT NULL,
    attempt_number INT UNSIGNED NOT NULL DEFAULT 1,
    status ENUM('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'SKIPPED', 'TIMED_OUT') NOT NULL DEFAULT 'PENDING',
    started_at DATETIME(6) DEFAULT NULL,
    ended_at DATETIME(6) DEFAULT NULL,
    input_count INT UNSIGNED DEFAULT 0,
    output_count INT UNSIGNED DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (task_run_id),
    UNIQUE KEY uq_task_attempt (run_id, task_name, attempt_number),
    CONSTRAINT fk_task_run FOREIGN KEY (run_id) REFERENCES pipeline_runs (run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS source_orders (
    source_record_id BIGINT NOT NULL AUTO_INCREMENT,
    run_id CHAR(36) NOT NULL,
    source_file VARCHAR(255) NOT NULL,
    source_row_number INT UNSIGNED NOT NULL,
    order_id VARCHAR(100) DEFAULT NULL,
    customer_id VARCHAR(100) DEFAULT NULL,
    order_date DATETIME DEFAULT NULL,
    amount DECIMAL(12,2) DEFAULT NULL,
    order_status VARCHAR(30) DEFAULT NULL,
    raw_payload JSON DEFAULT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_record_id),
    UNIQUE KEY uq_source_row (run_id, source_row_number),
    KEY idx_source_order (order_id),
    CONSTRAINT fk_source_run FOREIGN KEY (run_id) REFERENCES pipeline_runs (run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS rejected_records (
    reject_id BIGINT NOT NULL AUTO_INCREMENT,
    run_id CHAR(36) NOT NULL,
    source_record_id BIGINT DEFAULT NULL,
    source_file VARCHAR(255) NOT NULL,
    source_row_number INT UNSIGNED NOT NULL,
    order_id VARCHAR(100) DEFAULT NULL,
    rejection_reason TEXT NOT NULL,
    raw_payload JSON DEFAULT NULL,
    rejected_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (reject_id),
    KEY idx_rejected_run (run_id),
    KEY fk_rejected_source (source_record_id),
    CONSTRAINT fk_rejected_run FOREIGN KEY (run_id) REFERENCES pipeline_runs (run_id),
    CONSTRAINT fk_rejected_source FOREIGN KEY (source_record_id) REFERENCES source_orders (source_record_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS transformed_orders (
    transformed_id BIGINT NOT NULL AUTO_INCREMENT,
    run_id CHAR(36) NOT NULL,
    source_record_id BIGINT NOT NULL,
    order_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    order_date DATETIME NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    order_status VARCHAR(30) NOT NULL,
    processed_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (transformed_id),
    UNIQUE KEY uq_transformed_source (source_record_id),
    KEY idx_transformed_order (order_id),
    KEY fk_transformed_run (run_id),
    CONSTRAINT fk_transformed_run FOREIGN KEY (run_id) REFERENCES pipeline_runs (run_id),
    CONSTRAINT fk_transformed_source FOREIGN KEY (source_record_id) REFERENCES source_orders (source_record_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS published_orders (
    published_id BIGINT NOT NULL AUTO_INCREMENT,
    order_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    order_date DATETIME NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    order_status VARCHAR(30) NOT NULL,
    source_run_id CHAR(36) NOT NULL,
    published_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (published_id),
    UNIQUE KEY uq_published_order (order_id),
    KEY idx_published_run (source_run_id),
    CONSTRAINT fk_published_run FOREIGN KEY (source_run_id) REFERENCES pipeline_runs (run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS notifications (
    notification_id BIGINT NOT NULL AUTO_INCREMENT,
    run_id CHAR(36) DEFAULT NULL,
    notification_type ENUM('FAILURE', 'SUCCESS', 'WARNING') NOT NULL,
    message TEXT NOT NULL,
    is_read TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (notification_id),
    KEY idx_notification_run (run_id),
    CONSTRAINT fk_notification_run FOREIGN KEY (run_id) REFERENCES pipeline_runs (run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
