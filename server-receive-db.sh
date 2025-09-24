#!/bin/bash

# 服务器端数据库接收脚本
# 在云端服务器上执行此脚本

set -e

echo "🚀 服务器端数据库迁移接收..."

# 检查上传的数据库文件
if [ ! -f "database_upload.tar.gz" ]; then
    echo "❌ 未找到数据库上传文件 database_upload.tar.gz"
    echo "请先上传数据库文件到当前目录"
    exit 1
fi

echo "✅ 找到数据库上传文件"

# 停止现有容器
echo "🛑 停止现有容器..."
docker stop $(docker ps -q --filter "name=crm") 2>/dev/null || true
docker rm $(docker ps -aq --filter "name=crm") 2>/dev/null || true

# 备份现有数据库（如果存在）
echo "💾 备份现有数据库..."
if [ -f "/var/lib/crm/instance/edu_crm.db" ]; then
    mkdir -p /var/lib/crm/backups
    cp /var/lib/crm/instance/edu_crm.db "/var/lib/crm/backups/edu_crm_server_backup_$(date +%Y%m%d_%H%M%S).db"
    echo "✅ 现有数据库已备份"
fi

# 创建目录
echo "📁 创建数据库目录..."
mkdir -p /var/lib/crm/instance
mkdir -p /var/lib/crm/logs
mkdir -p /var/lib/crm/backups

# 解压新数据库
echo "📦 解压新数据库..."
cd /var/lib/crm/instance
tar -xzf ~/database_upload.tar.gz

# 设置权限
echo "🔧 设置权限..."
chmod 666 edu_crm.db
chown -R 1000:1000 /var/lib/crm

# 验证数据库
echo "🔍 验证数据库..."
sqlite3 edu_crm.db "
.mode column
.headers on
SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'leads', COUNT(*) FROM leads
UNION ALL
SELECT 'customers', COUNT(*) FROM customers
UNION ALL
SELECT 'consultations', COUNT(*) FROM consultations;
"

# 检查Docker镜像
echo "🐳 检查Docker镜像..."
if ! docker images | grep crm-app > /dev/null; then
    echo "❌ 未找到crm-app镜像，请先构建镜像"
    echo "请执行: docker build -t crm-app:latest ."
    exit 1
fi

# 启动新容器
echo "🚀 启动新容器..."
docker run -d \
    --name crm-app \
    --restart unless-stopped \
    -p 80:80 \
    -e FLASK_ENV=production \
    -e DATABASE_URL=sqlite:///instance/edu_crm.db \
    -e SECRET_KEY=crm-production-secret-$(date +%s) \
    -v /var/lib/crm/instance:/app/instance \
    -v /var/lib/crm/logs:/app/logs \
    crm-app:latest

# 等待启动
echo "⏳ 等待应用启动..."
sleep 30

# 检查状态
echo "📊 检查容器状态..."
docker ps | grep crm-app

echo "📝 查看启动日志..."
docker logs crm-app | tail -15

# 测试访问
echo "🧪 测试应用访问..."
echo "健康检查:"
curl -s http://localhost/health | python3 -m json.tool 2>/dev/null || curl -I http://localhost/health

echo ""
echo "登录页面:"
curl -I http://localhost/auth/login

echo ""
echo "🎉 数据库迁移完成！"
echo "================================"
echo "📊 应用信息:"
echo "  容器名称: crm-app"
echo "  访问地址: http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_SERVER_IP')"
echo "  数据库位置: /var/lib/crm/instance/edu_crm.db"
echo ""
echo "🔧 管理命令:"
echo "  查看日志: docker logs -f crm-app"
echo "  重启应用: docker restart crm-app"
echo "  进入容器: docker exec -it crm-app bash"
echo "  停止应用: docker stop crm-app"
echo ""
echo "💾 备份位置:"
echo "  服务器备份: /var/lib/crm/backups/"
echo "================================"
