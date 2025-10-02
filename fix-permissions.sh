#!/bin/bash

# ============================================
# 修复静态文件权限问题
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
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo ""
echo "========================================="
echo "  修复静态文件权限（403错误）"
echo "========================================="
echo ""

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then 
    log_error "请使用root权限运行此脚本"
    echo "使用命令: sudo bash fix-permissions.sh"
    exit 1
fi

# 获取项目路径
read -p "请输入CRM项目路径（默认: /root/crm）: " PROJECT_PATH
PROJECT_PATH=${PROJECT_PATH:-/root/crm}

if [ ! -d "$PROJECT_PATH" ]; then
    log_error "项目路径不存在: $PROJECT_PATH"
    exit 1
fi

log_info "项目路径: $PROJECT_PATH"

# 1. 检查Nginx用户
log_info "检查Nginx运行用户..."
NGINX_USER=$(ps aux | grep "nginx: worker" | grep -v grep | head -1 | awk '{print $1}')

if [ -z "$NGINX_USER" ]; then
    log_error "无法检测Nginx用户，Nginx可能未运行"
    log_info "尝试启动Nginx..."
    systemctl start nginx
    sleep 2
    NGINX_USER=$(ps aux | grep "nginx: worker" | grep -v grep | head -1 | awk '{print $1}')
fi

if [ -z "$NGINX_USER" ]; then
    log_error "仍然无法检测Nginx用户"
    log_info "假设Nginx用户为 www-data 或 nginx"
    NGINX_USER="www-data"
else
    log_success "Nginx运行用户: $NGINX_USER"
fi

# 2. 修复目录权限
log_info "修复目录权限..."

# 修复项目根目录权限（需要x权限才能访问子目录）
chmod 755 "$PROJECT_PATH"
log_success "项目根目录权限: 755"

# 修复static目录权限
chmod -R 755 "$PROJECT_PATH/static"
log_success "static目录权限: 755"

# 修复文件权限
find "$PROJECT_PATH/static" -type f -exec chmod 644 {} \;
log_success "static文件权限: 644"

# 3. 修复所有者（关键步骤）
log_info "修复文件所有者..."

# 尝试修改所有者为Nginx用户
if id "$NGINX_USER" &>/dev/null; then
    chown -R "$NGINX_USER:$NGINX_USER" "$PROJECT_PATH/static"
    log_success "所有者已修改为: $NGINX_USER:$NGINX_USER"
else
    log_error "用户 $NGINX_USER 不存在"
    log_info "保持当前所有者，仅修改权限"
fi

# 4. 修复父目录权限（重要！）
log_info "修复父目录权限..."

# 确保从根目录到static的所有父目录都有x权限
CURRENT_DIR="$PROJECT_PATH"
while [ "$CURRENT_DIR" != "/" ]; do
    chmod o+x "$CURRENT_DIR" 2>/dev/null
    CURRENT_DIR=$(dirname "$CURRENT_DIR")
done

log_success "父目录权限已修复"

# 5. 检查SELinux
if command -v getenforce &> /dev/null; then
    SELINUX_STATUS=$(getenforce 2>/dev/null)
    if [ "$SELINUX_STATUS" = "Enforcing" ]; then
        log_info "检测到SELinux处于强制模式"
        log_info "设置SELinux上下文..."
        
        # 设置正确的SELinux上下文
        chcon -R -t httpd_sys_content_t "$PROJECT_PATH/static" 2>/dev/null
        
        # 或者临时禁用SELinux
        read -p "是否临时禁用SELinux？(y/N) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            setenforce 0
            log_success "SELinux已临时禁用"
            log_info "重启后会恢复，永久禁用请编辑 /etc/selinux/config"
        fi
    fi
fi

# 6. 显示当前权限
echo ""
log_info "当前权限信息："
echo "-----------------------------------"
ls -la "$PROJECT_PATH" | grep static
echo ""
ls -la "$PROJECT_PATH/static/images/" | head -10

# 7. 测试访问
echo ""
log_info "测试静态文件访问..."
sleep 2

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

# 8. 检查Nginx错误日志
echo ""
log_info "检查Nginx错误日志（最近5条）："
echo "-----------------------------------"
tail -5 /var/log/nginx/crm-error.log 2>/dev/null | grep -v "^$" || echo "无错误日志"

echo ""
echo "========================================="
echo "  修复完成"
echo "========================================="
echo ""

# 9. 提供额外建议
if [ "$HTTP_CODE" != "200" ]; then
    echo "⚠️  如果问题仍然存在，请尝试："
    echo ""
    echo "1. 检查Nginx配置中的alias路径："
    echo "   grep -A 3 'location /static' /etc/nginx/sites-available/crm"
    echo ""
    echo "2. 确保路径正确："
    echo "   应该是: alias $PROJECT_PATH/static/;"
    echo "   注意结尾的斜杠"
    echo ""
    echo "3. 手动测试文件是否可读："
    echo "   sudo -u $NGINX_USER cat $PROJECT_PATH/static/images/logo1.png > /dev/null"
    echo ""
    echo "4. 查看详细错误："
    echo "   sudo tail -f /var/log/nginx/crm-error.log"
    echo ""
    echo "5. 如果使用了SELinux，完全禁用："
    echo "   sudo setenforce 0"
    echo ""
else
    echo "✅ 所有测试通过！"
    echo ""
    echo "请在浏览器中按 Ctrl+F5 强制刷新页面"
    echo ""
fi

