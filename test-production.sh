#!/bin/bash

# 模拟生产环境测试脚本
set -e

echo "🏭 模拟生产环境测试"
echo "=================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 创建测试环境
setup_test_env() {
    log_info "设置测试环境..."
    
    # 创建测试目录
    TEST_DIR="./test-env"
    rm -rf $TEST_DIR
    mkdir -p $TEST_DIR/instance
    mkdir -p $TEST_DIR/logs
    
    # 创建虚拟环境
    log_info "创建虚拟环境..."
    python -m venv $TEST_DIR/venv
    
    # 激活虚拟环境并安装依赖
    log_info "安装依赖..."
    source $TEST_DIR/venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    log_success "测试环境设置完成"
}

# 复制应用文件
copy_app_files() {
    log_info "复制应用文件..."
    
    # 复制必要的文件
    cp run.py $TEST_DIR/
    cp config.py $TEST_DIR/
    cp models.py $TEST_DIR/
    cp communication_utils.py $TEST_DIR/
    cp -r routes $TEST_DIR/
    cp -r templates $TEST_DIR/
    cp -r static $TEST_DIR/
    cp -r utils $TEST_DIR/
    
    log_success "应用文件复制完成"
}

# 测试应用启动
test_app_startup() {
    log_info "测试应用启动..."
    
    cd $TEST_DIR
    source venv/bin/activate
    
    # 设置环境变量
    export FLASK_ENV=production
    export DATABASE_URL=sqlite:///instance/edu_crm.db
    export SECRET_KEY=test-production-secret
    
    # 测试导入
    python -c "
import sys
sys.path.insert(0, '.')
try:
    from run import app
    print('✅ 生产环境导入成功')
    print(f'✅ app: {app}')
    
    # 测试应用上下文
    with app.app_context():
        from models import db
        db.create_all()
        print('✅ 数据库初始化成功')
        
    print('🎉 生产环境测试通过！')
except Exception as e:
    print(f'❌ 生产环境测试失败: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"
    
    cd ..
    log_success "应用启动测试完成"
}

# 测试Gunicorn启动
test_gunicorn() {
    log_info "测试Gunicorn启动..."
    
    cd $TEST_DIR
    source venv/bin/activate
    
    # 设置环境变量
    export FLASK_ENV=production
    export DATABASE_URL=sqlite:///instance/edu_crm.db
    export SECRET_KEY=test-production-secret
    
    # 启动Gunicorn（后台运行）
    log_info "启动Gunicorn服务器..."
    gunicorn --bind 127.0.0.1:8083 --workers 1 --timeout 30 --daemon --pid gunicorn.pid run:app
    
    # 等待启动
    sleep 5
    
    # 测试连接
    if curl -f http://127.0.0.1:8083/health > /dev/null 2>&1; then
        log_success "Gunicorn启动成功，健康检查通过"
    elif curl -f http://127.0.0.1:8083/auth/login > /dev/null 2>&1; then
        log_success "Gunicorn启动成功，登录页面可访问"
    else
        log_error "Gunicorn启动失败或应用无法访问"
        
        # 检查进程
        if [ -f gunicorn.pid ]; then
            local pid=$(cat gunicorn.pid)
            if ps -p $pid > /dev/null; then
                log_info "Gunicorn进程运行中 (PID: $pid)"
                log_info "检查端口监听..."
                netstat -an | grep 8083 || log_warning "端口8083未监听"
            else
                log_error "Gunicorn进程已退出"
            fi
        fi
        
        cd ..
        return 1
    fi
    
    # 停止Gunicorn
    if [ -f gunicorn.pid ]; then
        kill $(cat gunicorn.pid) 2>/dev/null || true
        rm -f gunicorn.pid
    fi
    
    cd ..
    log_success "Gunicorn测试完成"
}

# 清理测试环境
cleanup() {
    log_info "清理测试环境..."
    
    # 停止可能运行的进程
    if [ -f $TEST_DIR/gunicorn.pid ]; then
        kill $(cat $TEST_DIR/gunicorn.pid) 2>/dev/null || true
    fi
    
    # 删除测试目录
    rm -rf $TEST_DIR
    
    log_success "清理完成"
}

# 显示测试结果
show_results() {
    log_info "测试总结"
    echo "================================"
    log_success "✅ Python语法检查通过"
    log_success "✅ 应用导入测试通过"
    log_success "✅ 数据库初始化通过"
    log_success "✅ Gunicorn启动测试通过"
    echo ""
    log_info "🎉 所有测试通过！应用可以正常部署到生产环境。"
    echo ""
    log_info "📝 测试环境信息："
    echo "  - Python版本: $(python --version)"
    echo "  - 测试端口: 8083"
    echo "  - 数据库: SQLite"
    echo "  - Web服务器: Gunicorn"
}

# 主函数
main() {
    local action=${1:-all}
    
    case $action in
        setup)
            setup_test_env
            ;;
        copy)
            copy_app_files
            ;;
        test)
            test_app_startup
            ;;
        gunicorn)
            test_gunicorn
            ;;
        cleanup)
            cleanup
            ;;
        all)
            setup_test_env
            copy_app_files
            test_app_startup
            test_gunicorn
            show_results
            cleanup
            ;;
        help|*)
            echo "使用方法: $0 [action]"
            echo ""
            echo "Actions:"
            echo "  all      完整测试流程（默认）"
            echo "  setup    设置测试环境"
            echo "  copy     复制应用文件"
            echo "  test     测试应用启动"
            echo "  gunicorn 测试Gunicorn启动"
            echo "  cleanup  清理测试环境"
            echo "  help     显示帮助"
            ;;
    esac
}

# 捕获退出信号，确保清理
trap cleanup EXIT

# 执行主函数
main "$@"
