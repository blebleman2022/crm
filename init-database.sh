#!/bin/bash

# 数据库初始化脚本
set -e

echo "🔧 检查数据库状态..."

# 检查数据库文件是否存在
if [ -f "/app/instance/edu_crm.db" ] && [ -s "/app/instance/edu_crm.db" ]; then
    echo "✅ 发现数据库文件，检查内容..."

    # 检查数据库内容
    python -c "
from run import app
from models import db, User, Lead, Customer

try:
    with app.app_context():
        user_count = User.query.count()
        lead_count = Lead.query.count() if hasattr(db.Model, 'Lead') else 0
        customer_count = Customer.query.count() if hasattr(db.Model, 'Customer') else 0

        print(f'📊 数据库统计:')
        print(f'   用户数量: {user_count}')
        print(f'   线索数量: {lead_count}')
        print(f'   客户数量: {customer_count}')

        if user_count > 0:
            print(f'👥 用户列表:')
            users = User.query.limit(5).all()
            for user in users:
                print(f'   - {user.username} ({user.phone}) - {user.role}')

        print('✅ 数据库内容验证完成')
except Exception as e:
    print(f'❌ 数据库验证失败: {e}')
    print('将重新初始化数据库...')
    exit(1)
"

    if [ $? -eq 0 ]; then
        echo "✅ 数据库验证成功，使用现有数据"
    else
        echo "❌ 数据库验证失败，重新初始化..."
        rm -f /app/instance/edu_crm.db
    fi
fi

# 如果数据库文件不存在或为空，创建新数据库
if [ ! -f "/app/instance/edu_crm.db" ] || [ ! -s "/app/instance/edu_crm.db" ]; then
    echo "📄 数据库文件不存在或为空，创建新数据库..."
    
    # 确保目录存在
    mkdir -p /app/instance
    
    # 初始化数据库
    python -c "
from run import app
from models import db, User
import os

print('初始化数据库表...')
with app.app_context():
    # 创建所有表
    db.create_all()
    print('✅ 数据库表创建完成')
    
    # 检查是否有用户
    user_count = User.query.count()
    print(f'当前用户数量: {user_count}')
    
    # 如果没有用户，创建默认管理员
    if user_count == 0:
        admin_user = User(
            username='系统管理员',
            phone='13800138000',
            role='admin',
            status=True
        )
        db.session.add(admin_user)
        db.session.commit()
        print('✅ 创建默认管理员用户成功')
        print('   手机号: 13800138000')
        print('   角色: admin')
    
    print('✅ 新数据库初始化完成')
"
fi

echo "🚀 启动应用..."
exec "$@"
