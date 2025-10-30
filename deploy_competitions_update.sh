#!/bin/bash

# 云服务器部署脚本 - 多赛事管理功能
# 服务器: 47.100.238.50
# 用户: root

echo "========================================="
echo "  多赛事管理功能部署脚本"
echo "========================================="
echo ""

# 服务器信息
SERVER="root@47.100.238.50"
PROJECT_DIR="/root/crm"

echo "📦 步骤1: 上传SQL文件..."
scp create_competitions_table.sql ${SERVER}:${PROJECT_DIR}/

echo ""
echo "🔄 步骤2: 在服务器上执行部署..."
ssh ${SERVER} << 'ENDSSH'
cd /root/crm

echo "📥 拉取最新代码..."
git pull origin master

echo ""
echo "🗄️  创建 customer_competitions 表..."
sqlite3 instance/edu_crm.db < create_competitions_table.sql

echo ""
echo "✅ 验证表是否创建成功..."
sqlite3 instance/edu_crm.db "SELECT name FROM sqlite_master WHERE type='table' AND name='customer_competitions';"

echo ""
echo "📋 查看表结构..."
sqlite3 instance/edu_crm.db ".schema customer_competitions"

echo ""
echo "🔄 重启服务..."
sudo systemctl restart crm

echo ""
echo "📊 查看服务状态..."
sudo systemctl status crm --no-pager

echo ""
echo "✅ 部署完成！"
ENDSSH

echo ""
echo "========================================="
echo "  部署完成！"
echo "========================================="
echo ""
echo "请访问 http://47.100.238.50/customers/list 测试功能"
echo ""

