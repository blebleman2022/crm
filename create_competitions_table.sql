-- 创建 customer_competitions 表
CREATE TABLE IF NOT EXISTS customer_competitions (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    competition_name_id INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT '未报名',
    custom_award VARCHAR(100),
    created_by_user_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE CASCADE,
    FOREIGN KEY(competition_name_id) REFERENCES competition_names (id) ON DELETE CASCADE,
    FOREIGN KEY(created_by_user_id) REFERENCES users (id)
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_customer_competitions_customer_id ON customer_competitions (customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_competitions_competition_name_id ON customer_competitions (competition_name_id);
CREATE INDEX IF NOT EXISTS idx_customer_competitions_status ON customer_competitions (status);

