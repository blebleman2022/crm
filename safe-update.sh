#!/bin/bash

# ============================================
# 安全更新脚本 - 保护数据库文件
# ============================================
# 
# 功能：
# 1. 自动备份数据库
# 2. 只更新代码文件，不影响数据库
# 3. 重新构建Docker镜像
# 4. 验证更新结果
#
# 使用方法：
#   bash safe-update.sh
#
# ============================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 日志函数
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

# 显示标题
echo ""
echo "========================================="
echo "  🚀 CRM系统安全更新脚本"
echo "========================================="
echo ""
echo "📋 本脚本将："
echo "  ✅ 自动备份数据库"
echo "  ✅ 只更新代码文件"
echo "  ✅ 保护数据库不被覆盖"
echo "  ✅ 重新构建Docker镜像"
echo ""

# 确认执行
read -p "是否继续？(y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "更新已取消"
    exit 0
fi

echo ""

# ============================================
# 步骤1: 检查环境
# ============================================
log_step "步骤1/7: 检查环境"

# 检查是否在项目目录
if [ ! -f "run.py" ] || [ ! -f "docker-compose.yml" ]; then
    log_error "请在项目根目录下运行此脚本"
    exit 1
fi
log_success "项目目录检查通过"

# 检查Git
if ! command -v git &> /dev/null; then
    log_error "Git未安装"
    exit 1
fi
log_success "Git已安装"

# 检查Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker未安装"
    exit 1
fi
log_success "Docker已安装"

echo ""

# ============================================
# 步骤2: 备份数据库
# ============================================
log_step "步骤2/7: 备份数据库"

if [ -f "instance/edu_crm.db" ]; then
    BACKUP_FILE="instance/edu_crm_backup_$(date +%Y%m%d_%H%M%S).db"
    cp instance/edu_crm.db "$BACKUP_FILE"
    log_success "数据库已备份: $BACKUP_FILE"
    
    # 显示数据库大小
    DB_SIZE=$(du -h instance/edu_crm.db | cut -f1)
    echo "  数据库大小: $DB_SIZE"
else
    log_warning "数据库文件不存在，跳过备份"
fi

echo ""

# ============================================
# 步骤3: 保护数据库文件
# ============================================
log_step "步骤3/7: 保护数据库文件"

# 临时移动数据库到安全位置
TEMP_DB="/tmp/edu_crm_temp_$(date +%s).db"
if [ -f "instance/edu_crm.db" ]; then
    mv instance/edu_crm.db "$TEMP_DB"
    log_success "数据库已移至安全位置: $TEMP_DB"
else
    log_warning "数据库文件不存在"
    TEMP_DB=""
fi

echo ""

# ============================================
# 步骤4: 清理Git状态
# ============================================
log_step "步骤4/7: 清理Git状态"

# 从Git中移除数据库文件的追踪（如果存在）
git rm --cached instance/edu_crm.db 2>/dev/null && log_success "已移除数据库文件的Git追踪" || log_info "数据库文件未被Git追踪"

# 重置本地更改（不影响未追踪的文件）
git reset --hard HEAD
log_success "Git状态已重置"

echo ""

# ============================================
# 步骤5: 拉取最新代码
# ============================================
log_step "步骤5/7: 拉取最新代码"

# 显示当前版本
CURRENT_COMMIT=$(git log --oneline -1)
echo "  当前版本: $CURRENT_COMMIT"

# 拉取代码
git pull origin master

if [ $? -eq 0 ]; then
    log_success "代码拉取成功"
    
    # 显示新版本
    NEW_COMMIT=$(git log --oneline -1)
    echo "  最新版本: $NEW_COMMIT"
    
    # 显示更新内容
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
        log_success "数据库已恢复"
    fi
    
    exit 1
fi

echo ""

# ============================================
# 步骤6: 恢复数据库
# ============================================
log_step "步骤6/7: 恢复数据库"

if [ -n "$TEMP_DB" ] && [ -f "$TEMP_DB" ]; then
    mv "$TEMP_DB" instance/edu_crm.db
    log_success "数据库已恢复到原位置"
    
    # 验证数据库完整性
    if [ -f "instance/edu_crm.db" ]; then
        DB_SIZE=$(du -h instance/edu_crm.db | cut -f1)
        log_success "数据库验证通过 (大小: $DB_SIZE)"
    else
        log_error "数据库恢复失败"
        exit 1
    fi
else
    log_info "无需恢复数据库"
fi

echo ""

# ============================================
# 步骤7: 重新构建Docker
# ============================================
log_step "步骤7/7: 重新构建Docker镜像"

# 停止容器
log_info "停止Docker容器..."
docker compose down
log_success "容器已停止"

# 重新构建
log_info "重新构建镜像（这可能需要几分钟）..."
docker compose build --no-cache

if [ $? -eq 0 ]; then
    log_success "镜像构建成功"
else
    log_error "镜像构建失败"
    exit 1
fi

# 启动容器
log_info "启动Docker容器..."
docker compose up -d

if [ $? -eq 0 ]; then
    log_success "容器已启动"
else
    log_error "容器启动失败"
    exit 1
fi

# 等待容器启动
log_info "等待容器启动..."
sleep 5

# 检查容器状态
CONTAINER_STATUS=$(docker compose ps | grep crm-app | awk '{print $4}')
if [ "$CONTAINER_STATUS" = "running" ]; then
    log_success "容器运行正常"
else
    log_error "容器状态异常: $CONTAINER_STATUS"
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
log_success "数据库文件已安全保留"
log_success "Docker容器已重新构建并启动"

echo ""
echo "📋 更新摘要:"
echo "  - 数据库备份: $BACKUP_FILE"
echo "  - 数据库状态: 已保留，未修改"
echo "  - 容器状态: $(docker compose ps | grep crm-app | awk '{print $4}')"
echo ""

echo "🔍 验证更新:"
echo "  - 查看日志: docker compose logs -f"
echo "  - 查看状态: docker compose ps"
echo "  - 访问系统: http://localhost:5000"
echo ""

echo "📁 备份文件位置:"
echo "  - $BACKUP_FILE"
echo ""

# 显示最近的日志
log_info "最近的容器日志:"
echo "-----------------------------------"
docker compose logs --tail=20
echo "-----------------------------------"

echo ""
log_success "安全更新流程已完成！"
echo ""

