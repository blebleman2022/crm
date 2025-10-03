#!/bin/bash

# ============================================
# 生产环境配置测试脚本
# 用于验证ECS直接部署时的配置是否正确
# ============================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "========================================"
echo "  生产环境配置测试"
echo "========================================"
echo ""

# 1. 测试Python环境
log_info "检查Python环境..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    log_success "Python已安装: $PYTHON_VERSION"
else
    log_error "Python3未安装"
    exit 1
fi

# 2. 测试虚拟环境
log_info "检查虚拟环境..."
if [ -d "venv" ]; then
    log_success "虚拟环境存在"
else
    log_error "虚拟环境不存在，请先创建: python3 -m venv venv"
    exit 1
fi

# 3. 激活虚拟环境并测试配置导入
log_info "测试配置导入..."
source venv/bin/activate

# 测试config模块导入
python3 << 'EOF'
import sys
try:
    from config import config, ProductionConfig, DevelopmentConfig, TestingConfig
    print("✅ config模块导入成功")
    print(f"   - ProductionConfig: {ProductionConfig.__name__}")
    print(f"   - DevelopmentConfig: {DevelopmentConfig.__name__}")
    print(f"   - TestingConfig: {TestingConfig.__name__}")
    sys.exit(0)
except Exception as e:
    print(f"❌ config模块导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    log_error "配置导入测试失败"
    exit 1
fi

# 4. 测试开发环境应用创建
log_info "测试开发环境应用创建..."
python3 << 'EOF'
import sys
import os
try:
    os.environ['FLASK_ENV'] = 'development'
    from run import create_app
    app = create_app('development')
    print(f"✅ 开发环境应用创建成功")
    print(f"   - DEBUG: {app.config.get('DEBUG')}")
    print(f"   - DATABASE: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    sys.exit(0)
except Exception as e:
    print(f"❌ 开发环境应用创建失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    log_error "开发环境应用创建失败"
    exit 1
fi

# 5. 测试生产环境应用创建
log_info "测试生产环境应用创建..."
python3 << 'EOF'
import sys
import os
try:
    os.environ['FLASK_ENV'] = 'production'
    from run import create_app
    app = create_app('production')
    print(f"✅ 生产环境应用创建成功")
    print(f"   - DEBUG: {app.config.get('DEBUG')}")
    print(f"   - SESSION_COOKIE_SECURE: {app.config.get('SESSION_COOKIE_SECURE')}")
    print(f"   - DATABASE: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    sys.exit(0)
except Exception as e:
    print(f"❌ 生产环境应用创建失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    log_error "生产环境应用创建失败"
    exit 1
fi

# 6. 测试Gunicorn导入（模拟ECS部署）
log_info "测试Gunicorn应用实例导入..."
python3 << 'EOF'
import sys
import os
try:
    os.environ['FLASK_ENV'] = 'production'
    # 模拟Gunicorn导入
    from run import app
    print(f"✅ Gunicorn应用实例导入成功")
    print(f"   - 应用名称: {app.name}")
    print(f"   - DEBUG: {app.config.get('DEBUG')}")
    sys.exit(0)
except Exception as e:
    print(f"❌ Gunicorn应用实例导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    log_error "Gunicorn应用实例导入失败"
    exit 1
fi

# 7. 测试Gunicorn配置文件
log_info "检查Gunicorn配置文件..."
if [ -f "gunicorn.conf.py" ]; then
    log_success "gunicorn.conf.py 存在"
    python3 -c "import gunicorn.conf" 2>/dev/null
    if [ $? -eq 0 ]; then
        log_success "Gunicorn配置文件语法正确"
    fi
else
    log_error "gunicorn.conf.py 不存在"
    exit 1
fi

echo ""
echo "========================================"
echo "  🎉 所有测试通过！"
echo "========================================"
echo ""
echo "✅ 配置修复成功，可以部署到ECS"
echo ""
echo "部署步骤："
echo "1. 推送代码到GitHub: git push github main"
echo "2. 在ECS上拉取代码: git pull"
echo "3. 重启服务: ./restart-server.sh 或 sudo systemctl restart crm"
echo ""

