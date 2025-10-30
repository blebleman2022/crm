#!/usr/bin/env python3
"""
在服务器上创建 customer_competitions 表的脚本
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import CustomerCompetition

def create_table():
    """创建 customer_competitions 表"""
    with app.app_context():
        try:
            # 创建所有表（只会创建不存在的表）
            db.create_all()
            print("✅ customer_competitions 表创建成功！")
            
            # 验证表是否存在
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'customer_competitions' in tables:
                print("✅ 验证成功：customer_competitions 表已存在")
                
                # 显示表结构
                columns = inspector.get_columns('customer_competitions')
                print("\n📋 表结构：")
                for col in columns:
                    print(f"  - {col['name']}: {col['type']}")
            else:
                print("❌ 错误：customer_competitions 表未创建")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ 创建表失败：{e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = create_table()
    sys.exit(0 if success else 1)

