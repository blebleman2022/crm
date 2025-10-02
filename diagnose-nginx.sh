#!/bin/bash

# ============================================
# Nginx静态文件问题诊断脚本
# ============================================

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
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

echo ""
echo "========================================="
echo "  Nginx静态文件问题诊断"
echo "========================================="
echo ""

# 获取项目路径
read -p "请输入CRM项目路径（默认: /root/crm）: " PROJECT_PATH
PROJECT_PATH=${PROJECT_PATH:-/root/crm}

echo ""
log_info "开始诊断..."
echo ""

# 1. 检查项目目录
echo "1️⃣  检查项目目录"
echo "-----------------------------------"
if [ -d "$PROJECT_PATH" ]; then
    log_success "项目目录存在: $PROJECT_PATH"
else
    log_error "项目目录不存在: $PROJECT_PATH"
    exit 1
fi

# 2. 检查静态文件目录
echo ""
echo "2️⃣  检查静态文件目录"
echo "-----------------------------------"
if [ -d "$PROJECT_PATH/static" ]; then
    log_success "static目录存在"
    
    if [ -d "$PROJECT_PATH/static/images" ]; then
        log_success "static/images目录存在"
        
        echo ""
        echo "📁 静态文件列表:"
        ls -lh "$PROJECT_PATH/static/images/" | grep -E '\.(png|jpg|jpeg|gif|svg|ico)$'
    else
        log_error "static/images目录不存在"
    fi
else
    log_error "static目录不存在"
    exit 1
fi

# 3. 检查文件权限
echo ""
echo "3️⃣  检查文件权限"
echo "-----------------------------------"
STATIC_PERM=$(stat -c "%a" "$PROJECT_PATH/static" 2>/dev/null || stat -f "%Lp" "$PROJECT_PATH/static" 2>/dev/null)
STATIC_OWNER=$(stat -c "%U:%G" "$PROJECT_PATH/static" 2>/dev/null || stat -f "%Su:%Sg" "$PROJECT_PATH/static" 2>/dev/null)

echo "static目录权限: $STATIC_PERM"
echo "static目录所有者: $STATIC_OWNER"

if [ -f "$PROJECT_PATH/static/images/logo1.png" ]; then
    LOGO_PERM=$(stat -c "%a" "$PROJECT_PATH/static/images/logo1.png" 2>/dev/null || stat -f "%Lp" "$PROJECT_PATH/static/images/logo1.png" 2>/dev/null)
    echo "logo1.png权限: $LOGO_PERM"
    
    if [ "$LOGO_PERM" -ge "644" ]; then
        log_success "文件权限正常"
    else
        log_warning "文件权限可能不足，建议设置为644或755"
    fi
else
    log_error "logo1.png文件不存在"
fi

# 4. 检查Nginx配置
echo ""
echo "4️⃣  检查Nginx配置"
echo "-----------------------------------"
if [ -f /etc/nginx/sites-available/crm ]; then
    log_success "Nginx配置文件存在"
    
    echo ""
    echo "📄 静态文件相关配置:"
    grep -A 5 "location /static" /etc/nginx/sites-available/crm
    
    echo ""
    echo "📄 Favicon配置:"
    grep -A 3 "favicon" /etc/nginx/sites-available/crm
else
    log_error "Nginx配置文件不存在: /etc/nginx/sites-available/crm"
fi

# 5. 测试Nginx配置
echo ""
echo "5️⃣  测试Nginx配置"
echo "-----------------------------------"
nginx -t 2>&1 | head -5

# 6. 检查Nginx进程
echo ""
echo "6️⃣  检查Nginx进程"
echo "-----------------------------------"
if systemctl is-active --quiet nginx; then
    log_success "Nginx正在运行"
    
    NGINX_USER=$(ps aux | grep nginx | grep worker | head -1 | awk '{print $1}')
    echo "Nginx worker进程用户: $NGINX_USER"
else
    log_error "Nginx未运行"
fi

# 7. 测试静态文件访问
echo ""
echo "7️⃣  测试静态文件访问"
echo "-----------------------------------"

