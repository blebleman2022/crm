#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加客户付款信息表

功能说明：
- 创建 customer_payments 表，用于记录客户的付款进度
- 每个客户最多3笔付款记录
- 关联到Customer表和班主任User表
- 支持自动计算已付款总额和剩余付款

执行方式：
    python migrations/add_customer_payments_table.py
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run import create_app
from models import db
from sqlalchemy import text

def migrate():
    """执行数据库迁移"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("开始执行客户付款信息表迁移...")
        print("=" * 60)
        
        # 检查表是否已存在
        result = db.session.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='customer_payments'"
        ))
        table_exists = result.fetchone() is not None
        
        if table_exists:
            print("⚠️  customer_payments 表已存在，跳过创建")
            
            # 检查字段是否完整
            result = db.session.execute(text("PRAGMA table_info(customer_payments)"))
            columns = {row[1] for row in result.fetchall()}
            
            required_columns = {
                'id', 'customer_id', 'teacher_user_id', 'total_amount',
                'first_payment', 'first_payment_date',
                'second_payment', 'second_payment_date',
                'third_payment', 'third_payment_date',
                'created_at', 'updated_at'
            }
            
            missing_columns = required_columns - columns
            if missing_columns:
                print(f"⚠️  缺少字段: {missing_columns}")
                print("❌ 表结构不完整，请手动检查")
                return False
            else:
                print("✅ 表结构完整")
                return True
        
        # 创建 customer_payments 表
        print("\n📝 创建 customer_payments 表...")
        
        create_table_sql = """
        CREATE TABLE customer_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            teacher_user_id INTEGER NOT NULL,
            total_amount DECIMAL(10,2),
            first_payment DECIMAL(10,2),
            first_payment_date DATE,
            second_payment DECIMAL(10,2),
            second_payment_date DATE,
            third_payment DECIMAL(10,2),
            third_payment_date DATE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
            FOREIGN KEY (teacher_user_id) REFERENCES users(id)
        )
        """
        
        try:
            db.session.execute(text(create_table_sql))
            db.session.commit()
            print("✅ customer_payments 表创建成功")
        except Exception as e:
            db.session.rollback()
            print(f"❌ 创建表失败: {e}")
            return False
        
        # 创建索引以提高查询性能
        print("\n📝 创建索引...")
        
        indexes = [
            "CREATE INDEX idx_customer_payments_customer_id ON customer_payments(customer_id)",
            "CREATE INDEX idx_customer_payments_teacher_user_id ON customer_payments(teacher_user_id)"
        ]
        
        for index_sql in indexes:
            try:
                db.session.execute(text(index_sql))
                db.session.commit()
                print(f"✅ 索引创建成功: {index_sql.split('ON')[0].split('INDEX')[1].strip()}")
            except Exception as e:
                db.session.rollback()
                print(f"⚠️  索引创建失败（可能已存在）: {e}")
        
        # 验证表结构
        print("\n🔍 验证表结构...")
        result = db.session.execute(text("PRAGMA table_info(customer_payments)"))
        columns = result.fetchall()
        
        print("\n表字段列表:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # 统计现有客户数量
        result = db.session.execute(text("SELECT COUNT(*) FROM customers"))
        customer_count = result.fetchone()[0]
        print(f"\n📊 当前系统中有 {customer_count} 个客户")
        print("💡 提示：班主任可以在付款管理页面为客户添加付款信息")
        
        print("\n" + "=" * 60)
        print("✅ 迁移完成！customer_payments 表已创建")
        print("=" * 60)
        
        return True

if __name__ == '__main__':
    try:
        success = migrate()
        if success:
            print("\n✅ 数据库迁移成功完成！")
            sys.exit(0)
        else:
            print("\n❌ 数据库迁移失败！")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ 迁移过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

