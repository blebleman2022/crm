#!/bin/bash

# 启动本地CRM服务脚本
# 使用方法: bash start_local.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "启动 EduConnect CRM 本地服务"
echo "=========================================="
echo ""

# 设置端口（允许外部传入）
PORT="${PORT:-5002}"

# 优先使用项目内虚拟环境的 python3，避免 activate 路径失效
if [ -x "$SCRIPT_DIR/venv/bin/python3" ]; then
    PYTHON_BIN="$SCRIPT_DIR/venv/bin/python3"
else
    PYTHON_BIN="$(command -v python3 || true)"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "❌ 未找到 python3，请先安装 Python 3"
    exit 1
fi

echo "🐍 Python: $PYTHON_BIN"

# 检查端口是否被占用
echo "🔍 检查端口 $PORT 是否被占用..."
if lsof -ti:"$PORT" > /dev/null 2>&1; then
    echo "⚠️  端口 $PORT 已被占用，正在停止旧进程..."
    lsof -ti:"$PORT" | xargs kill -9 2>/dev/null || true
    sleep 1
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

PORT="$PORT" "$PYTHON_BIN" run.py run
