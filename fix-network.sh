#!/bin/bash

# ============================================
# 网络问题修复脚本
# ============================================

set -e

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

# 修复APT源网络问题
fix_apt_sources() {
    log_info "修复APT源网络问题..."
    
    # 备份原始源
    if [ -f "/etc/apt/sources.list" ] && [ ! -f "/etc/apt/sources.list.backup" ]; then
        sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup
    fi
    
    # 检测系统版本
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_ID=$ID
        VERSION_CODENAME=${VERSION_CODENAME:-$(lsb_release -cs 2>/dev/null || echo "bullseye")}
    else
        OS_ID="debian"
        VERSION_CODENAME="bullseye"
    fi
    
    # 配置国内源
    case $OS_ID in
        "debian")
            log_info "配置Debian国内源..."
            sudo tee /etc/apt/sources.list > /dev/null <<EOF
# 阿里云Debian镜像源
deb https://mirrors.aliyun.com/debian/ $VERSION_CODENAME main contrib non-free
deb https://mirrors.aliyun.com/debian-security/ $VERSION_CODENAME-security main contrib non-free
deb https://mirrors.aliyun.com/debian/ $VERSION_CODENAME-updates main contrib non-free
EOF
            ;;
        "ubuntu")
            log_info "配置Ubuntu国内源..."
            sudo tee /etc/apt/sources.list > /dev/null <<EOF
# 阿里云Ubuntu镜像源
deb https://mirrors.aliyun.com/ubuntu/ $VERSION_CODENAME main restricted universe multiverse
deb https://mirrors.aliyun.com/ubuntu/ $VERSION_CODENAME-security main restricted universe multiverse
deb https://mirrors.aliyun.com/ubuntu/ $VERSION_CODENAME-updates main restricted universe multiverse
EOF
            ;;
    esac
    
    # 清理并更新
    sudo rm -rf /etc/apt/sources.list.d/*
    sudo apt-get clean
    sudo apt-get update
    
    log_success "APT源修复完成"
}

# 修复Docker网络问题
fix_docker_network() {
    log_info "修复Docker网络问题..."
    
    # 配置Docker镜像源
    sudo mkdir -p /etc/docker
    sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "registry-mirrors": [
        "https://docker.mirrors.ustc.edu.cn",
        "https://hub-mirror.c.163.com",
        "https://mirror.baidubce.com"
    ],
    "dns": ["8.8.8.8", "114.114.114.114"],
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
EOF
    
    # 重启Docker服务
    sudo systemctl restart docker
    
    log_success "Docker网络修复完成"
}

# 修复pip网络问题
fix_pip_network() {
    log_info "修复pip网络问题..."
    
    mkdir -p ~/.pip
    cat > ~/.pip/pip.conf <<EOF
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
timeout = 300
retries = 5

[install]
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF
    
    log_success "pip网络修复完成"
}

# 使用简化版Dockerfile
use_simple_dockerfile() {
    log_info "切换到简化版Dockerfile..."
    
    if [ -f "Dockerfile" ] && [ ! -f "Dockerfile.backup" ]; then
        cp Dockerfile Dockerfile.backup
        log_info "已备份原始Dockerfile"
    fi
    
    if [ -f "Dockerfile.simple" ]; then
        cp Dockerfile.simple Dockerfile
        log_success "已切换到简化版Dockerfile"
    else
        log_error "未找到简化版Dockerfile"
        return 1
    fi
}

# 测试网络连接
test_network() {
    log_info "测试网络连接..."
    
    # 测试基本网络
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        log_success "基本网络连接正常"
    else
        log_error "基本网络连接失败"
        return 1
    fi
    
    # 测试DNS解析
    if nslookup mirrors.aliyun.com >/dev/null 2>&1; then
        log_success "DNS解析正常"
    else
        log_warning "DNS解析可能有问题"
    fi
    
    # 测试镜像源连接
    if curl -s --connect-timeout 5 https://mirrors.aliyun.com >/dev/null; then
        log_success "阿里云镜像源连接正常"
    else
        log_warning "阿里云镜像源连接可能有问题"
    fi
    
    # 测试Docker Hub镜像源
    if curl -s --connect-timeout 5 https://docker.mirrors.ustc.edu.cn >/dev/null; then
        log_success "Docker镜像源连接正常"
    else
        log_warning "Docker镜像源连接可能有问题"
    fi
}

# 清理Docker缓存
clean_docker_cache() {
    log_info "清理Docker缓存..."
    
    # 停止所有容器
    docker stop $(docker ps -aq) 2>/dev/null || true
    
    # 清理镜像和缓存
    docker system prune -af
    docker builder prune -af
    
    log_success "Docker缓存清理完成"
}

# 主函数
main() {
    echo ""
    echo "========================================"
    echo "  网络问题修复脚本"
    echo "========================================"
    echo ""
    
    log_info "开始修复网络问题..."
    
    # 执行修复步骤
    fix_apt_sources
    fix_docker_network
    fix_pip_network
    use_simple_dockerfile
    clean_docker_cache
    
    echo ""
    log_info "测试修复效果..."
    test_network
    
    echo ""
    log_success "网络问题修复完成！"
    echo ""
    log_info "现在可以重新运行部署脚本："
    echo "  ./deploy.sh"
    echo ""
}

# 运行主函数
main
