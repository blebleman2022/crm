#!/bin/bash

# ============================================
# CRM 系统一键部署脚本
# ============================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 全局变量
DEPLOYMENT_TYPE=""
STASHED=false

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
    
    # 检查是否在项目目录
    if [ ! -f "run.py" ] || [ ! -f "models.py" ]; then
        log_error "请在项目根目录下运行此脚本"
        exit 1
    fi
    
    log_success "项目目录检查通过"
}

# 检测部署方式
detect_deployment_type() {
    log_info "检测部署方式..."
    
    if [ -f "docker-compose.yml" ]; then
        DEPLOYMENT_TYPE="docker"
        log_info "检测到 Docker Compose 配置，使用 Docker 部署"
    elif systemctl list-unit-files | grep -q "crm.service"; then
        DEPLOYMENT_TYPE="systemd"
        log_info "检测到 Systemd 服务，使用 Systemd 部署"
    elif command -v supervisorctl &> /dev/null && supervisorctl status | grep -q crm; then
        DEPLOYMENT_TYPE="supervisor"
        log_info "检测到 Supervisor 配置，使用 Supervisor 部署"
    else
        DEPLOYMENT_TYPE="direct"
        log_info "使用直接运行方式部署"
    fi
}

# 检查并安装Docker
check_and_install_docker() {
    if [ "$DEPLOYMENT_TYPE" != "docker" ]; then
        return 0
    fi
    
    log_info "检查Docker环境..."
    
    # 检查Docker是否已安装
    if ! command -v docker &> /dev/null; then
        log_info "Docker未安装，开始安装..."
        curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -aG docker $USER
        log_success "Docker安装完成"
    else
        log_success "Docker已安装: $(docker --version)"
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
        log_info "Docker Compose未安装，开始安装..."
        DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
        sudo curl -L "https://get.daocloud.io/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        log_success "Docker Compose安装完成"
    else
        log_success "Docker Compose已安装"
    fi
}

# 配置国内镜像源
setup_china_mirrors() {
    log_info "配置国内镜像源..."
    
    # 配置APT国内镜像源
    if [ -f "/etc/apt/sources.list" ] && [ ! -f "/etc/apt/sources.list.backup" ]; then
        log_info "配置APT国内镜像源..."
        sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup
        
        # 检测系统版本
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS_ID=$ID
            VERSION_CODENAME=${VERSION_CODENAME:-$(lsb_release -cs 2>/dev/null || echo "bullseye")}
        else
            OS_ID="debian"
            VERSION_CODENAME="bullseye"
        fi
        
        case $OS_ID in
            "debian")
                log_info "检测到Debian系统，版本: $VERSION_CODENAME"
                sudo tee /etc/apt/sources.list > /dev/null <<EOF
# 阿里云Debian镜像源
deb https://mirrors.aliyun.com/debian/ $VERSION_CODENAME main contrib non-free
deb-src https://mirrors.aliyun.com/debian/ $VERSION_CODENAME main contrib non-free

deb https://mirrors.aliyun.com/debian-security/ $VERSION_CODENAME-security main contrib non-free
deb-src https://mirrors.aliyun.com/debian-security/ $VERSION_CODENAME-security main contrib non-free

deb https://mirrors.aliyun.com/debian/ $VERSION_CODENAME-updates main contrib non-free
deb-src https://mirrors.aliyun.com/debian/ $VERSION_CODENAME-updates main contrib non-free
EOF
                ;;
            "ubuntu")
                log_info "检测到Ubuntu系统，版本: $VERSION_CODENAME"
                sudo tee /etc/apt/sources.list > /dev/null <<EOF
# 阿里云Ubuntu镜像源
deb https://mirrors.aliyun.com/ubuntu/ $VERSION_CODENAME main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ $VERSION_CODENAME main restricted universe multiverse

deb https://mirrors.aliyun.com/ubuntu/ $VERSION_CODENAME-security main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ $VERSION_CODENAME-security main restricted universe multiverse

