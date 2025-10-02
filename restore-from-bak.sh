#!/bin/bash

# ============================================
# 从Gitee bak分支恢复
# ============================================
# 
# 功能：
# 1. 从Gitee的bak分支恢复完整项目
# 2. 包括数据库文件
# 3. 恢复所有配置
#
# 使用方法：
#   bash restore-from-bak.sh
#
# ============================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

echo ""
echo "========================================="
echo "  📥 从Gitee bak分支恢复"
echo "========================================="
echo ""
echo "📋 本脚本将："
echo "  ✅ 从bak分支拉取完整备份"
echo "  ✅ 恢复数据库文件"
echo "  ✅ 恢复所有配置"
echo ""
echo "⚠️  注意："
echo "  - 这将覆盖当前的数据库文件"
echo "  - 建议先备份当前数据"
echo ""

read -p "是否继续？(y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "恢复已取消"
    exit 0
fi

echo ""

# ============================================
# 步骤1: 备份当前数据
# ============================================
log_step "步骤1/5: 备份当前数据"

if [ -f "instance/edu_crm.db" ]; then
    BACKUP_FILE="instance/edu_crm_before_restore_$(date +%Y%m%d_%H%M%S).db"
    cp instance/edu_crm.db "$BACKUP_FILE"
    log_success "当前数据库已备份: $BACKUP_FILE"
else
    log_info "当前没有数据库文件"
fi

echo ""

# ============================================
# 步骤2: 获取bak分支
# ============================================
log_step "步骤2/5: 获取bak分支"

log_info "从远程获取bak分支..."
git fetch origin bak

if [ $? -eq 0 ]; then
    log_success "bak分支获取成功"
else
    log_error "获取bak分支失败"
    exit 1
fi

echo ""

# ============================================
# 步骤3: 查看备份信息
# ============================================
log_step "步骤3/5: 查看备份信息"

log_info "最新备份信息:"
echo "-----------------------------------"
git log origin/bak -1 --pretty=format:"%h - %s%n%b" | head -20
echo ""
echo "-----------------------------------"

echo ""
read -p "确认要恢复这个备份吗？(y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "恢复已取消"
    exit 0
fi

echo ""

# ============================================
# 步骤4: 恢复文件
# ============================================
log_step "步骤4/5: 恢复文件"

# 保存当前分支
CURRENT_BRANCH=$(git branch --show-current)
log_info "当前分支: $CURRENT_BRANCH"

# 从bak分支恢复特定文件
log_info "恢复数据库文件..."
git checkout origin/bak -- instance/edu_crm.db

if [ $? -eq 0 ]; then
    log_success "数据库文件已恢复"
    
    # 显示数据库信息
    if [ -f "instance/edu_crm.db" ]; then
        DB_SIZE=$(du -h instance/edu_crm.db | cut -f1)
        log_info "恢复的数据库大小: $DB_SIZE"
    fi
else
    log_error "数据库文件恢复失败"
    exit 1
fi

# 询问是否恢复其他文件
echo ""
log_warning "是否要恢复其他文件？"
echo "  1) 只恢复数据库（推荐）"
echo "  2) 恢复所有文件（包括代码）"
echo ""
read -p "请选择 (1/2): " -n 1 -r
echo ""

if [[ $REPLY == "2" ]]; then
    log_info "恢复所有文件..."
    
    # 切换到bak分支
    git checkout bak
    
    # 复制所有文件到临时目录
    TEMP_DIR="/tmp/crm_restore_$(date +%s)"
    mkdir -p "$TEMP_DIR"
    cp -r . "$TEMP_DIR/"
    
    # 切换回原分支
    git checkout $CURRENT_BRANCH
    
    # 恢复文件（排除.git目录）
    rsync -av --exclude='.git' "$TEMP_DIR/" ./
    
    # 清理临时目录
    rm -rf "$TEMP_DIR"
    
    log_success "所有文件已恢复"
else
    log_info "只恢复数据库文件"
fi

echo ""

# ============================================
# 步骤5: 验证恢复
# ============================================
log_step "步骤5/5: 验证恢复"

# 检查数据库文件
if [ -f "instance/edu_crm.db" ]; then
    log_success "数据库文件存在"
    
    # 检查数据库完整性
    if sqlite3 instance/edu_crm.db "PRAGMA integrity_check;" | grep -q "ok"; then
        log_success "数据库完整性检查通过"
    else
        log_error "数据库完整性检查失败"
    fi
else
    log_error "数据库文件不存在"
fi

echo ""

# ============================================
# 完成
# ============================================
echo "========================================="
echo "  ✅ 恢复完成！"
echo "========================================="
echo ""

log_success "数据已从bak分支恢复"

echo ""
echo "📋 恢复信息:"
if [ -n "$BACKUP_FILE" ]; then
    echo "  - 原数据库备份: $BACKUP_FILE"
fi
echo "  - 恢复的数据库: instance/edu_crm.db"
if [ -f "instance/edu_crm.db" ]; then
    DB_SIZE=$(du -h instance/edu_crm.db | cut -f1)
    echo "  - 数据库大小: $DB_SIZE"
fi
echo ""

echo "🔍 下一步:"
echo "  - 重启服务: sudo systemctl restart crm"
echo "  - 验证数据: 登录系统检查数据"
echo "  - 查看日志: sudo journalctl -u crm -f"
echo ""

log_success "恢复流程已完成！"
echo ""

