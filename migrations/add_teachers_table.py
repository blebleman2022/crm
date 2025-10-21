#!/usr/bin/env python3
"""
数据库迁移脚本：添加teachers表和customer表的teacher_id字段
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Teacher, Customer
from run import app

def migrate():
    """执行数据库迁移"""
    with app.app_context():
        print("开始数据库迁移...")

        # 创建teachers表
        print("1. 创建teachers表...")
        with db.engine.connect() as conn:
            conn.execute(db.text("""
                CREATE TABLE IF NOT EXISTS teachers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chinese_name VARCHAR(50) NOT NULL,
                    english_name VARCHAR(100),
                    current_institution VARCHAR(200),
                    major_direction VARCHAR(200),
                    highest_degree VARCHAR(50),
                    degree_description TEXT,
                    research_achievements TEXT,
                    innovation_coaching_achievements TEXT,
                    social_roles TEXT,
                    status BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
        print("   ✓ teachers表创建成功")

        # 检查customers表是否已有teacher_id字段
        print("2. 检查customers表的teacher_id字段...")
        with db.engine.connect() as conn:
            cursor = conn.execute(db.text("PRAGMA table_info(customers)"))
            columns = [row[1] for row in cursor.fetchall()]

            if 'teacher_id' not in columns:
                print("   添加teacher_id字段...")
                conn.execute(db.text("""
                    ALTER TABLE customers ADD COLUMN teacher_id INTEGER REFERENCES teachers(id)
                """))
                conn.commit()
                print("   ✓ teacher_id字段添加成功")
            else:
                print("   ✓ teacher_id字段已存在")

        print("\n数据库迁移完成！")
        print("\n提示：")
        print("- teachers表已创建，包含老师的详细信息")
        print("- customers表已添加teacher_id字段，用于关联老师")
        print("- teacher_user_id字段保留用于向后兼容")

if __name__ == '__main__':
    migrate()

