#!/bin/bash

# 启动本地CRM服务脚本
# 使用方法: bash start_local.sh

echo "=========================================="
echo "启动 EduConnect CRM 本地服务"
echo "=========================================="
echo ""

# 设置端口
PORT=5002

# 检查端口是否被占用
echo "🔍 检查端口 $PORT 是否被占用..."
if lsof -ti:$PORT > /dev/null 2>&1; then
    echo "⚠️  端口 $PORT 已被占用，正在停止旧进程..."
    lsof -ti:$PORT | xargs kill -9 2>/dev/null
    sleep 2
    echo "✅ 旧进程已停止"
else
    echo "✅ 端口 $PORT 可用"
fi

echo ""
echo "🚀 启动服务..."
echo "   - 端口: $PORT"
echo "   - 环境: development"
echo "   - 访问地址: http://127.0.0.1:$PORT"
echo ""

# 激活虚拟环境并启动服务
source venv/bin/activate && PORT=$PORT python run.py

