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

    # 检查数据库连接（不重复初始化）
    with run.app.app_context():
        from models import db
        try:
            db.engine.execute('SELECT 1')
            print('✅ 数据库连接正常')
        except Exception as e:
            print(f'⚠️ 数据库连接问题: {e}')
            print('数据库将在应用启动时自动处理')
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
    # 使用gunicorn配置文件启动
    gunicorn -c gunicorn.conf.py run:app
fi
