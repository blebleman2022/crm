#!/usr/bin/env python3
"""
检查服务器数据库状态
用于诊断500错误
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, SystemConfig, CustomerPayment
from run import create_app

def check_database():
    """检查数据库表是否存在"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("检查数据库表")
        print("=" * 60)
        
        # 检查 system_config 表
        try:
            count = SystemConfig.query.count()
            print(f"✅ system_config 表存在，记录数: {count}")
            
            # 查看锁定配置
            lock_config = SystemConfig.query.filter_by(config_key='payment_lock_month').first()
            if lock_config:
                print(f"   锁定月份: {lock_config.config_value}")
            else:
                print("   未设置锁定月份")
        except Exception as e:
            print(f"❌ system_config 表不存在或有错误: {e}")
        
        # 检查 customer_payments 表
        try:
            count = CustomerPayment.query.count()
            print(f"✅ customer_payments 表存在，记录数: {count}")
        except Exception as e:
            print(f"❌ customer_payments 表不存在或有错误: {e}")
        
        print("\n" + "=" * 60)
        print("检查完成")
        print("=" * 60)
        
        # 如果表不存在，提示执行迁移
        print("\n如果表不存在，请执行以下命令：")
        print("  python migrate_database.py")

if __name__ == '__main__':
    check_database()

