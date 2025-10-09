#!/bin/bash

# ============================================
# 推送到GitHub main分支
# ============================================

echo "正在推送到GitHub main分支..."

# 推送master分支到GitHub的main分支
git push github master:main

if [ $? -eq 0 ]; then
    echo "✅ 成功推送到GitHub main分支"
else
    echo "❌ 推送失败，请检查网络连接"
    exit 1
fi

