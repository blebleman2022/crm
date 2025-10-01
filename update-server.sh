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

    # 检查是否是Git仓库
    if [ ! -d ".git" ]; then
        log_warning "当前目录不是Git仓库，跳过代码更新"
        return 0
    fi

    # 保存当前提交哈希供回滚使用
    git rev-parse HEAD > .last_commit 2>/dev/null || echo "unknown" > .last_commit

    # 检查是否有本地修改
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        log_warning "检测到本地修改，将暂存..."
        git stash push -m "Auto-stash before update $(date)" || {
            log_error "暂存本地修改失败"
            return 1
        }
        STASHED=true
    fi

    # 检查远程仓库连接
    log_info "检查远程仓库连接..."
    if ! git ls-remote --exit-code origin >/dev/null 2>&1; then
        if ! git ls-remote --exit-code github >/dev/null 2>&1; then
            log_error "无法连接到远程仓库，跳过代码更新"
            return 1
        else
            log_info "使用GitHub远程仓库..."
            git pull github master || {
                log_error "从GitHub拉取代码失败"
                return 1
            }
        fi
    else
        log_info "使用origin远程仓库..."
        git pull origin master || {
            log_error "从origin拉取代码失败"
            return 1
        }
    fi

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
            # 检查Docker服务状态
            if ! systemctl is-active --quiet docker; then
                log_info "启动Docker服务..."
                sudo systemctl start docker
                sleep 3
            fi

            # 清理旧容器
            log_info "清理旧容器..."
            if command -v docker-compose &> /dev/null; then
                docker-compose down --remove-orphans 2>/dev/null || true
            else
                docker compose down --remove-orphans 2>/dev/null || true
            fi

            # 构建镜像（带超时和错误处理）
            log_info "构建Docker镜像（最大等待10分钟）..."
            if command -v docker-compose &> /dev/null; then
                timeout 600 docker-compose build --no-cache || {
                    log_error "Docker镜像构建失败或超时"
                    log_info "尝试查看构建日志..."
                    docker-compose logs
                    return 1
                }

                log_info "启动Docker容器..."
                docker-compose up -d || {
                    log_error "Docker容器启动失败"
                    docker-compose logs
                    return 1
                }
            else
                timeout 600 docker compose build --no-cache || {
                    log_error "Docker镜像构建失败或超时"
                    log_info "尝试查看构建日志..."
                    docker compose logs
                    return 1
                }

                log_info "启动Docker容器..."
                docker compose up -d || {
                    log_error "Docker容器启动失败"
                    docker compose logs
                    return 1
                }
            fi

            # 等待容器启动
            log_info "等待容器启动..."
            sleep 10

            log_success "Docker 服务已启动"
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

    # 等待应用启动
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        log_info "尝试连接应用... ($attempt/$max_attempts)"

        if curl -f -s --connect-timeout 5 http://localhost:5000/auth/login > /dev/null 2>&1; then
            log_success "应用响应正常"
            return 0
        fi

        sleep 2
        attempt=$((attempt + 1))
    done

    log_warning "应用在60秒内未响应，可能需要更多时间启动"
    log_info "您可以稍后手动检查: curl http://localhost:5000/auth/login"
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

# 错误恢复函数
handle_error() {
    local error_msg="$1"
    log_error "$error_msg"

    log_info "尝试错误恢复..."

    # 如果有暂存的修改，恢复它们
    if [ "$STASHED" = true ]; then
        log_info "恢复暂存的本地修改..."
        git stash pop 2>/dev/null || log_warning "无法恢复暂存的修改"
    fi

    # 显示有用的调试信息
    log_info "调试信息："
    echo "  - Docker状态: $(systemctl is-active docker 2>/dev/null || echo '未知')"
    echo "  - 容器状态: $(docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null || echo '无法获取')"
    echo "  - 磁盘空间: $(df -h . | tail -1 | awk '{print $4}' 2>/dev/null || echo '无法获取')"
    echo "  - 内存使用: $(free -h | grep Mem | awk '{print $3"/"$2}' 2>/dev/null || echo '无法获取')"

    log_warning "如需回滚，请运行: ./rollback-server.sh"
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

    # 执行更新步骤（带错误处理）
    if ! backup_database; then
        handle_error "数据库备份失败"
        exit 1
    fi

    if ! stop_service; then
        handle_error "停止服务失败"
        exit 1
    fi

    if ! pull_code; then
        handle_error "拉取代码失败"
        exit 1
    fi

    if ! update_dependencies; then
        handle_error "更新依赖失败"
        exit 1
    fi

    if ! start_service; then
        handle_error "启动服务失败"
        exit 1
    fi

    # 验证服务
    if verify_service; then
        log_success "✅ 更新成功完成！"
        cleanup_old_backups
        show_logs

        echo ""
        log_info "更新完成检查清单："
        echo "  - 登录功能: http://localhost:5000/auth/login"
        echo "  - 线索列表页: http://localhost:5000/leads"
        echo "  - 客户列表页: http://localhost:5000/customers"
        echo "  - 管理员功能: http://localhost:5000/admin"
        echo ""
        log_info "默认管理员账号: admin / admin123"
        echo ""
    else
        handle_error "服务验证失败"
        show_logs
        exit 1
    fi
}

# 运行主函数
main

