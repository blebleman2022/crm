#!/bin/bash

# 修复版启动脚本
set -e

echo "🚀 启动EduConnect CRM应用 (修复版)..."

# 检查目录
mkdir -p instance logs
chmod 755 instance logs

echo "🔧 验证应用配置..."
python -c "
import sys
print('Python版本:', sys.version)
print('当前目录:', sys.path[0])

# 测试导入
try:
    from run import app
    print('✅ 应用导入成功')
    print('✅ 应用对象:', app)
    print('✅ 应用名称:', app.name)
    
    # 初始化数据库
    with app.app_context():
        from models import db, User
        db.create_all()
        
        # 检查是否有用户
        user_count = User.query.count()
        print(f'✅ 数据库用户数量: {user_count}')
        
        # 如果没有用户，创建默认管理员
        if user_count == 0:
            admin_user = User(
                name='系统管理员',
                phone='13800138000',
                role='admin',
                is_active=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print('✅ 创建默认管理员用户')
    
    # 列出路由
    print('\\n=== 注册的路由 ===')
    for rule in app.url_map.iter_rules():
        print(f'  {rule.rule} -> {rule.endpoint}')
        
except Exception as e:
    print('❌ 应用验证失败:', e)
    import traceback
    traceback.print_exc()
    exit(1)
"

echo "🌐 启动Web服务器..."

# 使用更详细的gunicorn配置
if [ "$FLASK_ENV" = "development" ]; then
    echo "🔧 开发模式启动..."
    export FLASK_APP=run:app
    flask run --host=0.0.0.0 --port=80
else
    echo "🚀 生产模式启动..."
    # 使用更详细的配置
    gunicorn \
        --bind 0.0.0.0:80 \
        --workers 2 \
        --worker-class sync \
        --timeout 120 \
        --keep-alive 2 \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --access-logfile - \
        --error-logfile - \
        --log-level info \
        --capture-output \
        run:app
fi
