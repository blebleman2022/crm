#!/bin/bash

# 生产环境部署脚本
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
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

# 检查Docker
check_docker() {
    log_info "检查Docker环境..."
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        exit 1
    fi
    
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker服务未运行"
        exit 1
    fi
    
    log_success "Docker环境正常"
}

# 清理旧容器
cleanup_old() {
    log_info "清理旧容器和镜像..."
    
    # 停止并删除旧容器
    docker stop crm-app 2>/dev/null || true
    docker rm crm-app 2>/dev/null || true
    docker stop crm-app-fixed 2>/dev/null || true
    docker rm crm-app-fixed 2>/dev/null || true
    
    # 删除旧镜像（可选）
    # docker rmi crm-app:latest 2>/dev/null || true
    
    log_success "清理完成"
}

# 构建镜像
build_image() {
    log_info "构建Docker镜像..."
    
    # 构建镜像
    docker build -t crm-app:latest . --no-cache
    
    if [ $? -eq 0 ]; then
        log_success "镜像构建成功"
    else
        log_error "镜像构建失败"
        exit 1
    fi
}

# 测试镜像
test_image() {
    log_info "测试镜像..."
    
    # 创建测试容器
    docker run --rm --name crm-test -d -p 8080:80 \
        -e FLASK_ENV=production \
        -e DATABASE_URL=sqlite:///instance/edu_crm.db \
        -e SECRET_KEY=test-secret-key \
        crm-app:latest
    
    # 等待启动
    log_info "等待应用启动..."
    sleep 30
    
    # 测试健康检查
    local health_ok=false
    for i in {1..10}; do
        if curl -f http://localhost:8080/health > /dev/null 2>&1; then
            health_ok=true
            break
        fi
        sleep 3
    done
    
    # 测试登录页面
    local login_ok=false
    if curl -f http://localhost:8080/auth/login > /dev/null 2>&1; then
        login_ok=true
    fi
    
    # 停止测试容器
    docker stop crm-test
    
    if [ "$health_ok" = true ] || [ "$login_ok" = true ]; then
        log_success "镜像测试通过"
    else
        log_error "镜像测试失败"
        exit 1
    fi
}

# 部署生产容器
deploy_production() {
    log_info "部署生产容器..."
    
    # 创建数据目录
    sudo mkdir -p /var/lib/crm/instance
    sudo mkdir -p /var/lib/crm/logs
    sudo chmod 755 /var/lib/crm/instance /var/lib/crm/logs
    
    # 启动生产容器
    docker run -d \
        --name crm-app \
        --restart unless-stopped \
        -p 80:80 \
        -e FLASK_ENV=production \
        -e DATABASE_URL=sqlite:///instance/edu_crm.db \
        -e SECRET_KEY=crm-production-secret-$(date +%s) \
        -v /var/lib/crm/instance:/app/instance \
        -v /var/lib/crm/logs:/app/logs \
        crm-app:latest
    
    if [ $? -eq 0 ]; then
        log_success "生产容器启动成功"
    else
        log_error "生产容器启动失败"
        exit 1
    fi
}

# 验证部署
verify_deployment() {
    log_info "验证部署..."
    
    # 等待启动
    log_info "等待应用完全启动..."
    sleep 60
    
    # 检查容器状态
    if docker ps | grep crm-app > /dev/null; then
        log_success "容器运行正常"
    else
        log_error "容器未运行"
        docker logs crm-app
        exit 1
    fi
    
    # 测试访问
    local test_passed=false
    
    # 测试健康检查
    if curl -f http://localhost/health > /dev/null 2>&1; then
        log_success "健康检查通过"
        test_passed=true
    fi
    
    # 测试登录页面
    if curl -f http://localhost/auth/login > /dev/null 2>&1; then
        log_success "登录页面可访问"
        test_passed=true
    fi
    
    # 测试根路径
    if curl -I http://localhost/ 2>&1 | grep -E "302|200" > /dev/null; then
        log_success "根路径重定向正常"
        test_passed=true
    fi
    
    if [ "$test_passed" = true ]; then
        log_success "部署验证通过"
        log_info "🎉 应用已成功部署！"
        log_info "🌐 访问地址: http://$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP')"
        log_info "📊 管理后台: http://$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP')/admin"
    else
        log_error "部署验证失败"
        log_info "查看容器日志:"
        docker logs crm-app | tail -50
        exit 1
    fi
}

# 显示管理命令
show_management_commands() {
    log_info "管理命令:"
    echo "  查看日志: docker logs -f crm-app"
    echo "  重启应用: docker restart crm-app"
    echo "  停止应用: docker stop crm-app"
    echo "  进入容器: docker exec -it crm-app bash"
    echo "  查看状态: docker ps | grep crm-app"
}

# 主函数
main() {
    echo "🚀 开始生产环境部署..."
    echo "================================"
    
    check_docker
    cleanup_old
    build_image
    test_image
    deploy_production
    verify_deployment
    show_management_commands
    
    echo "================================"
    log_success "部署完成！"
}

# 执行主函数
main "$@"
