#!/bin/bash

# ============================================
# CRM 系统一键部署脚本（简化版）
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

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查基本环境
check_environment() {
    log_info "检查基本环境..."

    if [ ! -f "run.py" ] || [ ! -f "models.py" ]; then
        log_error "请在项目根目录下运行此脚本"
        exit 1
    fi

    if [ ! -f "docker-compose.yml" ]; then
        log_error "未找到docker-compose.yml文件"
        exit 1
    fi

    log_success "环境检查通过"
}

# 检查Docker环境
check_docker() {
    log_info "检查Docker环境..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        log_info "安装命令: curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
        log_error "Docker Compose未安装"
        exit 1
    fi

    if ! systemctl is-active --quiet docker; then
        log_info "启动Docker服务..."
        sudo systemctl start docker
    fi

    log_success "Docker环境正常"
}

# 配置国内镜像源
setup_mirrors() {
    log_info "配置国内镜像源..."

    # 配置pip镜像源
    mkdir -p ~/.pip
    cat > ~/.pip/pip.conf << EOF
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
timeout = 120
EOF

    # 配置Docker镜像源
    if [ ! -f "/etc/docker/daemon.json" ]; then
        sudo mkdir -p /etc/docker
        sudo tee /etc/docker/daemon.json > /dev/null << EOF
{
    "registry-mirrors": [
        "https://docker.mirrors.ustc.edu.cn",
        "https://hub-mirror.c.163.com",
        "https://mirror.baidubce.com"
    ]
}
EOF
        sudo systemctl restart docker
        sleep 3
        log_success "Docker镜像源配置完成"
    fi

    log_success "镜像源配置完成"
}

# 备份数据库
backup_database() {
    log_info "备份数据库..."

    mkdir -p instance
    if [ -f "instance/edu_crm.db" ]; then
        BACKUP_FILE="edu_crm_backup_$(date +%Y%m%d_%H%M%S).db"
        cp instance/edu_crm.db "instance/${BACKUP_FILE}"
        log_success "数据库已备份到: instance/${BACKUP_FILE}"
    else
        log_info "未找到数据库文件，跳过备份"
    fi
}

# 部署应用
deploy_app() {
    log_info "部署CRM应用..."

    # 创建必要目录
    mkdir -p instance logs backups

    # 停止现有服务
    log_info "停止现有服务..."
    docker-compose down --remove-orphans 2>/dev/null || true

    # 清理Docker缓存
    log_info "清理Docker缓存..."
    docker system prune -f 2>/dev/null || true

    # 构建并启动服务
    log_info "构建并启动服务..."
    if command -v docker-compose &> /dev/null; then
        docker-compose build --no-cache
        docker-compose up -d
    else
        docker compose build --no-cache
        docker compose up -d
    fi

    log_success "应用部署完成"
}

# 验证部署
verify_deployment() {
    log_info "验证部署状态..."

    # 等待服务启动
    sleep 10

    # 检查容器状态
    log_info "检查容器状态..."
    if command -v docker-compose &> /dev/null; then
        docker-compose ps
    else
        docker compose ps
    fi

    # 检查应用响应
    log_info "检查应用响应..."
    local max_attempts=15
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s --connect-timeout 5 http://localhost:5000/auth/login > /dev/null 2>&1; then
            log_success "应用响应正常！"
            return 0
        fi

        log_info "等待应用启动... ($attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done

    log_warning "应用可能需要更多时间启动"
    return 1
}

# 显示部署信息
show_deployment_info() {
    echo ""
    echo "========================================"
    echo "  🎉 CRM系统部署完成！"
    echo "========================================"
    echo ""
    echo "📋 访问信息："
    echo "  - 系统地址: http://localhost:5000"
    echo "  - 登录页面: http://localhost:5000/auth/login"
    echo ""
    echo "🔑 默认管理员账号："
    echo "  - 用户名: admin"
    echo "  - 密码: admin123"
    echo ""
    echo "🛠️ 常用命令："
    echo "  - 查看日志: docker-compose logs -f"
    echo "  - 重启服务: docker-compose restart"
    echo "  - 停止服务: docker-compose down"
    echo ""
    echo "📁 重要目录："
    echo "  - 数据库: instance/edu_crm.db"
    echo "  - 日志: logs/"
    echo "  - 备份: instance/"
    echo ""
}

# 主函数
main() {
    echo ""
    echo "========================================"
    echo "  CRM 系统一键部署脚本（简化版）"
    echo "========================================"
    echo ""

    # 确认部署
    read -p "确认要部署CRM系统吗？(y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "部署已取消"
        exit 0
    fi

    # 执行部署步骤
    check_environment
    check_docker
    setup_mirrors
    backup_database
    deploy_app

    # 验证部署
    if verify_deployment; then
        show_deployment_info
    else
        echo ""
        log_warning "部署可能未完全成功，请检查："
        echo "  1. 查看日志: docker-compose logs"
        echo "  2. 检查状态: docker-compose ps"
        echo "  3. 手动测试: curl http://localhost:5000/auth/login"
        echo ""
    fi
}

# 运行主函数
main