deb https://mirrors.aliyun.com/ubuntu/ $VERSION_CODENAME-updates main restricted universe multiverse
deb-src https://mirrors.aliyun.com/ubuntu/ $VERSION_CODENAME-updates main restricted universe multiverse
EOF
                ;;
        esac
        
        # 更新包列表
        sudo apt update
        log_success "APT国内镜像源配置完成"
    else
        log_info "APT镜像源已配置或无需配置"
    fi
    
    # 配置pip镜像源
    mkdir -p ~/.pip
    cat > ~/.pip/pip.conf << EOF
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
timeout = 120
EOF
    
    # 配置Docker镜像源
    if [ "$DEPLOYMENT_TYPE" = "docker" ] && [ ! -f "/etc/docker/daemon.json" ]; then
        sudo mkdir -p /etc/docker
        sudo tee /etc/docker/daemon.json > /dev/null << EOF
{
    "registry-mirrors": [
        "https://docker.mirrors.ustc.edu.cn",
        "https://hub-mirror.c.163.com",
        "https://mirror.baidubce.com"
    ],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
EOF
        sudo systemctl restart docker
        log_success "Docker镜像源配置完成"
    fi
    
    log_success "国内镜像源配置完成"
}

# 备份数据库
backup_database() {
    log_info "备份数据库..."
    
    if [ -f "instance/edu_crm.db" ]; then
        BACKUP_FILE="edu_crm_backup_$(date +%Y%m%d_%H%M%S).db"
        cp instance/edu_crm.db "instance/${BACKUP_FILE}"
        log_success "数据库已备份到: instance/${BACKUP_FILE}"
        echo "${BACKUP_FILE}" > .last_backup
    else
        log_warning "未找到数据库文件，跳过备份"
    fi
}

# 拉取最新代码
pull_code() {
    if [ ! -d ".git" ]; then
        log_warning "当前目录不是Git仓库，跳过代码更新"
        return 0
    fi
    
    log_info "拉取最新代码..."
    
    # 保存当前提交哈希
    git rev-parse HEAD > .last_commit 2>/dev/null || echo "unknown" > .last_commit
    
    # 检查本地修改
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        log_warning "检测到本地修改，将暂存..."
        git stash push -m "Auto-stash before deploy $(date)" || {
            log_error "暂存本地修改失败"
            return 1
        }
        STASHED=true
    fi
    
    # 拉取代码
    if ! git ls-remote --exit-code origin >/dev/null 2>&1; then
        if ! git ls-remote --exit-code github >/dev/null 2>&1; then
            log_warning "无法连接到远程仓库，跳过代码更新"
            return 0
        else
            git pull github master || log_warning "代码拉取失败，继续使用本地代码"
        fi
    else
        git pull origin master || log_warning "代码拉取失败，继续使用本地代码"
    fi
    
    log_success "代码更新完成"
}

# 停止服务
stop_service() {
    log_info "停止现有服务..."
    
    case $DEPLOYMENT_TYPE in
        docker)
            if command -v docker-compose &> /dev/null; then
                docker-compose down 2>/dev/null || true
            else
                docker compose down 2>/dev/null || true
            fi
            ;;
        systemd)
            sudo systemctl stop crm 2>/dev/null || true
            ;;
        supervisor)
            sudo supervisorctl stop crm 2>/dev/null || true
            ;;
        direct)
            if [ -f ".app_pid" ]; then
                kill $(cat .app_pid) 2>/dev/null || true
                rm -f .app_pid
            fi
            ;;
    esac
    
    log_success "服务已停止"
}

# 更新依赖
update_dependencies() {
    if [ "$DEPLOYMENT_TYPE" != "docker" ]; then
        log_info "更新Python依赖..."
        
        if [ -d "venv" ]; then
            source venv/bin/activate
            pip install -r requirements.txt --upgrade \
                -i https://pypi.tuna.tsinghua.edu.cn/simple \
                --trusted-host pypi.tuna.tsinghua.edu.cn
            log_success "依赖已更新"
        else
            log_warning "未找到虚拟环境，跳过依赖更新"
        fi
    fi
}

