#!/bin/bash

# ============================================
# 完整备份到Gitee bak分支
# ============================================
# 
# 功能：
# 1. 备份整个项目文件夹（包括数据库）
# 2. 推送到Gitee的bak分支
# 3. 保留完整的项目状态
#
# 使用方法：
#   bash backup-to-gitee.sh
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
echo "  📦 完整备份到Gitee bak分支"
echo "========================================="
echo ""
echo "📋 本脚本将："
echo "  ✅ 备份整个项目文件夹"
echo "  ✅ 包括数据库文件"
echo "  ✅ 包括日志文件"
echo "  ✅ 推送到Gitee的bak分支"
echo ""
echo "⚠️  注意："
echo "  - 这将创建一个新的bak分支"
echo "  - 数据库文件会被包含在备份中"
echo "  - 备份会覆盖远程bak分支"
echo ""

read -p "是否继续？(y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "备份已取消"
    exit 0
fi

echo ""

# ============================================
# 步骤1: 检查环境
# ============================================
log_step "步骤1/7: 检查环境"

# 检查是否在Git仓库中
if [ ! -d ".git" ]; then
    log_error "当前目录不是Git仓库"
    exit 1
fi
log_success "Git仓库检查通过"

# 检查远程仓库
if ! git remote | grep -q "origin"; then
    log_error "未找到origin远程仓库"
    exit 1
fi

REMOTE_URL=$(git remote get-url origin)
log_success "远程仓库: $REMOTE_URL"

echo ""

# ============================================
# 步骤2: 保存当前分支
# ============================================
log_step "步骤2/7: 保存当前状态"

CURRENT_BRANCH=$(git branch --show-current)
log_info "当前分支: $CURRENT_BRANCH"

# 保存当前工作区状态
if ! git diff-index --quiet HEAD --; then
    log_warning "工作区有未提交的更改"
    git stash push -m "backup-script-stash-$(date +%Y%m%d_%H%M%S)"
    STASHED=true
    log_success "工作区已暂存"
else
    STASHED=false
    log_info "工作区干净"
fi

echo ""

# ============================================
# 步骤3: 创建临时.gitignore用于备份
# ============================================
log_step "步骤3/7: 准备备份配置"

# 备份原始.gitignore
if [ -f ".gitignore" ]; then
    cp .gitignore .gitignore.backup
    log_success "已备份原始.gitignore"
fi

# 创建备份专用的.gitignore（只排除不需要的文件）
cat > .gitignore.bak <<EOF
# 备份专用.gitignore - 只排除真正不需要的文件

# Python缓存
__pycache__/
*.py[cod]
*\$py.class
*.so

# 虚拟环境（太大，不备份）
venv/
env/
ENV/

# IDE配置
.vscode/
.idea/

# OS文件
.DS_Store
Thumbs.db

# 临时文件
*.tmp
*.temp
*.swp
*.swo
*~

# 备份文件本身
.gitignore.backup
.gitignore.bak
EOF

log_success "备份配置已创建"

echo ""

# ============================================
# 步骤4: 切换到bak分支
# ============================================
log_step "步骤4/7: 切换到bak分支"

# 检查bak分支是否存在
if git show-ref --verify --quiet refs/heads/bak; then
    log_info "bak分支已存在，切换到bak分支"
    git checkout bak
else
    log_info "创建新的bak分支"
    git checkout -b bak
fi

log_success "已切换到bak分支"

echo ""

# ============================================
# 步骤5: 使用备份配置并添加所有文件
# ============================================
log_step "步骤5/7: 添加所有文件到备份"

# 使用备份专用的.gitignore
mv .gitignore.bak .gitignore

# 添加所有文件（包括数据库）
log_info "添加所有文件..."
git add -A

# 显示将要备份的文件
log_info "备份文件列表："
echo "-----------------------------------"
git status --short | head -20
TOTAL_FILES=$(git status --short | wc -l)
if [ $TOTAL_FILES -gt 20 ]; then
    echo "... 还有 $((TOTAL_FILES - 20)) 个文件"
fi
echo "-----------------------------------"

log_success "已添加 $TOTAL_FILES 个文件"

echo ""

# ============================================
# 步骤6: 提交备份
# ============================================
log_step "步骤6/7: 提交备份"

# 生成备份信息
BACKUP_TIME=$(date '+%Y-%m-%d %H:%M:%S')
BACKUP_HOST=$(hostname)
BACKUP_USER=$(whoami)

# 检查是否有数据库文件
DB_INFO=""
if [ -f "instance/edu_crm.db" ]; then
    DB_SIZE=$(du -h instance/edu_crm.db | cut -f1)
    DB_INFO="数据库大小: $DB_SIZE"
fi

# 提交备份
COMMIT_MSG="backup: 完整备份 - $BACKUP_TIME

备份信息:
- 时间: $BACKUP_TIME
- 主机: $BACKUP_HOST
- 用户: $BACKUP_USER
- $DB_INFO
- 分支: $CURRENT_BRANCH

此备份包含:
- 所有源代码
- 数据库文件
- 配置文件
- 日志文件（如果有）
- 静态文件
"

git commit -m "$COMMIT_MSG"

if [ $? -eq 0 ]; then
    log_success "备份已提交"
else
    log_warning "没有新的更改需要提交"
fi

echo ""

# ============================================
# 步骤7: 推送到Gitee
# ============================================
log_step "步骤7/7: 推送到Gitee"

log_info "推送到远程bak分支..."
git push -f origin bak

if [ $? -eq 0 ]; then
    log_success "备份已推送到Gitee"
else
    log_error "推送失败"
    
    # 恢复原始状态
    git checkout $CURRENT_BRANCH
    if [ -f ".gitignore.backup" ]; then
        mv .gitignore.backup .gitignore
    fi
    
    exit 1
fi

echo ""

# ============================================
# 清理和恢复
# ============================================
log_step "清理和恢复"

# 切换回原始分支
log_info "切换回 $CURRENT_BRANCH 分支..."
git checkout $CURRENT_BRANCH

# 恢复原始.gitignore
if [ -f ".gitignore.backup" ]; then
    mv .gitignore.backup .gitignore
    log_success "已恢复原始.gitignore"
fi

# 恢复工作区
if [ "$STASHED" = true ]; then
    log_info "恢复工作区..."
    git stash pop
    log_success "工作区已恢复"
fi

echo ""

# ============================================
# 完成
# ============================================
echo "========================================="
echo "  ✅ 备份完成！"
echo "========================================="
echo ""

log_success "完整备份已推送到Gitee的bak分支"

echo ""
echo "📋 备份信息:"
echo "  - 备份时间: $BACKUP_TIME"
echo "  - 备份主机: $BACKUP_HOST"
echo "  - 备份用户: $BACKUP_USER"
if [ -n "$DB_INFO" ]; then
    echo "  - $DB_INFO"
fi
echo "  - 远程分支: origin/bak"
echo ""

echo "🔍 查看备份:"
echo "  - Gitee网页: ${REMOTE_URL%.git}/tree/bak"
echo "  - 本地查看: git checkout bak"
echo "  - 查看提交: git log bak -1"
echo ""

echo "📥 恢复备份:"
echo "  - 克隆备份: git clone -b bak $REMOTE_URL"
echo "  - 切换到备份: git checkout bak"
echo ""

echo "💡 提示:"
echo "  - bak分支包含完整的项目状态"
echo "  - 包括数据库文件和所有配置"
echo "  - 可以随时从bak分支恢复"
echo ""

log_success "备份流程已完成！"
echo ""

