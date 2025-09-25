#!/bin/bash

# 部署前检查脚本
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

echo "🔍 EduConnect CRM 部署前检查"
echo "================================"

# 检查必需文件
check_files() {
    log_info "检查必需文件..."
    
    local missing_files=()
    
    if [ ! -f "Dockerfile" ]; then
        missing_files+=("Dockerfile")
    fi
    
    if [ ! -f "docker-compose.yml" ]; then
        missing_files+=("docker-compose.yml")
    fi
    
    if [ ! -f "requirements.txt" ]; then
        missing_files+=("requirements.txt")
    fi
    
    if [ ! -f "run.py" ]; then
        missing_files+=("run.py")
    fi
    
    if [ ! -f "instance/edu_crm.db" ]; then
        missing_files+=("instance/edu_crm.db")
    fi
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        log_error "缺少必需文件:"
        for file in "${missing_files[@]}"; do
            echo "  ❌ $file"
        done
        return 1
    fi
    
    log_success "所有必需文件检查通过"
    return 0
}

# 检查Docker环境
check_docker() {
    log_info "检查Docker环境..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        echo "安装命令: curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
        return 1
    fi
    
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker服务未运行"
        echo "启动命令: sudo systemctl start docker"
        return 1
    fi
    
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装或版本过低"
        return 1
    fi
    
    log_success "Docker环境正常"
    return 0
}

# 检查端口占用
check_ports() {
    log_info "检查端口占用..."
    
    if command -v netstat &> /dev/null; then
        if netstat -tlnp 2>/dev/null | grep :5000 > /dev/null; then
            log_warning "端口5000已被占用"
            echo "占用进程:"
            netstat -tlnp 2>/dev/null | grep :5000
            echo "建议: 修改docker-compose.yml中的端口映射"
            return 1
        fi
    elif command -v ss &> /dev/null; then
        if ss -tlnp 2>/dev/null | grep :5000 > /dev/null; then
            log_warning "端口5000已被占用"
            echo "占用进程:"
            ss -tlnp 2>/dev/null | grep :5000
            return 1
        fi
    else
        log_warning "无法检查端口占用（缺少netstat或ss命令）"
    fi
    
    log_success "端口5000可用"
    return 0
}

# 检查数据库文件
check_database() {
    log_info "检查数据库文件..."
    
    if [ ! -f "instance/edu_crm.db" ]; then
        log_error "数据库文件不存在: instance/edu_crm.db"
        return 1
    fi
    
    # 检查文件权限
    local perms=$(stat -c "%a" instance/edu_crm.db 2>/dev/null || stat -f "%A" instance/edu_crm.db 2>/dev/null || echo "unknown")
    if [ "$perms" != "666" ] && [ "$perms" != "unknown" ]; then
        log_warning "数据库文件权限不正确: $perms (应该是666)"
        echo "修复命令: chmod 666 instance/edu_crm.db"
    fi
    
    # 检查文件大小
    local size=$(stat -c "%s" instance/edu_crm.db 2>/dev/null || stat -f "%z" instance/edu_crm.db 2>/dev/null || echo "0")
    if [ "$size" -eq 0 ]; then
        log_warning "数据库文件为空"
    else
        log_success "数据库文件存在且有内容 (${size} bytes)"
    fi
    
    return 0
}

# 检查系统资源
check_resources() {
    log_info "检查系统资源..."
    
    # 检查内存
    if command -v free &> /dev/null; then
        local mem_available=$(free -m | awk 'NR==2{printf "%.0f", $7}')
        if [ "$mem_available" -lt 512 ]; then
            log_warning "可用内存不足: ${mem_available}MB (建议至少512MB)"
        else
            log_success "可用内存充足: ${mem_available}MB"
        fi
    fi
    
    # 检查磁盘空间
    if command -v df &> /dev/null; then
        local disk_available=$(df . | awk 'NR==2{print $4}')
        local disk_available_mb=$((disk_available / 1024))
        if [ "$disk_available_mb" -lt 1024 ]; then
            log_warning "可用磁盘空间不足: ${disk_available_mb}MB (建议至少1GB)"
        else
            log_success "可用磁盘空间充足: ${disk_available_mb}MB"
        fi
    fi
    
    return 0
}

# 检查配置文件
check_config() {
    log_info "检查配置文件..."
    
    # 检查docker-compose.yml语法
    if ! docker compose -f docker-compose.yml config > /dev/null 2>&1; then
        log_error "docker-compose.yml配置文件有语法错误"
        echo "检查命令: docker compose -f docker-compose.yml config"
        return 1
    fi
    
    log_success "配置文件语法正确"
    return 0
}

# 修复常见问题
fix_common_issues() {
    log_info "修复常见问题..."
    
    # 创建必要目录
    mkdir -p instance logs
    chmod 755 instance logs
    
    # 修复数据库权限
    if [ -f "instance/edu_crm.db" ]; then
        chmod 666 instance/edu_crm.db
        log_success "已修复数据库文件权限"
    fi
    
    return 0
}

# 主检查流程
main() {
    local failed_checks=0
    
    # 执行所有检查
    check_files || ((failed_checks++))
    check_docker || ((failed_checks++))
    check_ports || ((failed_checks++))
    check_database || ((failed_checks++))
    check_resources || ((failed_checks++))
    check_config || ((failed_checks++))
    
    echo ""
    echo "================================"
    
    if [ $failed_checks -eq 0 ]; then
        log_success "🎉 所有检查通过！可以开始部署"
        echo ""
        echo "部署命令:"
        echo "  docker compose up -d --build"
        echo ""
        echo "访问地址:"
        echo "  http://localhost:5000"
        echo "  默认管理员: 13800138000"
    else
        log_error "❌ 发现 $failed_checks 个问题，请修复后再部署"
        echo ""
        echo "尝试自动修复:"
        echo "  ./pre-deploy-check.sh fix"
    fi
    
    echo "================================"
    return $failed_checks
}

# 自动修复模式
if [ "${1:-}" = "fix" ]; then
    log_info "🔧 自动修复模式"
    fix_common_issues
    echo ""
    log_info "重新检查..."
    main
else
    main
fi