# 测试logo1.png
echo -n "测试 /static/images/logo1.png ... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/static/images/logo1.png 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    log_success "HTTP $HTTP_CODE"
else
    log_error "HTTP $HTTP_CODE"
fi

# 测试custom-logo.png
echo -n "测试 /static/images/custom-logo.png ... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/static/images/custom-logo.png 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    log_success "HTTP $HTTP_CODE"
else
    log_error "HTTP $HTTP_CODE"
fi

# 测试favicon
echo -n "测试 /favicon.ico ... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/favicon.ico 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    log_success "HTTP $HTTP_CODE"
else
    log_error "HTTP $HTTP_CODE"
fi

# 8. 检查Nginx日志
echo ""
echo "8️⃣  检查Nginx错误日志（最近10条）"
echo "-----------------------------------"
if [ -f /var/log/nginx/crm-error.log ]; then
    tail -10 /var/log/nginx/crm-error.log | grep -v "^$" || echo "无错误日志"
else
    echo "错误日志文件不存在"
fi

# 9. 检查SELinux（如果适用）
echo ""
echo "9️⃣  检查SELinux状态"
echo "-----------------------------------"
if command -v getenforce &> /dev/null; then
    SELINUX_STATUS=$(getenforce 2>/dev/null)
    echo "SELinux状态: $SELINUX_STATUS"
    
    if [ "$SELINUX_STATUS" = "Enforcing" ]; then
        log_warning "SELinux处于强制模式，可能阻止Nginx访问静态文件"
        echo "临时禁用SELinux: sudo setenforce 0"
        echo "永久禁用SELinux: 编辑 /etc/selinux/config"
    fi
else
    echo "系统未安装SELinux"
fi

# 10. 生成修复建议
echo ""
echo "========================================="
echo "  🔧 修复建议"
echo "========================================="
echo ""

# 检查是否有问题
ISSUES=0

# 检查权限
if [ "$STATIC_PERM" -lt "755" ]; then
    echo "1. 修复静态文件权限:"
    echo "   sudo chmod -R 755 $PROJECT_PATH/static"
    ISSUES=$((ISSUES+1))
fi

# 检查Nginx配置
if ! grep -q "location /static/" /etc/nginx/sites-available/crm 2>/dev/null; then
    echo "2. Nginx配置缺少静态文件location块"
    echo "   运行修复脚本: sudo bash fix-nginx-static.sh"
    ISSUES=$((ISSUES+1))
fi

# 检查alias路径
if grep -q "alias.*static;" /etc/nginx/sites-available/crm 2>/dev/null; then
    ALIAS_PATH=$(grep "alias.*static;" /etc/nginx/sites-available/crm | awk '{print $2}' | sed 's/;//')
    if [ "$ALIAS_PATH" != "$PROJECT_PATH/static/" ]; then
        echo "3. Nginx配置中的alias路径不正确"
        echo "   当前: $ALIAS_PATH"
        echo "   应为: $PROJECT_PATH/static/"
        echo "   运行修复脚本: sudo bash fix-nginx-static.sh"
        ISSUES=$((ISSUES+1))
    fi
fi

if [ $ISSUES -eq 0 ]; then
    echo ""
    log_success "未发现明显问题"
    echo ""
    echo "如果静态文件仍然无法访问，请检查:"
    echo "  1. 浏览器缓存（Ctrl+F5强制刷新）"
    echo "  2. 防火墙设置"
    echo "  3. Nginx错误日志: sudo tail -f /var/log/nginx/crm-error.log"
else
    echo ""
    echo "发现 $ISSUES 个问题，请按照上述建议修复"
fi

echo ""
echo "========================================="
echo "  📋 快速修复命令"
echo "========================================="
echo ""
echo "# 修复权限"
echo "sudo chmod -R 755 $PROJECT_PATH/static"
echo ""
echo "# 运行修复脚本"
echo "sudo bash fix-nginx-static.sh"
echo ""
echo "# 重新加载Nginx"
echo "sudo systemctl reload nginx"
echo ""
echo "# 清除浏览器缓存后测试"
echo "curl -I http://localhost/static/images/logo1.png"
echo ""

