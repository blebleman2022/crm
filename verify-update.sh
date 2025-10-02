#!/bin/bash

# ============================================
# 验证服务器更新脚本
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
echo "  验证服务器更新状态"
echo "========================================="
echo ""

# 1. 检查Git状态
log_info "检查Git状态..."
echo ""

# 当前分支
CURRENT_BRANCH=$(git branch --show-current)
echo "当前分支: $CURRENT_BRANCH"

# 本地最新提交
LOCAL_COMMIT=$(git log --oneline -1)
echo "本地最新提交: $LOCAL_COMMIT"

# 远程最新提交
git fetch origin &>/dev/null
REMOTE_COMMIT=$(git log origin/master --oneline -1)
echo "远程最新提交: $REMOTE_COMMIT"

echo ""

# 比较本地和远程
if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    log_success "本地代码与远程同步"
else
    log_warning "本地代码与远程不同步"
    echo ""
    echo "未同步的提交:"
    git log HEAD..origin/master --oneline
    echo ""
    log_info "执行 'git pull origin master' 来更新"
fi

# 2. 检查关键文件
echo ""
log_info "检查关键文件..."
echo ""

# 检查约见管理模板
if grep -q "第二列显示今天" templates/consultations/list.html 2>/dev/null; then
    log_success "约见管理模板已更新（包含日历优化）"
else
    if grep -q "bg-green-500" templates/consultations/list.html 2>/dev/null; then
        log_success "约见管理模板已更新（包含颜色优化）"
    else
        log_error "约见管理模板未更新"
    fi
fi

# 检查.gitignore
if grep -q "instance/\*.db" .gitignore 2>/dev/null; then
    log_success ".gitignore已更新（数据库文件已忽略）"
else
    log_error ".gitignore未更新"
fi

# 3. 检查Docker容器状态
echo ""
log_info "检查Docker容器状态..."
echo ""

if command -v docker &> /dev/null; then
    if docker compose ps | grep -q "crm-app"; then
        CONTAINER_STATUS=$(docker compose ps | grep crm-app | awk '{print $4}')
        if [ "$CONTAINER_STATUS" = "running" ]; then
            log_success "Docker容器运行中"
            
            # 检查容器内的文件
            log_info "检查容器内的模板文件..."
            if docker compose exec -T crm-app grep -q "bg-green-500" /app/templates/consultations/list.html 2>/dev/null; then
                log_success "容器内模板文件已更新"
            else
                log_warning "容器内模板文件未更新，需要重新构建"
                echo ""
                echo "执行以下命令更新容器:"
                echo "  docker compose down"
                echo "  docker compose up -d --build"
            fi
        else
            log_error "Docker容器未运行: $CONTAINER_STATUS"
        fi
    else
        log_warning "未找到crm-app容器"
    fi
else
    log_info "Docker未安装，跳过容器检查"
fi

# 4. 检查最近的提交
echo ""
log_info "最近5次提交:"
echo ""
git log --oneline -5

# 5. 检查未追踪的文件
echo ""
log_info "检查未追踪的文件..."
echo ""

UNTRACKED=$(git ls-files --others --exclude-standard)
if [ -z "$UNTRACKED" ]; then
    log_success "没有未追踪的文件"
else
    log_warning "发现未追踪的文件:"
    echo "$UNTRACKED"
fi

# 6. 检查数据库文件
echo ""
log_info "检查数据库文件..."
echo ""

if [ -f "instance/edu_crm.db" ]; then
    log_success "数据库文件存在: instance/edu_crm.db"
    
    # 检查是否被Git追踪
    if git ls-files --error-unmatch instance/edu_crm.db &>/dev/null; then
        log_error "数据库文件仍被Git追踪（不应该）"
    else
        log_success "数据库文件未被Git追踪（正确）"
    fi
    
    # 显示数据库大小
    DB_SIZE=$(du -h instance/edu_crm.db | cut -f1)
    echo "数据库大小: $DB_SIZE"
else
    log_warning "数据库文件不存在，首次启动时会自动创建"
fi

# 7. 总结
echo ""
echo "========================================="
echo "  验证总结"
echo "========================================="
echo ""

# 检查是否需要更新
NEEDS_UPDATE=false

if [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
    NEEDS_UPDATE=true
    echo "❌ 需要执行: git pull origin master"
fi

if ! grep -q "bg-green-500" templates/consultations/list.html 2>/dev/null; then
    NEEDS_UPDATE=true
    echo "❌ 需要更新约见管理模板"
fi

if command -v docker &> /dev/null; then
    if docker compose ps | grep -q "crm-app"; then
        if ! docker compose exec -T crm-app grep -q "bg-green-500" /app/templates/consultations/list.html 2>/dev/null; then
            echo "❌ 需要重新构建Docker容器"
            echo ""
            echo "快速更新命令:"
            echo "  cd ~/crm"
            echo "  git pull origin master"
            echo "  docker compose down"
            echo "  docker compose up -d --build"
        fi
    fi
fi

if [ "$NEEDS_UPDATE" = false ]; then
    echo ""
    log_success "所有检查通过，系统已是最新状态！"
    echo ""
    echo "💡 提示："
    echo "  - 约见管理日历视图已优化"
    echo "  - 数据库文件已从Git中移除"
    echo "  - 刷新浏览器查看最新效果"
else
    echo ""
    log_warning "发现需要更新的项目，请按照上述提示操作"
fi

echo ""

