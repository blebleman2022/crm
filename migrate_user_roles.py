#!/usr/bin/env python3
"""
用户角色迁移脚本
将现有的 'sales' 角色用户迁移为新的角色系统
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db, User
from run import app

def migrate_user_roles():
    """迁移用户角色"""
    with app.app_context():
        try:
            # 查找所有 'sales' 角色的用户
            sales_users = User.query.filter_by(role='sales').all()
            
            print(f"找到 {len(sales_users)} 个 'sales' 角色用户需要迁移")
            
            # 迁移策略：
            # 1. 张三、钱七 -> sales_manager (销售管理)
            # 2. 李四 -> salesperson (销售)
            # 3. 其他用户根据用户名判断或默认为 salesperson
            
            for user in sales_users:
                if user.username in ['张三', '钱七']:
                    new_role = 'sales_manager'
                    print(f"将用户 {user.username} (ID: {user.id}) 从 'sales' 迁移为 'sales_manager'")
                else:
                    new_role = 'salesperson'
                    print(f"将用户 {user.username} (ID: {user.id}) 从 'sales' 迁移为 'salesperson'")
                
                user.role = new_role
            
            # 提交更改
            db.session.commit()
            print("用户角色迁移完成！")
            
            # 验证迁移结果
            print("\n迁移后的用户角色分布：")
            for role in ['admin', 'sales_manager', 'salesperson', 'teacher']:
                count = User.query.filter_by(role=role).count()
                print(f"  {role}: {count} 个用户")
            
            # 检查是否还有旧的 'sales' 角色用户
            old_sales_count = User.query.filter_by(role='sales').count()
            if old_sales_count > 0:
                print(f"\n⚠️  警告：仍有 {old_sales_count} 个用户使用旧的 'sales' 角色")
            else:
                print("\n✅ 所有用户角色迁移成功，没有遗留的 'sales' 角色用户")
                
        except Exception as e:
            db.session.rollback()
            print(f"迁移失败：{str(e)}")
            return False
        
        return True

if __name__ == '__main__':
    print("开始用户角色迁移...")
    success = migrate_user_roles()
    if success:
        print("迁移完成！")
    else:
        print("迁移失败！")
        sys.exit(1)
