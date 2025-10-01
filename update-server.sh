#!/bin/bash

# ============================================
# CRM 项目服务器更新脚本
# ============================================

set -e  # 遇到错误立即退出

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

# 检查是否在项目目录
check_project_dir() {
    if [ ! -f "run.py" ] || [ ! -f "models.py" ]; then
        log_error "请在项目根目录下运行此脚本"
        exit 1
    fi
    log_success "项目目录检查通过"
}

# 检查并安装Docker
check_and_install_docker() {
    log_info "检查Docker环境..."

    # 检查Docker是否已安装
    if command -v docker &> /dev/null; then
        log_success "Docker已安装: $(docker --version)"
    else
        log_info "Docker未安装，开始安装..."

        # 使用阿里云Docker安装脚本
        curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun

        # 启动Docker服务
        sudo systemctl start docker
        sudo systemctl enable docker

        # 将当前用户添加到docker组
        sudo usermod -aG docker $USER

        log_success "Docker安装完成"
    fi

    # 检查Docker Compose是否已安装
    if command -v docker-compose &> /dev/null; then
        log_success "Docker Compose已安装: $(docker-compose --version)"
    elif docker compose version &> /dev/null 2>&1; then
        log_success "Docker Compose (plugin)已安装"
    else
        log_info "Docker Compose未安装，开始安装..."

        # 使用国内镜像下载Docker Compose
        DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
        sudo curl -L "https://get.daocloud.io/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose

        log_success "Docker Compose安装完成"
    fi
}

# 检测部署方式
detect_deployment_type() {
    if docker ps | grep -q crm; then
        DEPLOYMENT_TYPE="docker"
        log_info "检测到 Docker 部署方式"
    elif systemctl is-active --quiet crm 2>/dev/null; then
        DEPLOYMENT_TYPE="systemd"
        log_info "检测到 Systemd 部署方式"
    elif supervisorctl status crm >/dev/null 2>&1; then
        DEPLOYMENT_TYPE="supervisor"
        log_info "检测到 Supervisor 部署方式"
    elif ps aux | grep -v grep | grep -q "python.*run.py"; then
        DEPLOYMENT_TYPE="direct"
        log_info "检测到直接运行方式"
    else
        log_warning "无法检测到运行中的服务，将使用 Docker 方式"
        DEPLOYMENT_TYPE="docker"
    fi
}

# 备份数据库
backup_database() {
    log_info "开始备份数据库..."
    
    BACKUP_DIR="instance"
    BACKUP_FILE="edu_crm_backup_$(date +%Y%m%d_%H%M%S).db"
    
    if [ -f "instance/edu_crm.db" ]; then
        cp instance/edu_crm.db "instance/${BACKUP_FILE}"
        log_success "数据库已备份到: instance/${BACKUP_FILE}"
        
        # 保存备份文件名供回滚使用
        echo "${BACKUP_FILE}" > .last_backup
    else
        log_warning "未找到数据库文件，跳过备份"
    fi
}

# 停止服务
stop_service() {
    log_info "停止服务..."
    
    case $DEPLOYMENT_TYPE in
        docker)
            if command -v docker-compose &> /dev/null; then
                docker-compose down
            else
                docker compose down
            fi
            log_success "Docker 容器已停止"
            ;;
        systemd)
            sudo systemctl stop crm
            log_success "Systemd 服务已停止"
            ;;
        supervisor)
            sudo supervisorctl stop crm
            log_success "Supervisor 服务已停止"
            ;;
        direct)
            PID=$(ps aux | grep -v grep | grep "python.*run.py" | awk '{print $2}')
            if [ -n "$PID" ]; then
                kill -15 $PID
                sleep 2
                log_success "Python 进程已停止 (PID: $PID)"
            fi
            ;;
    esac
}

# 拉取最新代码
pull_code() {
    log_info "拉取最新代码..."
    
    # 保存当前提交哈希供回滚使用
    git rev-parse HEAD > .last_commit
    
    # 检查是否有本地修改
    if ! git diff-index --quiet HEAD --; then
        log_warning "检测到本地修改，将暂存..."
        git stash
        STASHED=true
    fi
    
    # 拉取最新代码
    git pull origin master
    
    log_success "代码已更新到最新版本"
}

