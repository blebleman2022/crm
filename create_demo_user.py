#!/usr/bin/env python3
"""
创建展示账号
手机号：16666666666
角色：demo
登录方式：免密登录（只需输入手机号）
"""

from run import create_app
from models import db, User

def create_demo_user():
    """创建展示账号"""
    app = create_app()

    with app.app_context():
        # 检查是否已存在
        existing_user = User.query.filter_by(phone='16666666666').first()

        if existing_user:
            print(f"展示账号已存在: {existing_user.username} (ID: {existing_user.id})")
            print(f"角色: {existing_user.role}")
            print(f"状态: {'启用' if existing_user.status else '禁用'}")

            # 更新为demo角色
            if existing_user.role != 'demo':
                existing_user.role = 'demo'
                existing_user.username = '展示账号'
                existing_user.status = True
                db.session.commit()
                print("✅ 已更新为展示账号角色")
            else:
                print("✅ 角色已经是demo，无需更新")
        else:
            # 创建新用户（系统使用免密登录，不需要密码）
            demo_user = User(
                username='展示账号',
                phone='16666666666',
                role='demo',
                status=True
            )

            db.session.add(demo_user)
            db.session.commit()

            print("✅ 展示账号创建成功！")
            print(f"用户名: {demo_user.username}")
            print(f"手机号: {demo_user.phone}")
            print(f"角色: {demo_user.role}")
            print(f"登录方式: 免密登录（输入手机号即可）")
            print(f"ID: {demo_user.id}")
            print("\n📱 登录步骤：")
            print("1. 访问登录页面")
            print("2. 输入手机号：16666666666")
            print("3. 点击登录")

if __name__ == '__main__':
    create_demo_user()

