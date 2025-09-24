#!/bin/bash

# 修复数据库连接问题
set -e

echo "🔧 诊断和修复数据库连接问题..."

# 停止当前容器
echo "停止当前容器..."
docker stop o5b578f64f6 2>/dev/null || true
docker rm o5b578f64f6 2>/dev/null || true

# 诊断容器内部问题
echo "创建诊断容器..."
docker run --rm -it --name crm-debug \
    -e FLASK_ENV=production \
    -e DATABASE_URL=sqlite:///instance/edu_crm.db \
    -e SECRET_KEY=debug-secret-key \
    -v /var/lib/crm/instance:/app/instance \
    -v /var/lib/crm/logs:/app/logs \
    crm-app:latest bash -c "
echo '=== 诊断开始 ==='
echo '当前用户:' \$(whoami)
echo '当前目录:' \$(pwd)
echo '用户ID:' \$(id)

echo ''
echo '=== 检查目录权限 ==='
ls -la /app/
ls -la /app/instance/ 2>/dev/null || echo '❌ instance目录不存在或无权限'
ls -la /app/logs/ 2>/dev/null || echo '❌ logs目录不存在或无权限'

echo ''
echo '=== 检查环境变量 ==='
echo 'FLASK_ENV:' \$FLASK_ENV
echo 'DATABASE_URL:' \$DATABASE_URL
echo 'SECRET_KEY:' \$SECRET_KEY

echo ''
echo '=== 测试数据库连接 ==='
python -c \"
import os
import sys
print('Python路径:', sys.path)
print('当前工作目录:', os.getcwd())

try:
    # 测试导入
    print('导入Flask...')
    from flask import Flask
    print('✅ Flask导入成功')
    
    print('导入SQLAlchemy...')
    from flask_sqlalchemy import SQLAlchemy
    print('✅ SQLAlchemy导入成功')
    
    print('创建Flask应用...')
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///instance/edu_crm.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    print('✅ Flask应用创建成功')
    
    print('初始化数据库...')
    db = SQLAlchemy()
    db.init_app(app)
    print('✅ 数据库初始化成功')
    
    print('测试数据库连接...')
    with app.app_context():
        # 尝试创建表
        db.create_all()
        print('✅ 数据库表创建成功')
        
        # 尝试执行查询
        result = db.session.execute('SELECT 1').scalar()
        print(f'✅ 数据库查询成功，结果: {result}')
        
except Exception as e:
    print(f'❌ 错误: {e}')
    import traceback
    traceback.print_exc()
\"

echo ''
echo '=== 尝试手动创建数据库 ==='
mkdir -p /app/instance
touch /app/instance/edu_crm.db
chmod 666 /app/instance/edu_crm.db
ls -la /app/instance/

echo ''
echo '=== 测试应用启动 ==='
timeout 10 python -c \"
from run import app
print('应用对象:', app)
print('应用配置:', app.config.get('SQLALCHEMY_DATABASE_URI'))

# 测试健康检查
with app.test_client() as client:
    response = client.get('/health')
    print(f'健康检查状态码: {response.status_code}')
    print(f'健康检查响应: {response.get_data(as_text=True)}')
\" || echo '应用启动超时或失败'

echo '=== 诊断结束 ==='
"

echo ""
echo "🚀 重新部署修复版本..."

# 创建修复的启动脚本
cat > start_fixed_db.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 启动EduConnect CRM应用 (数据库修复版)..."

# 确保目录存在且权限正确
echo "📁 创建并设置目录权限..."
mkdir -p /app/instance /app/logs
chmod 755 /app/instance /app/logs

# 如果数据库文件不存在，创建它
if [ ! -f "/app/instance/edu_crm.db" ]; then
    echo "📄 创建数据库文件..."
    touch /app/instance/edu_crm.db
    chmod 666 /app/instance/edu_crm.db
fi

echo "🔧 初始化数据库..."
python -c "
import os
from run import app
from models import db, User

print('应用配置:', app.config.get('SQLALCHEMY_DATABASE_URI'))

with app.app_context():
    try:
        # 创建所有表
        db.create_all()
        print('✅ 数据库表创建成功')
        
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
        
        # 测试数据库连接
        result = db.session.execute('SELECT 1').scalar()
        print(f'✅ 数据库连接测试成功: {result}')
        
    except Exception as e:
        print(f'❌ 数据库初始化失败: {e}')
        import traceback
        traceback.print_exc()
        exit(1)
"

echo "🌐 启动Web服务器..."
if [ "$FLASK_ENV" = "development" ]; then
    echo "🔧 开发模式启动..."
    python run.py
else
    echo "🚀 生产模式启动..."
    gunicorn -c gunicorn.conf.py run:app
fi
EOF

chmod +x start_fixed_db.sh

# 重新构建镜像
echo "重新构建镜像..."
docker build -t crm-app-fixed:latest . --build-arg INSTALL_DEV=false

# 启动修复版容器
echo "启动修复版容器..."
docker run -d \
    --name crm-app-fixed \
    --restart unless-stopped \
    -p 80:80 \
    -e FLASK_ENV=production \
    -e DATABASE_URL=sqlite:///instance/edu_crm.db \
    -e SECRET_KEY=crm-production-secret-$(date +%s) \
    -v /var/lib/crm/instance:/app/instance \
    -v /var/lib/crm/logs:/app/logs \
    crm-app-fixed:latest ./start_fixed_db.sh

echo "⏳ 等待应用启动..."
sleep 30

echo "📊 检查容器状态..."
docker ps | grep crm-app-fixed

echo "📝 查看启动日志..."
docker logs crm-app-fixed | tail -20

echo "🧪 测试健康检查..."
curl -v http://localhost/health || echo "健康检查失败"

echo "🧪 测试登录页面..."
curl -I http://localhost/auth/login || echo "登录页面失败"

echo "🎉 修复完成！"
echo "🌐 访问地址: http://47.100.238.50"
