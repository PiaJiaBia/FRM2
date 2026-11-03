CREATE TABLE IF NOT EXISTS frm_schema_versions (
    version INT PRIMARY KEY,
    applied_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS frm_datasets (
    dataset_id CHAR(36) CHARACTER SET ascii PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT NOT NULL,
    row_count BIGINT UNSIGNED NOT NULL,
    column_count INT UNSIGNED NOT NULL,
    sha256 CHAR(64) CHARACTER SET ascii NOT NULL,
    frame_json LONGTEXT NOT NULL,
    metadata_json LONGTEXT NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX idx_dataset_name_created (name, created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS frm_calculations (
    run_id CHAR(36) CHARACTER SET ascii PRIMARY KEY,
    dataset_id CHAR(36) CHARACTER SET ascii NOT NULL,
    operation VARCHAR(255) NOT NULL,
    parameters_json LONGTEXT NOT NULL,
    result_json LONGTEXT NOT NULL,
    source_sha256 CHAR(64) CHARACTER SET ascii NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_frm_calculation_dataset FOREIGN KEY (dataset_id) REFERENCES frm_datasets(dataset_id),
    INDEX idx_calculation_dataset_created (dataset_id, created_at)
) ENGINE=InnoDB;

INSERT IGNORE INTO frm_schema_versions (version) VALUES (1);
