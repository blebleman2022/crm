#!/bin/bash

# ============================================
# Nginx反向代理配置脚本
# ============================================

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

echo ""
echo "========================================="
echo "  Nginx反向代理配置脚本"
echo "========================================="
echo ""

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then 
    log_error "请使用root权限运行此脚本"
    echo "使用命令: sudo bash setup-nginx.sh"
    exit 1
fi

# 检查Nginx是否安装
if ! command -v nginx &> /dev/null; then
    log_warning "Nginx未安装，正在安装..."
    apt update
    apt install nginx -y
    
    if [ $? -eq 0 ]; then
        log_success "Nginx安装成功"
    else
        log_error "Nginx安装失败"
        exit 1
    fi
else
    log_success "Nginx已安装"
fi

# 获取服务器域名或IP
echo ""
log_info "配置服务器访问地址"
echo "如果您有域名，请输入域名（例如: example.com）"
echo "如果没有域名，直接回车使用IP地址访问"
read -p "请输入域名（留空使用IP）: " DOMAIN

if [ -z "$DOMAIN" ]; then
    DOMAIN="_"
    SERVER_NAME_DISPLAY="IP地址"
    log_info "使用默认配置（通过IP访问）"
else
    SERVER_NAME_DISPLAY="$DOMAIN"
    log_info "使用域名: $DOMAIN"
fi

# 获取项目路径
echo ""
read -p "请输入CRM项目路径（默认: /root/crm）: " PROJECT_PATH
PROJECT_PATH=${PROJECT_PATH:-/root/crm}

if [ ! -d "$PROJECT_PATH" ]; then
    log_error "项目路径不存在: $PROJECT_PATH"
    exit 1
fi

log_success "项目路径: $PROJECT_PATH"

# 创建Nginx配置文件
log_info "创建Nginx配置文件..."

cat > /etc/nginx/sites-available/crm << 'NGINX_EOF'
server {
    listen 80;
    server_name SERVER_NAME_PLACEHOLDER;

    # 日志配置
    access_log /var/log/nginx/crm-access.log;
    error_log /var/log/nginx/crm-error.log;

    # 客户端上传大小限制
    client_max_body_size 10M;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;

    # 反向代理到Flask应用
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # 禁用缓冲以支持流式响应
        proxy_buffering off;
    }

    # 静态文件直接由Nginx处理（提升性能）
    location /static {
        alias PROJECT_PATH_PLACEHOLDER/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Favicon
    location = /favicon.ico {
        alias PROJECT_PATH_PLACEHOLDER/static/images/favicon.ico;
        access_log off;
        log_not_found off;
    }

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
NGINX_EOF

# 替换占位符
sed -i "s|SERVER_NAME_PLACEHOLDER|$DOMAIN|g" /etc/nginx/sites-available/crm
sed -i "s|PROJECT_PATH_PLACEHOLDER|$PROJECT_PATH|g" /etc/nginx/sites-available/crm

log_success "配置文件已创建: /etc/nginx/sites-available/crm"

# 创建软链接启用站点
log_info "启用站点配置..."
ln -sf /etc/nginx/sites-available/crm /etc/nginx/sites-enabled/crm

# 询问是否删除默认站点
if [ -f /etc/nginx/sites-enabled/default ]; then
    echo ""
    read -p "是否删除Nginx默认站点配置？(y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm /etc/nginx/sites-enabled/default
        log_success "默认站点配置已删除"
    else
        log_info "保留默认站点配置"
    fi
fi

# 测试Nginx配置
log_info "测试Nginx配置..."
nginx -t

if [ $? -eq 0 ]; then
    log_success "Nginx配置测试通过"
    
    # 重启Nginx
    log_info "重启Nginx..."
    systemctl restart nginx
    
    if [ $? -eq 0 ]; then
        log_success "Nginx重启成功"
        
        # 设置开机自启
        systemctl enable nginx
        
        echo ""
        echo "========================================="
        echo "  ✅ Nginx配置成功！"
        echo "========================================="
        echo ""
        echo "📋 访问信息："
        
        if [ "$DOMAIN" = "_" ]; then
            SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
            echo "  - HTTP访问: http://$SERVER_IP"
        else
            echo "  - HTTP访问: http://$DOMAIN"
        fi
        
        echo ""
        echo "🔧 管理命令："
        echo "  - 查看Nginx状态: sudo systemctl status nginx"
        echo "  - 重启Nginx: sudo systemctl restart nginx"
        echo "  - 重新加载配置: sudo systemctl reload nginx"
        echo "  - 查看访问日志: sudo tail -f /var/log/nginx/crm-access.log"
        echo "  - 查看错误日志: sudo tail -f /var/log/nginx/crm-error.log"
        echo ""
        echo "📁 配置文件位置："
        echo "  - /etc/nginx/sites-available/crm"
        echo ""
        
        # 测试访问
        log_info "测试HTTP访问..."
        sleep 2
        
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null)
        
        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
            log_success "HTTP访问测试通过（状态码: $HTTP_CODE）"
        else
            log_warning "HTTP访问测试失败（状态码: $HTTP_CODE）"
            echo "请检查CRM应用是否在5000端口运行："
            echo "  docker compose ps"
            echo "  docker compose logs"
        fi
        
        # HTTPS提示
        if [ "$DOMAIN" != "_" ]; then
            echo ""
            echo "💡 提示："
            echo "如果您想配置HTTPS，可以使用Let's Encrypt免费SSL证书："
            echo "  sudo apt install certbot python3-certbot-nginx -y"
            echo "  sudo certbot --nginx -d $DOMAIN"
        fi
        
        echo ""
        
    else
        log_error "Nginx重启失败"
        echo "请检查错误日志: sudo journalctl -xeu nginx"
        exit 1
    fi
else
    log_error "Nginx配置测试失败"
    echo ""
    echo "请检查配置文件: /etc/nginx/sites-available/crm"
    echo "查看详细错误: sudo nginx -t"
    exit 1
fi

