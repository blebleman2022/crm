#!/bin/bash

# 简化版数据库迁移脚本
set -e

echo "🚀 简化版数据库迁移..."

# 检查本地数据库
if [ ! -f "./instance/edu_crm.db" ]; then
    echo "❌ 本地数据库文件不存在"
    exit 1
fi

echo "✅ 本地数据库文件存在"
ls -la ./instance/edu_crm.db

# 创建备份
echo "📦 创建本地备份..."
mkdir -p ./database_backups
cp ./instance/edu_crm.db "./database_backups/edu_crm_backup_$(date +%Y%m%d_%H%M%S).db"
echo "✅ 备份创建完成"

# 创建上传包
echo "📦 创建上传包..."
tar -czf database_upload.tar.gz -C instance edu_crm.db

echo "📊 数据库信息:"
sqlite3 ./instance/edu_crm.db "
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

echo ""
echo "🎯 下一步操作指南:"
echo "================================"
echo "1. 将 database_upload.tar.gz 上传到服务器"
echo "2. 在服务器上执行以下命令:"
echo ""
echo "# 停止容器"
echo "docker stop \$(docker ps -q --filter ancestor=crm-app:latest) 2>/dev/null || true"
echo "docker rm \$(docker ps -aq --filter ancestor=crm-app:latest) 2>/dev/null || true"
echo ""
echo "# 创建目录并解压数据库"
echo "mkdir -p /var/lib/crm/instance"
echo "cd /var/lib/crm/instance"
echo "tar -xzf ~/database_upload.tar.gz"
echo "chmod 666 edu_crm.db"
echo "chown -R 1000:1000 /var/lib/crm"
echo ""
echo "# 重新启动容器"
echo "docker run -d \\"
echo "    --name crm-app \\"
echo "    --restart unless-stopped \\"
echo "    -p 80:80 \\"
echo "    -e FLASK_ENV=production \\"
echo "    -e DATABASE_URL=sqlite:///instance/edu_crm.db \\"
echo "    -e SECRET_KEY=crm-production-secret-\$(date +%s) \\"
echo "    -v /var/lib/crm/instance:/app/instance \\"
echo "    -v /var/lib/crm/logs:/app/logs \\"
echo "    crm-app:latest"
echo ""
echo "# 检查状态"
echo "docker ps"
echo "docker logs crm-app"
echo "curl http://localhost/health"
echo ""
echo "================================"
echo "✅ 上传包已准备完成: database_upload.tar.gz"
