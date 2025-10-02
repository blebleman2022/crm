#!/bin/bash

# ============================================
# 修复Git冲突 - 保留服务器数据库
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
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo ""
echo "========================================="
echo "  修复Git冲突 - 保留数据库"
echo "========================================="
echo ""

# 1. 备份数据库
log_info "备份数据库文件..."
if [ -f "instance/edu_crm.db" ]; then
    BACKUP_FILE="instance/edu_crm_backup_$(date +%Y%m%d_%H%M%S).db"
    cp instance/edu_crm.db "$BACKUP_FILE"
    log_success "数据库已备份到: $BACKUP_FILE"
else
    log_warning "数据库文件不存在，跳过备份"
fi

# 2. 从Git中移除数据库文件的追踪
log_info "从Git中移除数据库文件追踪..."
git rm --cached instance/edu_crm.db 2>/dev/null || true
log_success "数据库文件追踪已移除"

# 3. 重置本地更改
log_info "重置本地更改..."
git reset --hard HEAD
log_success "本地更改已重置"

# 4. 拉取最新代码
log_info "拉取最新代码..."
git pull origin master

if [ $? -eq 0 ]; then
    log_success "代码拉取成功"
else
    log_error "代码拉取失败"
    exit 1
fi

# 5. 恢复数据库文件
log_info "恢复数据库文件..."
if [ -f "$BACKUP_FILE" ]; then
    cp "$BACKUP_FILE" instance/edu_crm.db
    log_success "数据库文件已恢复"
else
    log_warning "备份文件不存在，使用现有数据库"
fi

# 6. 验证.gitignore
log_info "验证.gitignore配置..."
if grep -q "instance/\*.db" .gitignore; then
    log_success ".gitignore已正确配置"
else
    log_warning ".gitignore可能需要更新"
fi

# 7. 检查Git状态
log_info "检查Git状态..."
git status

echo ""
echo "========================================="
echo "  ✅ 修复完成！"
echo "========================================="
echo ""

log_success "数据库文件已保留，代码已更新"
echo ""
echo "📋 下一步操作："
echo "  1. 重新构建Docker镜像: docker compose build --no-cache"
echo "  2. 启动容器: docker compose up -d"
echo "  3. 查看日志: docker compose logs -f"
echo ""

