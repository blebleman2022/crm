#!/bin/bash

# ============================================
# 清理废弃文件脚本
# ============================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

echo ""
echo "========================================="
echo "  🗑️  清理废弃文件"
echo "========================================="
echo ""
echo "📋 将要删除的文件："
echo ""

# 列出将要删除的文件
FILES_TO_DELETE=(
    # 废弃的Shell脚本
    "setup-nginx.sh"
    "fix-nginx-static.sh"
    "fix-permissions.sh"
    "deploy.sh"
    "rollback-server.sh"
    "fix-network.sh"
    "check-sync.sh"
    "sync-all.sh"
    
    # 废弃的文档
    "服务器更新完整指南.md"
    "服务器更新指南.md"
    "服务器更新步骤.md"
    "云服务器配置检查报告.md"
    "修复Nginx静态文件问题.md"
    "DEPLOY-CLOUD.md"
    
    # 废弃的PowerShell脚本
    "sync-all.ps1"
    "check-sync.ps1"
    "verify-sync.ps1"
    
    # 废弃的配置文件
    "Dockerfile.simple"
    "requirements-minimal.txt"
)

# 显示将要删除的文件
for file in "${FILES_TO_DELETE[@]}"; do
    if [ -f "$file" ]; then
        echo "  ❌ $file"
    fi
done

echo ""
echo "⚠️  注意："
echo "  - 这些文件已被新的部署方案替代"
echo "  - 删除后可以从Git历史恢复"
echo ""

read -p "确认删除这些文件？(y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "清理已取消"
    exit 0
fi

echo ""
log_info "开始清理..."
echo ""

# 删除文件
DELETED_COUNT=0
for file in "${FILES_TO_DELETE[@]}"; do
    if [ -f "$file" ]; then
        rm "$file"
        log_success "已删除: $file"
        DELETED_COUNT=$((DELETED_COUNT + 1))
    fi
done

echo ""
echo "========================================="
echo "  ✅ 清理完成！"
echo "========================================="
echo ""

log_success "已删除 $DELETED_COUNT 个文件"

echo ""
echo "📋 Git状态："
echo "-----------------------------------"
git status --short | grep "^ D" || echo "  (无删除的文件)"
echo "-----------------------------------"

echo ""
echo "💡 下一步："
echo "  1. 查看删除的文件: git status"
echo "  2. 提交更改: git add -A"
echo "  3. 提交: git commit -m 'chore: 清理废弃文件'"
echo "  4. 推送: git push origin master"
echo ""

