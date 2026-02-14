#!/bin/bash

echo "=========================================="
echo "🔍 检查服务器启动问题"
echo "=========================================="
echo ""

cd /root/crm

echo "1. 检查 config.py 文件"
echo "----------------------------------------"
if [ -f "config.py" ]; then
    echo "✅ config.py 存在"
    echo "文件大小: $(wc -l < config.py) 行"
else
    echo "❌ config.py 不存在!"
fi
echo ""

echo "2. 测试导入 config"
echo "----------------------------------------"
source venv/bin/activate
python3 << 'EOF'
try:
    from config import config
    print("✅ config 模块导入成功")
    print(f"   可用配置: {list(config.keys())}")
except Exception as e:
    print(f"❌ config 模块导入失败: {e}")
    import traceback
    traceback.print_exc()
EOF
echo ""

echo "3. 测试创建 Flask 应用"
echo "----------------------------------------"
python3 << 'EOF'
import sys
import os

# 捕获所有输出
import io
from contextlib import redirect_stdout, redirect_stderr

stdout_capture = io.StringIO()
stderr_capture = io.StringIO()

try:
    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        from run import app
    
    stdout_output = stdout_capture.getvalue()
    stderr_output = stderr_capture.getvalue()
    
    if stdout_output:
        print("标准输出:")
        print(stdout_output)
    
    if stderr_output:
        print("错误输出:")
        print(stderr_output)
    
    print(f"✅ Flask 应用创建成功")
    print(f"   应用类型: {type(app)}")
    print(f"   应用名称: {app.name}")
    
    # 测试路由
    print(f"   注册的蓝图数量: {len(app.blueprints)}")
    print(f"   蓝图列表: {list(app.blueprints.keys())}")
    
except Exception as e:
    print(f"❌ Flask 应用创建失败: {e}")
    import traceback
    traceback.print_exc()
    
    stdout_output = stdout_capture.getvalue()
    stderr_output = stderr_capture.getvalue()
    
    if stdout_output:
        print("\n标准输出:")
        print(stdout_output)
    
    if stderr_output:
        print("\n错误输出:")
        print(stderr_output)
EOF
echo ""

echo "4. 检查 Gunicorn 配置"
echo "----------------------------------------"
if [ -f "gunicorn_config.py" ]; then
    echo "✅ gunicorn_config.py 存在"
    cat gunicorn_config.py
else
    echo "⚠️  gunicorn_config.py 不存在"
fi
echo ""

echo "5. 查看 systemd 服务配置"
echo "----------------------------------------"
cat /etc/systemd/system/crm.service
echo ""

echo "6. 测试 Gunicorn 启动"
echo "----------------------------------------"
echo "尝试手动启动 Gunicorn (5秒后自动停止)..."
timeout 5 gunicorn -c gunicorn_config.py run:app 2>&1 || true
echo ""

echo "=========================================="
echo "检查完成"
echo "=========================================="

