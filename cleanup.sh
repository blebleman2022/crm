#!/bin/bash

# 项目文件清理脚本
# 删除过时的 Docker 文件、重复脚本和过时文档

set -e

echo "=========================================="
echo "  CRM 项目文件清理"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否在项目目录
if [ ! -f "run.py" ]; then
    echo -e "${RED}❌ 错误：请在项目根目录下运行此脚本${NC}"
    exit 1
fi

echo "即将删除以下文件："
echo ""
echo "【Docker 相关】"
echo "  - Dockerfile"
echo "  - Dockerfile.simple"
echo "  - docker-compose.yml"
echo "  - .dockerignore"
echo "  - DEPLOY-CLOUD.md"
echo ""
echo "【过时脚本】"
echo "  - backup-db.sh"
echo "  - install-backup-cron.sh"
echo "  - deploy.sh"
echo "  - diagnose-and-fix.sh"
echo "  - fix-network.sh"
echo "  - restart-server.sh"
echo "  - rollback-server.sh"
echo "  - setup-china-mirrors.sh"
echo "  - test_production_config.sh"
echo "  - verify-deployment.sh"
echo ""
echo "【过时文档】"
echo "  - CHINA-MIRRORS.md"
echo "  - CONFIG.md"
echo "  - DEPLOYMENT_FIX.md"
echo "  - ECS_DEPLOYMENT_GUIDE.md"
echo "  - README-backup.md"
echo "  - REQUIREMENTS.md"
echo "  - 修复总结.md"
echo "  - 客户列表权限修改说明.md"
echo "  - 服务器更新指南.md"
echo ""
echo "【测试/临时文件】"
echo "  - fix_test_data.py"
echo "  - migrate_user_roles.py"
echo "  - test_config.py"
echo ""
echo "【重复文件】"
echo "  - instance/edu_crm1.db"
echo "  - requirements-dev.txt"
echo "  - requirements-minimal.txt"
echo ""

read -p "确认删除这些文件？[y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⚠️  已取消清理${NC}"
    exit 0
fi

echo ""
echo "开始清理..."
echo ""

# 计数器
DELETED=0
NOTFOUND=0

# 删除函数
delete_file() {
    if [ -f "$1" ]; then
        rm -f "$1"
        echo -e "${GREEN}✅ 已删除: $1${NC}"
        DELETED=$((DELETED + 1))
    else
        echo -e "${YELLOW}⚠️  未找到: $1${NC}"
        NOTFOUND=$((NOTFOUND + 1))
    fi
}

# Docker 相关
echo "清理 Docker 相关文件..."
delete_file "Dockerfile"
delete_file "Dockerfile.simple"
delete_file "docker-compose.yml"
delete_file ".dockerignore"
delete_file "DEPLOY-CLOUD.md"
echo ""

# 过时脚本
echo "清理过时脚本..."
delete_file "backup-db.sh"
delete_file "install-backup-cron.sh"
delete_file "deploy.sh"
delete_file "diagnose-and-fix.sh"
delete_file "fix-network.sh"
delete_file "restart-server.sh"
delete_file "rollback-server.sh"
delete_file "setup-china-mirrors.sh"
delete_file "test_production_config.sh"
delete_file "verify-deployment.sh"
echo ""

# 过时文档
echo "清理过时文档..."
delete_file "CHINA-MIRRORS.md"
delete_file "CONFIG.md"
delete_file "DEPLOYMENT_FIX.md"
delete_file "ECS_DEPLOYMENT_GUIDE.md"
delete_file "README-backup.md"
delete_file "REQUIREMENTS.md"
delete_file "修复总结.md"
delete_file "客户列表权限修改说明.md"
delete_file "服务器更新指南.md"
echo ""

# 测试/临时文件
echo "清理测试/临时文件..."
delete_file "fix_test_data.py"
delete_file "migrate_user_roles.py"
delete_file "test_config.py"
echo ""

# 重复文件
echo "清理重复文件..."
delete_file "instance/edu_crm1.db"
delete_file "requirements-dev.txt"
delete_file "requirements-minimal.txt"
echo ""

echo "=========================================="
echo "  清理完成"
echo "=========================================="
echo ""
echo "统计："
echo "  - 已删除: $DELETED 个文件"
echo "  - 未找到: $NOTFOUND 个文件"
echo ""
echo "下一步："
echo "  1. 运行 'git status' 查看变更"
echo "  2. 运行 'git add -A' 暂存删除"
echo "  3. 运行 'git commit -m \"chore: 清理过时文件\"'"
echo "  4. 运行 'git push github master:main' 推送到远程"
echo ""

