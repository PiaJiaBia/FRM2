CREATE TABLE IF NOT EXISTS frm_dataset_ui (
    dataset_id CHAR(36) CHARACTER SET ascii PRIMARY KEY,
    display_name VARCHAR(128) NOT NULL,
    archived BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (dataset_id) REFERENCES frm_datasets(dataset_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS frm_calculation_ui (
    run_id CHAR(36) CHARACTER SET ascii PRIMARY KEY,
    job_id CHAR(36) CHARACTER SET ascii NOT NULL UNIQUE,
    display_name VARCHAR(128) NOT NULL,
    archived BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (run_id) REFERENCES frm_calculations(run_id)
) ENGINE=InnoDB;

INSERT IGNORE INTO frm_schema_versions (version) VALUES (2);
