#!/bin/bash

# EduConnect CRM 部署脚本
# 使用方法: ./deploy.sh [环境] [操作]
# 环境: dev, prod
# 操作: build, up, down, restart, logs, backup

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

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    mkdir -p logs backups ssl
    log_success "目录创建完成"
}

# 构建镜像
build_image() {
    log_info "构建 Docker 镜像..."
    docker-compose build --no-cache
    log_success "镜像构建完成"
}

# 启动服务
start_services() {
    local env=${1:-prod}
    log_info "启动服务 (环境: $env)..."
    
    if [ "$env" = "dev" ]; then
        # 开发环境：只启动应用，不启动nginx
        docker-compose up -d crm-app
    else
        # 生产环境：启动所有服务
        docker-compose up -d
    fi
    
    log_success "服务启动完成"
    show_status
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    docker-compose down
    log_success "服务已停止"
}

# 重启服务
restart_services() {
    log_info "重启服务..."
    docker-compose restart
    log_success "服务重启完成"
    show_status
}

# 显示日志
show_logs() {
    local service=${1:-crm-app}
    log_info "显示 $service 服务日志..."
    docker-compose logs -f $service
}

# 显示服务状态
show_status() {
    log_info "服务状态:"
    docker-compose ps
    
    log_info "检查服务健康状态..."
    sleep 5
    
    # 检查应用是否正常运行
    if curl -f http://localhost:5000/auth/login > /dev/null 2>&1; then
        log_success "CRM应用运行正常 - http://localhost:5000"
    else
        log_warning "CRM应用可能未正常启动，请检查日志"
    fi
    
    # 检查Nginx是否运行
    if docker-compose ps nginx | grep -q "Up"; then
        if curl -f http://localhost > /dev/null 2>&1; then
            log_success "Nginx代理运行正常 - http://localhost"
        else
            log_warning "Nginx代理可能未正常启动"
        fi
    fi
}

# 数据库备份
backup_database() {
    log_info "创建数据库备份..."
    
    # 创建备份目录
    mkdir -p backups
    
    # 备份文件名
    backup_file="backups/edu_crm_backup_$(date +%Y%m%d_%H%M%S).db"
    
    # 从容器中复制数据库文件
    docker-compose exec crm-app cp /app/instance/edu_crm.db /tmp/backup.db
    docker cp $(docker-compose ps -q crm-app):/tmp/backup.db $backup_file
    
    log_success "数据库备份完成: $backup_file"
}

# 恢复数据库
restore_database() {
    local backup_file=$1
    
    if [ -z "$backup_file" ]; then
        log_error "请指定备份文件路径"
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        log_error "备份文件不存在: $backup_file"
        exit 1
    fi
    
    log_warning "即将恢复数据库，这将覆盖现有数据！"
    read -p "确认继续？(y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "恢复数据库..."
        
        # 停止服务
        docker-compose stop crm-app
        
        # 复制备份文件到容器
        docker cp $backup_file $(docker-compose ps -q crm-app):/app/instance/edu_crm.db
        
        # 重启服务
        docker-compose start crm-app
        
        log_success "数据库恢复完成"
    else
        log_info "操作已取消"
    fi
}

# 清理资源
cleanup() {
    log_info "清理 Docker 资源..."
    
    # 停止并删除容器
    docker-compose down --volumes --remove-orphans
    
    # 删除镜像
    docker rmi $(docker images -q educonnect-crm_crm-app) 2>/dev/null || true
    
    # 清理未使用的资源
    docker system prune -f
    
    log_success "清理完成"
}

# 显示帮助信息
show_help() {
    echo "EduConnect CRM 部署脚本"
    echo ""
    echo "使用方法:"
    echo "  $0 [环境] [操作] [参数]"
    echo ""
    echo "环境:"
    echo "  dev     开发环境（只启动应用）"
    echo "  prod    生产环境（启动所有服务）"
    echo ""
    echo "操作:"
    echo "  build           构建 Docker 镜像"
    echo "  up              启动服务"
    echo "  down            停止服务"
    echo "  restart         重启服务"
    echo "  logs [service]  显示日志"
    echo "  status          显示服务状态"
    echo "  backup          备份数据库"
    echo "  restore <file>  恢复数据库"
    echo "  cleanup         清理 Docker 资源"
    echo "  help            显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 prod build    # 构建生产环境镜像"
    echo "  $0 prod up       # 启动生产环境"
    echo "  $0 dev up        # 启动开发环境"
    echo "  $0 logs crm-app  # 查看应用日志"
    echo "  $0 backup        # 备份数据库"
}

# 主函数
main() {
    local env=${1:-prod}
    local action=${2:-help}
    local param=$3
    
    # 检查Docker
    check_docker
    
    # 创建目录
    create_directories
    
    case $action in
        build)
            build_image
            ;;
        up)
            start_services $env
            ;;
        down)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        logs)
            show_logs $param
            ;;
        status)
            show_status
            ;;
        backup)
            backup_database
            ;;
        restore)
            restore_database $param
            ;;
        cleanup)
            cleanup
            ;;
        help|*)
            show_help
            ;;
    esac
}

# 执行主函数
main "$@"
