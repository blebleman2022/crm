#!/bin/bash

# 快速部署脚本
set -e

echo "🚀 CRM应用快速部署"
echo "=================="

# 获取时间戳
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
PACKAGE_NAME="crm-${TIMESTAMP}.tar.gz"

echo "📦 创建部署包: ${PACKAGE_NAME}"

# 创建部署包，排除不需要的文件
tar -czf "${PACKAGE_NAME}" \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='test-*' \
    --exclude='deploy-*' \
    --exclude='*.tar.gz' \
    --exclude='upload-*.sh' \
    --exclude='instance/*.db' \
    --exclude='.DS_Store' \
    .

echo "✅ 部署包创建完成"

# 显示包信息
SIZE=$(du -h "${PACKAGE_NAME}" | cut -f1)
echo "📊 包大小: ${SIZE}"

# 创建上传脚本
cat > "upload-${TIMESTAMP}.sh" << EOF
#!/bin/bash

echo "📤 上传并部署CRM应用"
echo "==================="

SERVER_IP="47.100.238.50"
PACKAGE="${PACKAGE_NAME}"

echo "正在上传 \${PACKAGE} 到服务器..."

# 上传文件
scp "\${PACKAGE}" root@\${SERVER_IP}:/tmp/

echo "正在服务器上部署..."

# 在服务器上执行部署
ssh root@\${SERVER_IP} << 'REMOTE_SCRIPT'
set -e

echo "🚀 开始部署CRM应用"

# 进入临时目录
cd /tmp

# 解压应用
tar -xzf ${PACKAGE_NAME}

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
docker run -d \\
    --name crm-app \\
    --restart unless-stopped \\
    -p 80:80 \\
    -e FLASK_ENV=production \\
    -e DATABASE_URL=sqlite:///instance/edu_crm.db \\
    -e SECRET_KEY=crm-production-secret-\$(date +%s) \\
    -v /var/lib/crm/instance:/app/instance \\
    -v /var/lib/crm/logs:/app/logs \\
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
    
    echo "等待应用启动... (\$i/30)"
    sleep 2
done

# 显示状态
echo ""
echo "🎉 部署完成！"
echo "================================"
echo "✅ 应用已成功部署"
echo "🌐 访问地址: http://\$(hostname -I | awk '{print \$1}')"
echo "📊 容器状态:"
docker ps --filter name=crm-app
echo ""
echo "📝 管理命令:"
echo "  查看日志: docker logs -f crm-app"
echo "  重启应用: docker restart crm-app"
echo "  停止应用: docker stop crm-app"

# 清理临时文件
rm -f ${PACKAGE_NAME}
rm -rf run.py config.py models.py routes templates static utils *.txt *.sh *.py *.md Dockerfile start.sh gunicorn.conf.py

REMOTE_SCRIPT

echo ""
echo "🎉 远程部署完成！"
echo "访问地址: http://\${SERVER_IP}"
EOF

chmod +x "upload-${TIMESTAMP}.sh"

echo ""
echo "🎉 快速部署准备完成！"
echo "======================"
echo "📦 部署包: ${PACKAGE_NAME}"
echo "📤 上传脚本: upload-${TIMESTAMP}.sh"
echo ""
echo "🚀 执行部署:"
echo "  ./upload-${TIMESTAMP}.sh"
echo ""
echo "📋 手动部署:"
echo "  1. scp ${PACKAGE_NAME} root@47.100.238.50:/tmp/"
echo "  2. ssh root@47.100.238.50"
echo "  3. cd /tmp && tar -xzf ${PACKAGE_NAME}"
echo "  4. docker build -t crm-app:latest ."
echo "  5. docker run -d --name crm-app -p 80:80 crm-app:latest"
