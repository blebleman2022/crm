#!/bin/bash

# 简单的Gunicorn测试脚本 - 使用现有环境
set -e

echo "🚀 Gunicorn本地测试"
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

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查Python
    if ! command -v python &> /dev/null; then
        log_error "Python未安装"
        exit 1
    fi
    
    # 检查Gunicorn
    if ! python -c "import gunicorn" 2>/dev/null; then
        log_error "Gunicorn未安装，请运行: pip install gunicorn"
        exit 1
    fi
    
    # 检查Flask
    if ! python -c "import flask" 2>/dev/null; then
        log_error "Flask未安装，请运行: pip install flask"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# 测试应用导入
test_import() {
    log_info "测试应用导入..."
    
    python -c "
import sys
sys.path.insert(0, '.')

try:
    from run import app
    print('✅ 成功导入 run.app')
    print(f'✅ app 类型: {type(app)}')
    print(f'✅ app 名称: {app.name}')
    
    # 测试应用上下文
    with app.app_context():
        print('✅ 应用上下文正常')
        
    print('🎉 应用导入测试通过！')
except Exception as e:
    print(f'❌ 应用导入失败: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_success "应用导入测试通过"
    else
        log_error "应用导入测试失败"
        exit 1
    fi
}

# 启动Gunicorn测试
start_gunicorn() {
    log_info "启动Gunicorn测试服务器..."
    
    # 设置环境变量
    export FLASK_ENV=production
    export DATABASE_URL=sqlite:///instance/edu_crm.db
    export SECRET_KEY=test-gunicorn-secret
    
    # 创建必要目录
    mkdir -p instance logs
    
    # 启动Gunicorn（后台运行）
    log_info "启动Gunicorn (端口8084)..."
    gunicorn --bind 127.0.0.1:8084 \
             --workers 1 \
             --timeout 30 \
             --daemon \
             --pid gunicorn-test.pid \
             --access-logfile logs/gunicorn-access.log \
             --error-logfile logs/gunicorn-error.log \
             run:app
    
    if [ $? -eq 0 ]; then
        log_success "Gunicorn启动成功"
    else
        log_error "Gunicorn启动失败"
        exit 1
    fi
}

# 测试服务器响应
test_server() {
    log_info "等待服务器启动..."
    sleep 5
    
    log_info "测试服务器响应..."
    
    # 测试健康检查
    if curl -f http://127.0.0.1:8084/health > /dev/null 2>&1; then
        log_success "✅ 健康检查端点正常"
        curl -s http://127.0.0.1:8084/health | python -m json.tool
    else
        log_warning "健康检查失败，尝试测试登录页面..."
        
        # 测试登录页面
        if curl -f http://127.0.0.1:8084/auth/login > /dev/null 2>&1; then
            log_success "✅ 登录页面可访问"
        else
            log_error "❌ 服务器无法访问"
            show_logs
            return 1
        fi
    fi
    
    # 测试主页重定向
    log_info "测试主页重定向..."
    response_code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8084/)
    if [ "$response_code" = "302" ] || [ "$response_code" = "200" ]; then
        log_success "✅ 主页响应正常 (HTTP $response_code)"
    else
        log_warning "主页响应异常 (HTTP $response_code)"
    fi
    
    log_success "🎉 服务器测试通过！"
    log_info "🌐 访问地址: http://127.0.0.1:8084"
}

# 显示日志
show_logs() {
    log_info "显示Gunicorn日志..."
    
    if [ -f logs/gunicorn-error.log ]; then
        echo "=== 错误日志 ==="
        tail -20 logs/gunicorn-error.log
    fi
    
    if [ -f logs/gunicorn-access.log ]; then
        echo "=== 访问日志 ==="
        tail -10 logs/gunicorn-access.log
    fi
}

# 停止服务器
stop_server() {
    log_info "停止Gunicorn服务器..."
    
    if [ -f gunicorn-test.pid ]; then
        local pid=$(cat gunicorn-test.pid)
        if ps -p $pid > /dev/null; then
            kill $pid
            log_success "Gunicorn服务器已停止"
        else
            log_warning "Gunicorn进程不存在"
        fi
        rm -f gunicorn-test.pid
    else
        log_warning "PID文件不存在"
    fi
}

# 清理
cleanup() {
    stop_server
    rm -f gunicorn-test.pid
}

# 显示测试结果
show_results() {
    log_info "测试总结"
    echo "================================"
    log_success "✅ 依赖检查通过"
    log_success "✅ 应用导入通过"
    log_success "✅ Gunicorn启动通过"
    log_success "✅ 服务器响应通过"
    echo ""
    log_info "🎉 所有测试通过！应用可以正常使用Gunicorn部署。"
    echo ""
    log_info "📝 测试信息："
    echo "  - 测试端口: 8084"
    echo "  - 访问地址: http://127.0.0.1:8084"
    echo "  - 日志文件: logs/gunicorn-*.log"
    echo "  - PID文件: gunicorn-test.pid"
}

# 主函数
main() {
    local action=${1:-all}
    
    case $action in
        check)
            check_dependencies
            ;;
        import)
            test_import
            ;;
        start)
            start_gunicorn
            ;;
        test)
            test_server
            ;;
        logs)
            show_logs
            ;;
        stop)
            stop_server
            ;;
        all)
            check_dependencies
            test_import
            start_gunicorn
            test_server
            show_results
            
            # 询问是否保持运行
            echo ""
            read -p "是否保持服务器运行以便手动测试？(y/N): " -n 1 -r
            echo
            
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                cleanup
            else
                log_info "服务器继续运行，使用以下命令管理："
                echo "  查看日志: ./test-gunicorn.sh logs"
                echo "  停止服务: ./test-gunicorn.sh stop"
            fi
            ;;
        help|*)
            echo "使用方法: $0 [action]"
            echo ""
            echo "Actions:"
            echo "  all      完整测试流程（默认）"
            echo "  check    检查依赖"
            echo "  import   测试应用导入"
            echo "  start    启动Gunicorn"
            echo "  test     测试服务器响应"
            echo "  logs     显示日志"
            echo "  stop     停止服务器"
            echo "  help     显示帮助"
            ;;
    esac
}

# 捕获退出信号，确保清理
trap cleanup EXIT

# 执行主函数
main "$@"
