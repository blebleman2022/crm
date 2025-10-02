#!/bin/bash

# ============================================
# 从bak分支恢复数据库文件
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
echo "  📥 从bak分支恢复数据库"
echo "========================================="
echo ""

# ============================================
# 步骤1: 检查当前数据库
# ============================================
log_step "步骤1/5: 检查当前数据库"

if [ -f "instance/edu_crm.db" ]; then
    DB_SIZE=$(stat -f%z "instance/edu_crm.db" 2>/dev/null || stat -c%s "instance/edu_crm.db" 2>/dev/null)
    log_info "当前数据库大小: $DB_SIZE bytes"
    
    if [ "$DB_SIZE" -gt 0 ]; then
        log_warning "当前数据库不为空"
        read -p "是否备份当前数据库并继续？(y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "操作已取消"
            exit 0
        fi
        
        # 备份当前数据库
        BACKUP_FILE="instance/edu_crm_before_restore_$(date +%Y%m%d_%H%M%S).db"
        cp instance/edu_crm.db "$BACKUP_FILE"
        log_success "当前数据库已备份: $BACKUP_FILE"
    else
        log_info "当前数据库为空，可以安全恢复"
    fi
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
# 步骤3: 检查bak分支的数据库
# ============================================
log_step "步骤3/5: 检查bak分支的数据库"

# 检查bak分支是否有数据库文件
if git cat-file -e origin/bak:instance/edu_crm.db 2>/dev/null; then
    log_success "bak分支中存在数据库文件"

    # 获取数据库文件大小
    BAK_DB_SIZE=$(git cat-file -s origin/bak:instance/edu_crm.db 2>/dev/null)
    log_info "bak分支数据库大小: $BAK_DB_SIZE bytes"

    if [ "$BAK_DB_SIZE" -eq 0 ] || [ -z "$BAK_DB_SIZE" ]; then
        log_error "bak分支的数据库文件也是空的！"
        exit 1
    fi
else
    log_error "bak分支中没有数据库文件"
    log_info "尝试列出bak分支的文件..."
    git ls-tree -r origin/bak --name-only | grep -i "instance\|db"
    exit 1
fi

echo ""

# ============================================
# 步骤4: 恢复数据库文件
# ============================================
log_step "步骤4/5: 恢复数据库文件"

log_info "从bak分支恢复数据库..."

# 确保instance目录存在
mkdir -p instance

# 从bak分支恢复数据库文件
git show origin/bak:instance/edu_crm.db > instance/edu_crm.db

if [ $? -eq 0 ]; then
    log_success "数据库文件已恢复"
    
    # 检查恢复后的文件大小
    RESTORED_SIZE=$(stat -f%z "instance/edu_crm.db" 2>/dev/null || stat -c%s "instance/edu_crm.db" 2>/dev/null)
    log_info "恢复后的数据库大小: $RESTORED_SIZE bytes"
    
    if [ "$RESTORED_SIZE" -eq 0 ]; then
        log_error "恢复的数据库文件是空的！"
        exit 1
    fi
else
    log_error "数据库文件恢复失败"
    exit 1
fi

echo ""

# ============================================
# 步骤5: 验证数据库
# ============================================
log_step "步骤5/5: 验证数据库"

log_info "验证数据库完整性..."

# 使用Python验证数据库
python3 check-db.py | grep -A 10 "6. 数据库表:"

echo ""

# ============================================
# 完成
# ============================================
echo "========================================="
echo "  ✅ 数据库恢复完成！"
echo "========================================="
echo ""

log_success "数据库已从bak分支恢复"

echo ""
echo "📋 恢复信息:"
echo "  - 数据库文件: instance/edu_crm.db"
echo "  - 文件大小: $RESTORED_SIZE bytes"
echo ""

echo "🔄 下一步:"
echo "  1. 重启CRM服务: sudo systemctl restart crm"
echo "  2. 查看服务状态: sudo systemctl status crm"
echo "  3. 查看日志: sudo journalctl -u crm -n 50"
echo "  4. 测试访问: curl http://localhost/health"
echo ""

log_success "恢复流程已完成！"
echo ""

