#!/bin/bash

# 检查本地代码是否与远程同步的脚本

echo "=========================================="
echo "  检查代码同步状态"
echo "=========================================="
echo ""

# 获取远程最新信息
echo "📡 获取远程最新信息..."
git fetch github 2>&1 | grep -v "^From" || true
echo ""

# 获取当前分支
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "📍 当前分支: $CURRENT_BRANCH"
echo ""

# 获取本地和远程的commit hash
LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse github/master 2>/dev/null || echo "未找到")

echo "🔍 Commit对比:"
echo "  本地 HEAD:        ${LOCAL_COMMIT:0:12}"
echo "  远程 github/master: ${REMOTE_COMMIT:0:12}"
echo ""

# 检查是否同步
if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo "✅ 状态: 本地代码与远程完全同步"
    echo ""
    echo "📋 最新的5个提交:"
    git log --oneline -5
else
    echo "⚠️  状态: 本地代码与远程不同步"
    echo ""
    
    # 检查本地是否领先
    AHEAD=$(git rev-list --count github/master..HEAD 2>/dev/null || echo "0")
    # 检查本地是否落后
    BEHIND=$(git rev-list --count HEAD..github/master 2>/dev/null || echo "0")
    
    if [ "$AHEAD" -gt 0 ]; then
        echo "📤 本地领先远程 $AHEAD 个提交"
        echo "   建议执行: git push github master"
        echo ""
        echo "📋 本地独有的提交:"
        git log github/master..HEAD --oneline
    fi
    
    if [ "$BEHIND" -gt 0 ]; then
        echo "📥 本地落后远程 $BEHIND 个提交"
        echo "   建议执行: git pull github master"
        echo ""
        echo "📋 远程新增的提交:"
        git log HEAD..github/master --oneline
    fi
fi

echo ""
echo "=========================================="
echo "  检查完成"
echo "=========================================="

