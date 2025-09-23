#!/bin/bash

# 启动脚本 - 用于Docker容器
set -e

echo "🚀 启动EduConnect CRM应用..."

# 检查数据库目录
if [ ! -d "instance" ]; then
    echo "📁 创建instance目录..."
    mkdir -p instance
fi

# 检查日志目录
if [ ! -d "logs" ]; then
    echo "📁 创建logs目录..."
    mkdir -p logs
fi

# 设置权限
chmod 755 instance logs

echo "🔧 测试应用导入..."
# 测试应用导入
python -c "
import sys
print('🐍 Python版本:', sys.version)
print('📁 当前目录:', sys.path[0])
print('📦 尝试导入run模块...')
try:
    import run
    print('✅ run模块导入成功')
    print('✅ app对象:', run.app)
    print('✅ app类型:', type(run.app))
    print('✅ app名称:', run.app.name)

    # 初始化数据库
    with run.app.app_context():
        from models import db
        db.create_all()
        print('✅ 数据库初始化完成')
except Exception as e:
    print('❌ 导入失败:', e)
    import traceback
    traceback.print_exc()
    exit(1)
"

echo "🌐 启动Web服务器..."
# 启动应用
if [ "$FLASK_ENV" = "development" ]; then
    echo "🔧 开发模式启动..."
    python run.py
else
    echo "🚀 生产模式启动..."
    gunicorn --bind 0.0.0.0:80 --workers 2 --timeout 120 --access-logfile - --error-logfile - run:app
fi
