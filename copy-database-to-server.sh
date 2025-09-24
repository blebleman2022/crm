#!/bin/bash

# 将本地数据库文件复制到服务器的脚本
set -e

# 配置
SERVER_IP="47.100.238.50"
SERVER_USER="root"
LOCAL_DB_PATH="./instance/edu_crm.db"
REMOTE_PROJECT_DIR="/root/crm"

echo "🚀 复制本地数据库文件到服务器..."

# 检查本地数据库文件
if [ ! -f "$LOCAL_DB_PATH" ]; then
    echo "❌ 本地数据库文件不存在: $LOCAL_DB_PATH"
    exit 1
fi

echo "✅ 找到本地数据库文件"
ls -la "$LOCAL_DB_PATH"

# 显示数据库内容
echo "📊 本地数据库内容:"
sqlite3 "$LOCAL_DB_PATH" "
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

# 复制到服务器
echo "📤 上传数据库文件到服务器..."
scp "$LOCAL_DB_PATH" "$SERVER_USER@$SERVER_IP:$REMOTE_PROJECT_DIR/instance/"

# 在服务器上设置权限
ssh "$SERVER_USER@$SERVER_IP" "
    cd $REMOTE_PROJECT_DIR
    chmod 666 instance/edu_crm.db
    ls -la instance/edu_crm.db
    echo '✅ 数据库文件权限设置完成'
"

echo "🎉 数据库文件复制完成！"
echo "现在可以在服务器上运行部署脚本了："
echo "  cd $REMOTE_PROJECT_DIR"
echo "  ./deploy-compose.sh"
