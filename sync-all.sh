#!/bin/bash

# 同步代码到所有远程仓库的脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}==========================================${NC}"
echo -e "${CYAN}  同步代码到所有远程仓库${NC}"
echo -e "${CYAN}==========================================${NC}"
echo ""

# 检查是否有未提交的更改
if [[ -n $(git status --porcelain) ]]; then
    echo -e "${YELLOW}📝 检测到未提交的更改:${NC}"
    git status --short
    echo ""
    
    read -p "是否提交这些更改? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${YELLOW}📦 添加所有更改...${NC}"
        git add -A
        
        echo -e "${YELLOW}💾 提交更改...${NC}"
        COMMIT_MSG="${1:-sync: 同步代码到所有远程仓库}"
        git commit -m "$COMMIT_MSG"
        echo ""
    else
        echo -e "${BLUE}⏭️  跳过提交，仅推送已有提交${NC}"
        echo ""
    fi
fi

# 获取当前分支
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo -e "${NC}📍 当前分支: ${CURRENT_BRANCH}${NC}"
echo ""

# 推送到GitHub
echo -e "${CYAN}📤 推送到 GitHub...${NC}"
if git push github $CURRENT_BRANCH 2>&1; then
    echo -e "${GREEN}  ✅ GitHub 推送成功${NC}"
else
    echo -e "${RED}  ❌ GitHub 推送失败${NC}"
fi
echo ""

# 推送到Gitee
echo -e "${CYAN}📤 推送到 Gitee...${NC}"
if git push origin $CURRENT_BRANCH 2>&1; then
    echo -e "${GREEN}  ✅ Gitee 推送成功${NC}"
else
    echo -e "${RED}  ❌ Gitee 推送失败${NC}"
fi
echo ""

# 显示最新提交
echo -e "${NC}📋 最新的3个提交:${NC}"
git log --oneline -3
echo ""

# 显示远程状态
echo -e "${NC}🔍 远程仓库状态:${NC}"
LOCAL_COMMIT=$(git rev-parse HEAD)
GITHUB_COMMIT=$(git rev-parse github/$CURRENT_BRANCH 2>/dev/null || echo "未找到")
GITEE_COMMIT=$(git rev-parse origin/$CURRENT_BRANCH 2>/dev/null || echo "未找到")

echo "  本地:   ${LOCAL_COMMIT:0:12}"
echo "  GitHub: ${GITHUB_COMMIT:0:12}"
echo "  Gitee:  ${GITEE_COMMIT:0:12}"
echo ""

if [ "$LOCAL_COMMIT" = "$GITHUB_COMMIT" ] && [ "$LOCAL_COMMIT" = "$GITEE_COMMIT" ]; then
    echo -e "${GREEN}✅ 所有远程仓库已同步${NC}"
else
    echo -e "${YELLOW}⚠️  部分远程仓库未同步${NC}"
fi

echo ""
echo -e "${CYAN}==========================================${NC}"
echo -e "${CYAN}  同步完成${NC}"
echo -e "${CYAN}==========================================${NC}"
echo ""

