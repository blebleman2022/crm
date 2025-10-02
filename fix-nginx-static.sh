#!/bin/bash

# ============================================
# 修复Nginx静态文件配置
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
echo "  修复Nginx静态文件配置"
echo "========================================="
echo ""

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then 
    log_error "请使用root权限运行此脚本"
    echo "使用命令: sudo bash fix-nginx-static.sh"
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

# 检查静态文件目录
if [ ! -d "$PROJECT_PATH/static" ]; then
    log_error "静态文件目录不存在: $PROJECT_PATH/static"
    exit 1
fi

log_success "静态文件目录存在"

# 检查静态文件权限
log_info "检查静态文件权限..."
ls -la "$PROJECT_PATH/static/images/" | head -10

# 修复权限
log_info "修复静态文件权限..."
chmod -R 755 "$PROJECT_PATH/static"
chown -R www-data:www-data "$PROJECT_PATH/static" 2>/dev/null || chown -R nginx:nginx "$PROJECT_PATH/static" 2>/dev/null || true

log_success "权限已修复"

# 更新Nginx配置
log_info "更新Nginx配置..."

# 备份原配置
if [ -f /etc/nginx/sites-available/crm ]; then
    cp /etc/nginx/sites-available/crm /etc/nginx/sites-available/crm.backup.$(date +%Y%m%d_%H%M%S)
    log_success "原配置已备份"
fi

# 获取server_name
SERVER_NAME=$(grep "server_name" /etc/nginx/sites-available/crm | head -1 | awk '{print $2}' | sed 's/;//')

# 创建新配置
cat > /etc/nginx/sites-available/crm << NGINX_EOF
server {
    listen 80;
    server_name $SERVER_NAME;

    # 日志配置
    access_log /var/log/nginx/crm-access.log;
    error_log /var/log/nginx/crm-error.log;

    # 客户端上传大小限制
    client_max_body_size 10M;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss image/svg+xml;

    # 静态文件配置（优先级最高）
    location /static/ {
        alias $PROJECT_PATH/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
        
        # 允许跨域（如果需要）
        add_header Access-Control-Allow-Origin "*";
        
        # 自动索引（调试用，生产环境建议关闭）
        # autoindex on;
    }

    # Favicon特殊处理
    location = /favicon.ico {
        alias $PROJECT_PATH/static/images/logo1.png;
        access_log off;
        log_not_found off;
        expires 30d;
    }

    # 反向代理到Flask应用
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # 禁用缓冲
        proxy_buffering off;
    }

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
NGINX_EOF

log_success "Nginx配置已更新"

# 测试配置
log_info "测试Nginx配置..."
nginx -t

if [ $? -eq 0 ]; then
    log_success "配置测试通过"
    
    # 重新加载Nginx
    log_info "重新加载Nginx..."
    systemctl reload nginx
    
    if [ $? -eq 0 ]; then
        log_success "Nginx已重新加载"
        
        echo ""
        echo "========================================="
        echo "  ✅ 修复完成！"
        echo "========================================="
        echo ""
        
        # 测试静态文件访问
        log_info "测试静态文件访问..."
        sleep 2
        
        echo ""
        echo "📋 测试结果："
        
        # 测试logo
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/static/images/logo1.png 2>/dev/null)
        if [ "$HTTP_CODE" = "200" ]; then
            log_success "Logo访问正常 (HTTP $HTTP_CODE)"
        else
            log_error "Logo访问失败 (HTTP $HTTP_CODE)"
        fi
        
        # 测试favicon
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/favicon.ico 2>/dev/null)
        if [ "$HTTP_CODE" = "200" ]; then
            log_success "Favicon访问正常 (HTTP $HTTP_CODE)"
        else
            log_error "Favicon访问失败 (HTTP $HTTP_CODE)"
        fi
        
        # 测试custom-logo
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/static/images/custom-logo.png 2>/dev/null)
        if [ "$HTTP_CODE" = "200" ]; then
            log_success "Custom Logo访问正常 (HTTP $HTTP_CODE)"
        else
            log_error "Custom Logo访问失败 (HTTP $HTTP_CODE)"
        fi
        
        echo ""
        echo "🔍 调试信息："
        echo "  - 静态文件路径: $PROJECT_PATH/static/"
        echo "  - 查看Nginx错误日志: sudo tail -f /var/log/nginx/crm-error.log"
        echo "  - 查看访问日志: sudo tail -f /var/log/nginx/crm-access.log"
        echo ""
        echo "🧪 手动测试命令："
        echo "  curl -I http://localhost/static/images/logo1.png"
        echo "  curl -I http://localhost/static/images/custom-logo.png"
        echo "  curl -I http://localhost/favicon.ico"
        echo ""
        
    else
        log_error "Nginx重新加载失败"
        exit 1
    fi
else
    log_error "Nginx配置测试失败"
    echo "请检查配置文件: /etc/nginx/sites-available/crm"
    exit 1
fi

