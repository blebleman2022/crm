#!/usr/bin/env python3
"""
数据库迁移脚本：为customers表添加thesis_name字段

使用方法：
python add_thesis_name_to_customers.py
"""

import sqlite3
import os

def add_thesis_name_column():
    """为customers表添加thesis_name字段"""
    
    # 数据库文件路径
    db_path = 'instance/edu_crm.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(customers)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'thesis_name' in columns:
            print("✅ thesis_name 字段已存在，无需添加")
            conn.close()
            return True
        
        # 添加字段
        print("📝 正在添加 thesis_name 字段...")
        cursor.execute("""
            ALTER TABLE customers 
            ADD COLUMN thesis_name VARCHAR(200)
        """)
        
        conn.commit()
        print("✅ thesis_name 字段添加成功！")
        
        # 验证字段已添加
        cursor.execute("PRAGMA table_info(customers)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'thesis_name' in columns:
            print("✅ 验证成功：thesis_name 字段已存在于 customers 表中")
        else:
            print("❌ 验证失败：thesis_name 字段未找到")
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败: {str(e)}")
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("数据库迁移：添加课题名称字段")
    print("=" * 50)
    
    success = add_thesis_name_column()
    
    if success:
        print("\n✅ 迁移完成！")
    else:
        print("\n❌ 迁移失败，请检查错误信息")