# 配置国内镜像源
setup_china_mirrors() {
    log_info "配置国内镜像源..."

    # 配置pip国内镜像源
    if [ ! -d "$HOME/.pip" ]; then
        mkdir -p "$HOME/.pip"
    fi

    cat > "$HOME/.pip/pip.conf" << EOF
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
timeout = 120
EOF

    # 配置Docker Hub国内镜像源
    if [ -f "/etc/docker/daemon.json" ]; then
        log_info "Docker镜像源已配置，跳过"
    else
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

        # 重启Docker服务以应用配置
        if systemctl is-active --quiet docker; then
            sudo systemctl restart docker
            log_success "Docker镜像源配置完成并重启服务"
        else
            log_info "Docker镜像源配置完成，服务启动时生效"
        fi
    fi

    log_success "国内镜像源配置完成"
}

# 更新依赖
update_dependencies() {
    if [ "$DEPLOYMENT_TYPE" != "docker" ]; then
        log_info "检查依赖更新..."

        if [ -d "venv" ]; then
            source venv/bin/activate
            # 使用国内镜像源安装依赖
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
    
    case $DEPLOYMENT_TYPE in
        docker)
            # 重新构建镜像
            if command -v docker-compose &> /dev/null; then
                docker-compose build --no-cache
                docker-compose up -d
            else
                docker compose build --no-cache
                docker compose up -d
            fi
            log_success "Docker 容器已启动"
            ;;
        systemd)
            sudo systemctl start crm
            log_success "Systemd 服务已启动"
            ;;
        supervisor)
            sudo supervisorctl start crm
            log_success "Supervisor 服务已启动"
            ;;
        direct)
            nohup python run.py > logs/app.log 2>&1 &
            log_success "Python 进程已启动"
            ;;
    esac
    
    # 等待服务启动
    sleep 5
}

# 验证服务
verify_service() {
    log_info "验证服务状态..."
    
    # 检查服务是否运行
    case $DEPLOYMENT_TYPE in
        docker)
            if docker ps | grep -q crm; then
                log_success "Docker 容器运行正常"
            else
                log_error "Docker 容器未运行"
                return 1
            fi
            ;;
        systemd)
            if systemctl is-active --quiet crm; then
                log_success "Systemd 服务运行正常"
            else
                log_error "Systemd 服务未运行"
                return 1
            fi
            ;;
        supervisor)
            if supervisorctl status crm | grep -q RUNNING; then
                log_success "Supervisor 服务运行正常"
            else
                log_error "Supervisor 服务未运行"
                return 1
            fi
            ;;
        direct)
            if ps aux | grep -v grep | grep -q "python.*run.py"; then
                log_success "Python 进程运行正常"
            else
                log_error "Python 进程未运行"
                return 1
            fi
            ;;
    esac
    
    # 检查应用响应
    log_info "检查应用响应..."
    sleep 3
    
    if curl -f http://localhost:5000/auth/login > /dev/null 2>&1; then
        log_success "应用响应正常"
    else
        log_warning "应用暂时无响应，请稍后检查"
    fi
}

# 显示日志
show_logs() {
    log_info "最近的应用日志："
    echo "----------------------------------------"
    
    case $DEPLOYMENT_TYPE in
        docker)
            if command -v docker-compose &> /dev/null; then
                docker-compose logs --tail=20 crm-app
            else
                docker compose logs --tail=20 crm-app
            fi
            ;;
        *)
            if [ -f "logs/crm.log" ]; then
                tail -20 logs/crm.log
            else
                log_warning "未找到日志文件"
            fi
            ;;
    esac
    
    echo "----------------------------------------"
}

# 清理旧备份
cleanup_old_backups() {
    log_info "清理7天前的旧备份..."
    
    find instance/ -name "edu_crm_backup_*.db" -mtime +7 -delete 2>/dev/null || true
    
    log_success "旧备份已清理"
}

# 主函数
main() {
    echo ""
    echo "========================================"
    echo "  CRM 项目服务器更新脚本"
    echo "========================================"
    echo ""
    
    # 检查项目目录
    check_project_dir

    # 检查并安装Docker环境
    check_and_install_docker

    # 配置国内镜像源
    setup_china_mirrors

    # 检测部署方式
    detect_deployment_type

    # 确认更新
    echo ""
    read -p "确认要更新项目吗？(y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "更新已取消"
        exit 0
    fi

    # 执行更新步骤
    backup_database
    stop_service
    pull_code
    update_dependencies
    start_service
    
    # 验证服务
    if verify_service; then
        log_success "✅ 更新成功完成！"
        cleanup_old_backups
        show_logs
        
        echo ""
        log_info "更新完成检查清单："
        echo "  - 登录功能"
        echo "  - 线索列表页"
        echo "  - 客户列表页"
        echo "  - 管理员功能"
        echo ""
    else
        log_error "❌ 服务验证失败，请检查日志"
        show_logs
        
        echo ""
        log_warning "如需回滚，请运行: ./rollback-server.sh"
        echo ""
        exit 1
    fi
}

# 运行主函数
main

