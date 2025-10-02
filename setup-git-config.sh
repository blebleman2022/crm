#!/bin/bash

# ============================================
# Git配置脚本
# ============================================

echo "========================================="
echo "  Git用户配置"
echo "========================================="
echo ""

# 配置用户名
git config --global user.name "blebleman"

# 配置邮箱
git config --global user.email "blebleman2022@gmail.com"

# 配置默认分支名
git config --global init.defaultBranch master

# 配置编辑器
git config --global core.editor "nano"

# 配置颜色
git config --global color.ui auto

# 显示配置
echo "✅ Git配置完成！"
echo ""
echo "当前配置："
echo "-----------------------------------"
git config --global --list | grep user
echo "-----------------------------------"
echo ""

