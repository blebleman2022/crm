#!/bin/bash

# ============================================
# 配置国内镜像源脚本
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

# 配置APT国内镜像源
setup_apt_mirrors() {
    log_info "配置APT国内镜像源..."
    
    # 备份原始源列表
    if [ -f "/etc/apt/sources.list" ] && [ ! -f "/etc/apt/sources.list.backup" ]; then
        sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup
        log_info "已备份原始APT源列表"
    fi
    
    # 检测系统版本
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_ID=$ID
        VERSION_CODENAME=${VERSION_CODENAME:-$(lsb_release -cs 2>/dev/null || echo "unknown")}
    else
        log_warning "无法检测系统版本，使用默认配置"
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
        *)
            log_warning "未知系统类型: $OS_ID，跳过APT源配置"
            return
            ;;
    esac
    
    # 更新包列表
    sudo apt update
    log_success "APT国内镜像源配置完成"
}

# 配置pip国内镜像源
setup_pip_mirrors() {
    log_info "配置pip国内镜像源..."
    
    # 创建pip配置目录
    mkdir -p "$HOME/.pip"
    
    # 配置pip镜像源
    cat > "$HOME/.pip/pip.conf" << EOF
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
timeout = 120

[install]
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF
    
    log_success "pip国内镜像源配置完成"
}

# 配置Docker国内镜像源
setup_docker_mirrors() {
    log_info "配置Docker国内镜像源..."
    
    # 创建Docker配置目录
    sudo mkdir -p /etc/docker
    
    # 配置Docker镜像源
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
    },
    "storage-driver": "overlay2"
}
EOF
    
    # 重启Docker服务
    if systemctl is-active --quiet docker; then
        sudo systemctl restart docker
        log_success "Docker国内镜像源配置完成并重启服务"
    else
        log_info "Docker国内镜像源配置完成，服务启动时生效"
    fi
}

# 配置Git国内镜像源
setup_git_mirrors() {
    log_info "配置Git国内镜像源..."
    
    # 配置GitHub镜像
    git config --global url."https://github.com.cnpmjs.org/".insteadOf "https://github.com/"
    git config --global url."https://hub.fastgit.org/".insteadOf "https://github.com/"
    
    log_success "Git国内镜像源配置完成"
}

# 安装Docker（使用国内镜像）
install_docker_china() {
    log_info "使用国内镜像安装Docker..."
    
    if command -v docker &> /dev/null; then
        log_success "Docker已安装，跳过安装步骤"
        return
    fi
    
    # 使用阿里云Docker安装脚本
    curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
    
    # 启动Docker服务
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # 将当前用户添加到docker组
    sudo usermod -aG docker $USER
    
    log_success "Docker安装完成"
}

# 安装Docker Compose（使用国内镜像）
install_docker_compose_china() {
    log_info "使用国内镜像安装Docker Compose..."
    
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null 2>&1; then
        log_success "Docker Compose已安装，跳过安装步骤"
        return
    fi
    
    # 获取最新版本号
    DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    
    # 使用DaoCloud镜像下载
    sudo curl -L "https://get.daocloud.io/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    log_success "Docker Compose安装完成"
}

# 主函数
main() {
    echo ""
    echo "========================================"
    echo "  国内镜像源配置脚本"
    echo "========================================"
    echo ""
    
    # 确认配置
    read -p "确认要配置国内镜像源吗？(y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "配置已取消"
        exit 0
    fi
    
    # 执行配置步骤
    setup_apt_mirrors
    setup_pip_mirrors
    setup_docker_mirrors
    setup_git_mirrors
    install_docker_china
    install_docker_compose_china
    
    echo ""
    log_success "✅ 国内镜像源配置完成！"
    echo ""
    log_info "配置完成检查清单："
    echo "  - APT镜像源: 阿里云"
    echo "  - pip镜像源: 清华大学"
    echo "  - Docker镜像源: 中科大、网易、百度云、阿里云"
    echo "  - Git镜像源: cnpmjs、fastgit"
    echo ""
    log_warning "注意: 如果配置了Docker镜像源，请重新登录以使docker组权限生效"
    echo ""
}

# 运行主函数
main
