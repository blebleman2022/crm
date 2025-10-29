#!/bin/bash

# 自动推送脚本 - 每10秒尝试一次，直到成功
# 使用方法：bash auto_push.sh

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}自动推送脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "目标: 推送本地 master 分支到远程 main 分支"
echo "间隔: 每10秒重试一次"
echo "按 Ctrl+C 可随时停止"
echo ""

# 计数器
attempt=0

while true; do
  attempt=$((attempt + 1))
  timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  
  echo -e "${YELLOW}[尝试 #$attempt] $timestamp - 正在推送到 GitHub...${NC}"
  
  # 尝试推送
  if git push origin master:main 2>&1; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ 推送成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "推送时间: $timestamp"
    echo "尝试次数: $attempt"
    echo ""
    
    # 显示最新的提交
    echo "最新提交:"
    git log --oneline -3
    
    exit 0
  else
    echo -e "${RED}❌ 推送失败${NC}"
    echo -e "${YELLOW}10秒后重试...${NC}"
    echo ""
    sleep 10
  fi
done

