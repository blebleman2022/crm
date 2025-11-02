#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
添加客户图片表的数据库迁移脚本
- course_record_images: 课程记录图片表
- award_certificate_images: 获奖证书图片表
"""

import sqlite3
import os

def migrate_add_customer_image_tables():
    """添加客户图片表"""
    db_path = 'instance/edu_crm.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查course_record_images表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='course_record_images'")
        if cursor.fetchone():
            print("✅ course_record_images表已存在，跳过创建")
        else:
            # 创建课程记录图片表
            cursor.execute("""
                CREATE TABLE course_record_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    image_path VARCHAR(500) NOT NULL,
                    description VARCHAR(200),
                    file_size INTEGER,
                    file_name VARCHAR(200),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            """)
            print("✅ 成功创建course_record_images表")
        
        # 检查award_certificate_images表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='award_certificate_images'")
        if cursor.fetchone():
            print("✅ award_certificate_images表已存在，跳过创建")
        else:
            # 创建获奖证书图片表
            cursor.execute("""
                CREATE TABLE award_certificate_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    image_path VARCHAR(500) NOT NULL,
                    description VARCHAR(200),
                    file_size INTEGER,
                    file_name VARCHAR(200),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            """)
            print("✅ 成功创建award_certificate_images表")
        
        conn.commit()
        print("✅ 客户图片表迁移完成")
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    print("开始添加客户图片表...")
    success = migrate_add_customer_image_tables()
    if success:
        print("✅ 迁移成功完成")
    else:
        print("❌ 迁移失败")

