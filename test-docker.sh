#!/bin/bash

# 本地Docker测试脚本 - 模拟Dokploy环境
set -e

echo "🐳 本地Docker环境测试脚本"
echo "================================"

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

# 检查Docker是否运行
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker未运行，请启动Docker Desktop"
        exit 1
    fi
    log_success "Docker运行正常"
}

# 清理旧容器和镜像
cleanup() {
    log_info "清理旧的测试容器和镜像..."
    
    # 停止并删除容器
    docker stop crm-test 2>/dev/null || true
    docker rm crm-test 2>/dev/null || true
    
    # 删除镜像
    docker rmi crm-test-image 2>/dev/null || true
    
    log_success "清理完成"
}

# 构建镜像
build_image() {
    log_info "构建Docker镜像..."
    
    # 强制重新构建，不使用缓存
    docker build --no-cache -t crm-test-image .
    
    if [ $? -eq 0 ]; then
        log_success "镜像构建成功"
    else
        log_error "镜像构建失败"
        exit 1
    fi
}

# 运行容器
run_container() {
    log_info "启动测试容器..."
    
    # 创建数据目录
    mkdir -p ./test-data/instance
    mkdir -p ./test-data/logs
    
    # 运行容器
    docker run -d \
        --name crm-test \
        -p 8080:80 \
        -e FLASK_ENV=production \
        -e DATABASE_URL=sqlite:///instance/edu_crm.db \
        -v "$(pwd)/test-data/instance:/app/instance" \
        -v "$(pwd)/test-data/logs:/app/logs" \
        crm-test-image
    
    if [ $? -eq 0 ]; then
        log_success "容器启动成功"
        log_info "应用地址: http://localhost:8080"
    else
        log_error "容器启动失败"
        exit 1
    fi
}

# 查看日志
show_logs() {
    log_info "显示容器日志..."
    echo "================================"
    docker logs -f crm-test
}

# 测试应用
test_app() {
    log_info "等待应用启动..."
    sleep 10
    
    log_info "测试应用健康状态..."
    
    # 测试健康检查端点
    if curl -f http://localhost:8080/health > /dev/null 2>&1; then
        log_success "健康检查通过"
    else
        log_warning "健康检查失败，尝试测试登录页面..."
        
        # 测试登录页面
        if curl -f http://localhost:8080/auth/login > /dev/null 2>&1; then
            log_success "登录页面访问正常"
        else
            log_error "应用无法访问"
            log_info "查看容器日志："
            docker logs crm-test
            return 1
        fi
    fi
    
    log_success "应用测试通过！"
    log_info "🌐 访问地址: http://localhost:8080"
    log_info "📊 查看日志: docker logs -f crm-test"
    log_info "🛑 停止测试: docker stop crm-test"
}

# 主函数
main() {
    local action=${1:-all}
    
    case $action in
        cleanup)
            cleanup
            ;;
        build)
            check_docker
            cleanup
            build_image
            ;;
        run)
            check_docker
            run_container
            ;;
        test)
            test_app
            ;;
        logs)
            show_logs
            ;;
        all)
            check_docker
            cleanup
            build_image
            run_container
            test_app
            ;;
        help|*)
            echo "使用方法: $0 [action]"
            echo ""
            echo "Actions:"
            echo "  all      完整测试流程（默认）"
            echo "  cleanup  清理旧容器和镜像"
            echo "  build    构建镜像"
            echo "  run      运行容器"
            echo "  test     测试应用"
            echo "  logs     查看日志"
            echo "  help     显示帮助"
            ;;
    esac
}

# 执行主函数
main "$@"
