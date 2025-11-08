#!/bin/bash

# 优化nginx配置以支持certbot自动续期
# 确保HTTP重定向不影响certbot验证

set -e

echo "=========================================="
echo "优化Nginx配置以支持certbot自动续期"
echo "=========================================="
echo ""

# 检查是否以root运行
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请使用root权限运行此脚本"
    exit 1
fi

# 备份nginx配置
BACKUP_FILE="/etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)"
cp /etc/nginx/nginx.conf "$BACKUP_FILE"
echo "✅ 已备份nginx配置到: $BACKUP_FILE"
echo ""

# 创建certbot验证目录
mkdir -p /var/www/certbot
chmod 755 /var/www/certbot
echo "✅ 已创建certbot验证目录: /var/www/certbot"
echo ""

# 显示推荐的nginx配置
echo "=========================================="
echo "推荐的Nginx配置"
echo "=========================================="
echo ""

cat << 'EOF'
# HTTP服务器 - 支持certbot验证并重定向到HTTPS
server {
    listen 80;
    server_name sxylab.com www.sxylab.com;

    # certbot验证路径（不重定向）
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # 其他路径重定向到HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS服务器
server {
    listen 443 ssl http2;
    server_name sxylab.com www.sxylab.com;

    # SSL证书
    ssl_certificate /etc/letsencrypt/live/sxylab.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sxylab.com/privkey.pem;
    
    # SSL配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 日志
    access_log /var/log/nginx/sxylab_ssl_access.log;
    error_log /var/log/nginx/sxylab_ssl_error.log;

    # 上传大小限制
    client_max_body_size 10M;

    # 静态文件
    location /static/ {
        alias /root/crm/static/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # 反向代理到Flask应用
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

echo ""
echo "=========================================="
echo "配置说明"
echo "=========================================="
echo ""
echo "关键点："
echo "1. HTTP服务器保留 /.well-known/acme-challenge/ 路径用于certbot验证"
echo "2. 其他HTTP请求重定向到HTTPS"
echo "3. 这样certbot可以正常续期，用户访问也会自动跳转HTTPS"
echo ""

echo "💡 建议："
echo "请手动检查并更新 /etc/nginx/nginx.conf 中的sxylab.com配置"
echo "确保HTTP服务器块包含 /.well-known/acme-challenge/ 路径配置"
echo ""

echo "修改后执行："
echo "  nginx -t              # 测试配置"
echo "  systemctl reload nginx # 重新加载"
echo ""