# 启动服务
start_service() {
    log_info "启动服务..."
    
    # 创建必要目录
    mkdir -p instance logs backups
    
    case $DEPLOYMENT_TYPE in
        docker)
            # 确保Docker服务运行
            if ! systemctl is-active --quiet docker; then
                sudo systemctl start docker
                sleep 3
            fi
            
            # 构建并启动
            log_info "构建Docker镜像（最大等待10分钟）..."
            if command -v docker-compose &> /dev/null; then
                timeout 600 docker-compose build --no-cache || {
                    log_error "Docker镜像构建失败"
                    return 1
                }
                docker-compose up -d || {
                    log_error "Docker容器启动失败"
                    return 1
                }
            else
                timeout 600 docker compose build --no-cache || {
                    log_error "Docker镜像构建失败"
                    return 1
                }
                docker compose up -d || {
                    log_error "Docker容器启动失败"
                    return 1
                }
            fi
            ;;
        systemd)
            sudo systemctl start crm
            ;;
        supervisor)
            sudo supervisorctl start crm
            ;;
        direct)
            nohup python run.py > logs/app.log 2>&1 &
            echo $! > .app_pid
            ;;
    esac
    
    log_success "服务已启动"
}

# 验证部署
verify_deployment() {
    log_info "验证部署状态..."

    # 等待服务启动
    sleep 10

    # 检查服务状态
    case $DEPLOYMENT_TYPE in
        docker)
            if command -v docker-compose &> /dev/null; then
                docker-compose ps
            else
                docker compose ps
            fi
            ;;
    esac

    # 检查应用响应
    log_info "检查应用响应..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        log_info "尝试连接应用... ($attempt/$max_attempts)"

        if curl -f -s --connect-timeout 5 http://localhost:5000/auth/login > /dev/null 2>&1; then
            log_success "应用响应正常！"
            return 0
        fi

        sleep 2
        attempt=$((attempt + 1))
    done

    log_warning "应用在60秒内未响应，可能需要更多时间启动"
    return 1
}

# 错误处理
handle_error() {
    local error_msg="$1"
    log_error "$error_msg"

    # 恢复暂存的修改
    if [ "$STASHED" = true ]; then
        log_info "恢复暂存的本地修改..."
        git stash pop 2>/dev/null || log_warning "无法恢复暂存的修改"
    fi

    # 显示调试信息
    log_info "调试信息："
    echo "  - Docker状态: $(systemctl is-active docker 2>/dev/null || echo '未知')"
    echo "  - 容器状态: $(docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null || echo '无法获取')"
    echo "  - 磁盘空间: $(df -h . | tail -1 | awk '{print $4}' 2>/dev/null || echo '无法获取')"

    log_warning "如需回滚，请运行: ./rollback-server.sh"
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
    if [ "$DEPLOYMENT_TYPE" = "docker" ]; then
        echo "  - 查看日志: docker-compose logs -f"
        echo "  - 重启服务: docker-compose restart"
        echo "  - 停止服务: docker-compose down"
    else
        echo "  - 查看日志: tail -f logs/app.log"
        echo "  - 重启服务: ./deploy.sh"
    fi
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
    echo "  CRM 系统一键部署脚本"
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
    if ! check_environment; then
        handle_error "环境检查失败"
        exit 1
    fi

    detect_deployment_type

    if ! check_and_install_docker; then
        handle_error "Docker环境配置失败"
        exit 1
    fi

    if ! setup_china_mirrors; then
        handle_error "镜像源配置失败"
        exit 1
    fi

    if ! backup_database; then
        handle_error "数据库备份失败"
        exit 1
    fi

    if ! stop_service; then
        handle_error "停止服务失败"
        exit 1
    fi

    if ! pull_code; then
        handle_error "代码更新失败"
        exit 1
    fi

    if ! update_dependencies; then
        handle_error "依赖更新失败"
        exit 1
    fi

    if ! start_service; then
        handle_error "启动服务失败"
        exit 1
    fi

    # 验证部署
    if verify_deployment; then
        show_deployment_info
    else
        log_warning "部署可能未完全成功，请检查："
        echo "  1. 运行: docker-compose logs"
        echo "  2. 检查: curl http://localhost:5000/auth/login"
        echo ""
    fi
}

# 运行主函数
main
