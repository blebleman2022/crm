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

echo "🔧 初始化数据库..."
# 初始化数据库（如果需要）
python -c "
from run import app
with app.app_context():
    from models import db
    db.create_all()
    print('数据库初始化完成')
"

echo "🌐 启动Web服务器..."
# 启动应用
if [ "$FLASK_ENV" = "development" ]; then
    echo "🔧 开发模式启动..."
    python run.py
else
    echo "🚀 生产模式启动..."
    gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 --access-logfile - --error-logfile - run:app
fi
