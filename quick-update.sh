#!/bin/bash

# ============================================
# 快速更新脚本 - Ubuntu直接部署版本
# ============================================
# 
# 功能：
# 1. 备份数据库
# 2. 拉取最新代码
# 3. 重启服务
# 4. 验证更新
#
# 使用方法：
#   bash quick-update.sh
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
echo "  🚀 CRM系统快速更新"
echo "========================================="
echo ""

# ============================================
# 步骤1: 备份数据库
# ============================================
log_step "步骤1/4: 备份数据库"

if [ -f "instance/edu_crm.db" ]; then
    BACKUP_FILE="instance/edu_crm_backup_$(date +%Y%m%d_%H%M%S).db"
    cp instance/edu_crm.db "$BACKUP_FILE"
    log_success "数据库已备份: $BACKUP_FILE"
    
    DB_SIZE=$(du -h instance/edu_crm.db | cut -f1)
    echo "  数据库大小: $DB_SIZE"
else
    log_warning "数据库文件不存在"
fi

echo ""

# ============================================
# 步骤2: 拉取最新代码
# ============================================
log_step "步骤2/4: 拉取最新代码"

# 显示当前版本
CURRENT_COMMIT=$(git log --oneline -1)
echo "  当前版本: $CURRENT_COMMIT"

# 保护数据库文件
TEMP_DB=""
if [ -f "instance/edu_crm.db" ]; then
    TEMP_DB="/tmp/edu_crm_temp_$(date +%s).db"
    mv instance/edu_crm.db "$TEMP_DB"
    log_info "数据库已临时移动"
fi

# 清理Git状态
git rm --cached instance/edu_crm.db 2>/dev/null || true
git reset --hard HEAD

# 拉取代码
git pull origin master

if [ $? -eq 0 ]; then
    log_success "代码拉取成功"
    
    NEW_COMMIT=$(git log --oneline -1)
    echo "  最新版本: $NEW_COMMIT"
    
    if [ "$CURRENT_COMMIT" != "$NEW_COMMIT" ]; then
        echo ""
        log_info "本次更新内容:"
        git log --oneline --graph --decorate -5
    else
        log_info "代码已是最新版本"
    fi
else
    log_error "代码拉取失败"
    
    # 恢复数据库
    if [ -n "$TEMP_DB" ] && [ -f "$TEMP_DB" ]; then
        mv "$TEMP_DB" instance/edu_crm.db
    fi
    
    exit 1
fi

# 恢复数据库
if [ -n "$TEMP_DB" ] && [ -f "$TEMP_DB" ]; then
    mv "$TEMP_DB" instance/edu_crm.db
    log_success "数据库已恢复"
fi

echo ""

# ============================================
# 步骤3: 重启服务
# ============================================
log_step "步骤3/4: 重启服务"

log_info "重启CRM服务..."
sudo systemctl restart crm

sleep 2

if sudo systemctl is-active --quiet crm; then
    log_success "CRM服务已重启"
else
    log_error "CRM服务重启失败"
    log_info "查看日志: sudo journalctl -u crm -n 50"
    exit 1
fi

echo ""

# ============================================
# 步骤4: 验证更新
# ============================================
log_step "步骤4/4: 验证更新"

# 检查服务状态
SERVICE_STATUS=$(sudo systemctl is-active crm)
if [ "$SERVICE_STATUS" = "active" ]; then
    log_success "服务运行正常"
else
    log_error "服务状态异常: $SERVICE_STATUS"
fi

# 检查端口
if netstat -tuln | grep -q ":5000"; then
    log_success "端口5000正在监听"
else
    log_warning "端口5000未监听"
fi

# 测试HTTP访问
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000 2>/dev/null)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
    log_success "HTTP访问正常 (状态码: $HTTP_CODE)"
else
    log_warning "HTTP访问异常 (状态码: $HTTP_CODE)"
fi

echo ""

# ============================================
# 完成
# ============================================
echo "========================================="
echo "  ✅ 更新完成！"
echo "========================================="
echo ""

log_success "代码已更新到最新版本"
log_success "数据库文件已保留"
log_success "服务已重启"

echo ""
echo "📋 更新摘要:"
echo "  - 数据库备份: $BACKUP_FILE"
echo "  - 服务状态: $SERVICE_STATUS"
echo "  - HTTP状态: $HTTP_CODE"
echo ""

echo "🔍 验证更新:"
echo "  - 查看服务状态: sudo systemctl status crm"
echo "  - 查看实时日志: sudo journalctl -u crm -f"
echo "  - 查看应用日志: tail -f /var/log/crm/app.log"
echo "  - 访问系统: http://localhost"
echo ""

# 显示最近的日志
log_info "最近的服务日志:"
echo "-----------------------------------"
sudo journalctl -u crm -n 20 --no-pager
echo "-----------------------------------"

echo ""
log_success "快速更新完成！刷新浏览器即可看到最新效果。"
echo ""

