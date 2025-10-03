#!/bin/bash

# ========================================
# CRM 服务诊断和修复脚本
# ========================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "========================================"
echo "  CRM 服务诊断和修复"
echo "========================================"
echo ""

# 1. 检查服务状态
log_info "1. 检查服务状态..."
sudo systemctl status crm --no-pager
echo ""

# 2. 查看最近的错误日志
log_info "2. 查看最近的错误日志..."
sudo journalctl -u crm -n 30 --no-pager
echo ""

# 3. 检查服务配置文件
log_info "3. 检查服务配置文件..."
sudo systemctl cat crm
echo ""

# 4. 检查项目目录
log_info "4. 检查项目目录..."
ls -la /root/crm/ | head -20
echo ""

# 5. 检查数据库文件
log_info "5. 检查数据库文件..."
ls -lh /root/crm/instance/edu_crm.db 2>/dev/null || log_warning "数据库文件不存在"
echo ""

# 6. 检查虚拟环境
log_info "6. 检查虚拟环境..."
if [ -d "/root/crm/venv" ]; then
    log_success "虚拟环境存在"
    ls -la /root/crm/venv/bin/python* 2>/dev/null
else
    log_warning "虚拟环境不存在"
fi
echo ""

# 7. 检查端口占用
log_info "7. 检查端口占用..."
sudo lsof -i :5000 2>/dev/null || log_info "端口 5000 未被占用"
echo ""

# 8. 检查权限
log_info "8. 检查关键目录权限..."
ls -ld /root/crm/instance 2>/dev/null || log_warning "instance 目录不存在"
ls -ld /root/crm/logs 2>/dev/null || log_warning "logs 目录不存在"
echo ""

# 9. 尝试手动启动（测试）
log_info "9. 尝试手动启动测试..."
read -p "是否要尝试手动启动测试？(y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "停止 systemd 服务..."
    sudo systemctl stop crm
    sleep 2
    
    log_info "手动启动应用（10秒后自动停止）..."
    cd /root/crm
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    timeout 10 python run.py 2>&1 | head -50
    
    echo ""
    log_info "手动测试完成"
fi

echo ""
echo "========================================"
echo "  诊断完成"
echo "========================================"
echo ""
log_info "请根据上面的输出信息检查问题"
log_info "常见问题："
echo "  1. 虚拟环境路径错误 - 检查 systemd 配置中的 ExecStart"
echo "  2. 工作目录错误 - 检查 WorkingDirectory"
echo "  3. 权限问题 - 检查 instance/ 和 logs/ 目录权限"
echo "  4. 依赖缺失 - 运行: pip install -r requirements.txt"
echo "  5. 数据库问题 - 检查 instance/edu_crm.db 是否存在"
echo ""

