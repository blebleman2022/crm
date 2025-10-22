"""
数据库迁移脚本：添加老师图片表
创建时间：2025-10-22
说明：为老师信息添加相关图片功能，支持上传多张图片并添加描述
"""

import sqlite3
import os
from datetime import datetime

def migrate():
    """执行迁移"""
    # 获取数据库路径
    db_path = os.path.join('instance', 'edu_crm.db')
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否已存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='teacher_images'
        """)
        
        if cursor.fetchone():
            print("✅ teacher_images表已存在，跳过创建")
            conn.close()
            return True
        
        # 创建teacher_images表
        cursor.execute("""
            CREATE TABLE teacher_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                image_path VARCHAR(500) NOT NULL,
                description VARCHAR(200),
                file_size INTEGER,
                file_name VARCHAR(200),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id)
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX idx_teacher_images_teacher_id 
            ON teacher_images(teacher_id)
        """)
        
        conn.commit()
        print("✅ teacher_images表创建成功")
        print("✅ 索引创建成功")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def rollback():
    """回滚迁移"""
    db_path = os.path.join('instance', 'edu_crm.db')
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 删除表
        cursor.execute("DROP TABLE IF EXISTS teacher_images")
        
        conn.commit()
        print("✅ teacher_images表已删除")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 回滚失败: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("开始执行数据库迁移：添加老师图片表")
    print("=" * 50)
    
    if migrate():
        print("\n✅ 迁移完成！")
    else:
        print("\n❌ 迁移失败！")

