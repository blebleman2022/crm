#!/bin/bash

# Docker Compose 部署脚本
set -e

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

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查环境
check_environment() {
    log_info "检查部署环境..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装"
        exit 1
    fi
    
    # 检查数据库文件
    if [ ! -f "./instance/edu_crm.db" ]; then
        log_warning "数据库文件不存在，将在启动时创建"
    else
        log_success "找到数据库文件: ./instance/edu_crm.db"
        ls -la ./instance/edu_crm.db
    fi
    
    log_success "环境检查完成"
}

# 准备环境文件
prepare_env() {
    log_info "准备环境配置..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.production" ]; then
            cp .env.production .env
            log_info "已复制 .env.production 为 .env"
        else
            log_warning "未找到环境配置文件，使用默认配置"
        fi
    fi
    
    # 生成随机密钥
    if [ -f ".env" ]; then
        if grep -q "your-super-secret-key-change-this-in-production" .env; then
            local secret_key=$(openssl rand -hex 32 2>/dev/null || date +%s | sha256sum | head -c 64)
            sed -i.bak "s/your-super-secret-key-change-this-in-production/$secret_key/" .env
            log_info "已生成新的SECRET_KEY"
        fi
    fi
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    mkdir -p instance logs
    chmod 755 instance logs
    
    log_success "目录创建完成"
}

# 停止现有服务
stop_existing() {
    log_info "停止现有服务..."
    
    # 停止Docker Compose服务
    docker-compose down 2>/dev/null || true
    
    # 停止单独运行的容器
    docker stop crm-app crm-production 2>/dev/null || true
    docker rm crm-app crm-production 2>/dev/null || true
    
    log_success "现有服务已停止"
}

# 构建和启动服务
start_services() {
    local compose_file=${1:-docker-compose.yml}
    
    log_info "使用 $compose_file 启动服务..."
    
    # 构建镜像
    docker-compose -f $compose_file build --no-cache
    
    # 启动服务
    docker-compose -f $compose_file up -d
    
    log_success "服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待服务就绪..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps | grep "Up" > /dev/null; then
            log_success "服务已启动"
            break
        fi
        
        log_info "等待服务启动... ($attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "服务启动超时"
        return 1
    fi
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    local max_attempts=20
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        # 检查健康端点
        if curl -f http://localhost/health > /dev/null 2>&1; then
            log_success "✅ 健康检查通过"
            return 0
        fi
        
        # 检查登录页面
        if curl -f http://localhost/auth/login > /dev/null 2>&1; then
            log_success "✅ 登录页面可访问"
            return 0
        fi
        
        log_info "健康检查... ($attempt/$max_attempts)"
        sleep 3
        ((attempt++))
    done
    
    log_warning "健康检查失败，但服务可能仍在启动中"
    return 1
}

# 显示服务状态
show_status() {
    log_info "服务状态:"
    echo "================================"
    
    # 显示容器状态
    docker-compose ps
    
    echo ""
    log_info "应用信息:"
    echo "  🌐 访问地址: http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_SERVER_IP')"
    echo "  📊 本地访问: http://localhost"
    echo "  📝 查看日志: docker-compose logs -f"
    echo "  🛑 停止服务: docker-compose down"
    echo "  🔄 重启服务: docker-compose restart"
    
    echo ""
    log_info "数据库信息:"
    if [ -f "./instance/edu_crm.db" ]; then
        echo "  📄 数据库文件: ./instance/edu_crm.db"
        echo "  📊 文件大小: $(ls -lh ./instance/edu_crm.db | awk '{print $5}')"
    fi
    
    echo "================================"
}

# 显示日志
show_logs() {
    log_info "显示应用日志..."
    docker-compose logs -f crm-app
}

# 主函数
main() {
    local action=${1:-deploy}
    
    case $action in
        deploy)
            echo "🚀 开始Docker Compose部署..."
            check_environment
            prepare_env
            create_directories
            stop_existing
            start_services
            wait_for_services
            health_check
            show_status
            ;;
        start)
            log_info "启动服务..."
            docker-compose up -d
            wait_for_services
            show_status
            ;;
        stop)
            log_info "停止服务..."
            docker-compose down
            ;;
        restart)
            log_info "重启服务..."
            docker-compose restart
            show_status
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        clean)
            log_info "清理服务和镜像..."
            docker-compose down --rmi all --volumes
            ;;
        help|*)
            echo "使用方法: $0 [action]"
            echo ""
            echo "Actions:"
            echo "  deploy   完整部署流程（默认）"
            echo "  start    启动服务"
            echo "  stop     停止服务"
            echo "  restart  重启服务"
            echo "  logs     查看日志"
            echo "  status   显示状态"
            echo "  clean    清理服务和镜像"
            echo "  help     显示帮助"
            ;;
    esac
}

# 执行主函数
main "$@"
