#!/bin/bash

# 云服务器代码同步到GitHub脚本
# 用途: 将云服务器bak分支的最新代码推送到GitHub

set -e  # 遇到错误立即退出

echo "=========================================="
echo "云服务器代码同步到GitHub"
echo "=========================================="
echo ""

# 服务器信息
SERVER_USER="root"
SERVER_HOST="iZuf69hbdqliku9isirlemZ"
SERVER_PATH="/root/crm"
SSH_KEY="login.pem"

echo "步骤 1/4: 连接云服务器并检查状态..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" << 'ENDSSH'
cd /root/crm

echo "当前分支:"
git branch

echo ""
echo "当前状态:"
git status

echo ""
echo "最近提交:"
git log --oneline -5

ENDSSH

echo ""
echo "步骤 2/4: 推送bak分支到GitHub..."
read -p "是否推送bak分支到GitHub? (y/n): " confirm

if [ "$confirm" != "y" ]; then
    echo "操作已取消"
    exit 0
fi

ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" << 'ENDSSH'
cd /root/crm

# 确保在bak分支
git checkout bak

# 推送到远程
echo "正在推送bak分支..."
git push origin bak || git push origin bak --force

echo "✓ bak分支推送成功"

ENDSSH

echo ""
echo "步骤 3/4: 是否同时更新master分支?"
read -p "用bak覆盖远程master分支? (y/n): " update_master

if [ "$update_master" = "y" ]; then
    ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" << 'ENDSSH'
cd /root/crm

echo "正在用bak覆盖远程master..."
git push origin bak:master --force

echo "✓ master分支已更新"

ENDSSH
fi

echo ""
echo "步骤 4/4: 验证推送结果..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" << 'ENDSSH'
cd /root/crm

echo "远程分支状态:"
git branch -r

echo ""
echo "最新提交:"
git log --oneline -3

ENDSSH

echo ""
echo "=========================================="
echo "✓ 同步完成!"
echo "=========================================="
echo ""
echo "GitHub仓库: https://github.com/blebleman2022/crm"
echo ""

