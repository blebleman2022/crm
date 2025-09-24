#!/bin/bash

echo "📤 上传并部署CRM应用"
echo "==================="

SERVER_IP="47.100.238.50"
PACKAGE="crm-20250923-193056.tar.gz"

echo "正在上传 ${PACKAGE} 到服务器..."

# 上传文件
scp "${PACKAGE}" root@${SERVER_IP}:/tmp/

echo "正在服务器上部署..."

# 在服务器上执行部署
ssh root@${SERVER_IP} << 'REMOTE_SCRIPT'
set -e

echo "🚀 开始部署CRM应用"

# 进入临时目录
cd /tmp

# 解压应用
tar -xzf crm-20250923-193056.tar.gz

# 停止旧容器
echo "停止旧容器..."
docker stop crm-app 2>/dev/null || true
docker rm crm-app 2>/dev/null || true

# 构建新镜像
echo "构建Docker镜像..."
docker build -t crm-app:latest .

# 创建数据目录
mkdir -p /var/lib/crm/instance
mkdir -p /var/lib/crm/logs

# 启动新容器
echo "启动新容器..."
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
echo "等待应用启动..."
sleep 10

# 健康检查
echo "执行健康检查..."
for i in {1..30}; do
    if curl -f http://localhost/health > /dev/null 2>&1; then
        echo "✅ 应用健康检查通过"
        break
    elif curl -f http://localhost/auth/login > /dev/null 2>&1; then
        echo "✅ 应用启动成功（登录页面可访问）"
        break
    fi
    
    echo "等待应用启动... ($i/30)"
    sleep 2
done

# 显示状态
echo ""
echo "🎉 部署完成！"
echo "================================"
echo "✅ 应用已成功部署"
echo "🌐 访问地址: http://$(hostname -I | awk '{print $1}')"
echo "📊 容器状态:"
docker ps --filter name=crm-app
echo ""
echo "📝 管理命令:"
echo "  查看日志: docker logs -f crm-app"
echo "  重启应用: docker restart crm-app"
echo "  停止应用: docker stop crm-app"

# 清理临时文件
rm -f crm-20250923-193056.tar.gz
rm -rf run.py config.py models.py routes templates static utils *.txt *.sh *.py *.md Dockerfile start.sh gunicorn.conf.py

REMOTE_SCRIPT

echo ""
echo "🎉 远程部署完成！"
echo "访问地址: http://${SERVER_IP}"
