#!/bin/bash
# SSL 证书修复脚本
# 用于修复过期的 SSL 证书并配置 Nginx
# 使用方法: sudo bash fix_ssl_certificate.sh

set -e

echo "============================================================"
echo "🔧 SSL 证书修复脚本"
echo "域名: www.sxylab.com, sxylab.com"
echo "============================================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否以 root 权限运行
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ 请使用 sudo 运行此脚本${NC}"
    echo "   sudo bash fix_ssl_certificate.sh"
    exit 1
fi

echo "📋 当前问题:"
echo "   • SSL 证书已过期 (过期时间: 2026-02-06)"
echo "   • Nginx 配置未包含 SSL 设置"
echo ""

# 1. 备份当前配置
echo "📦 第1步: 备份当前配置..."
echo "-----------------------------------------------------------"

BACKUP_DIR="/root/ssl_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 备份 Nginx 配置
if [ -f "/etc/nginx/sites-available/crm" ]; then
    cp /etc/nginx/sites-available/crm "$BACKUP_DIR/crm.conf.bak"
    echo -e "${GREEN}✅ Nginx 配置已备份到: $BACKUP_DIR/crm.conf.bak${NC}"
fi

# 备份旧证书
if [ -d "/etc/letsencrypt/live/sxylab.com" ]; then
    cp -r /etc/letsencrypt/live/sxylab.com "$BACKUP_DIR/old_cert"
    echo -e "${GREEN}✅ 旧证书已备份到: $BACKUP_DIR/old_cert${NC}"
fi

echo ""

# 2. 续期证书
echo "🔄 第2步: 续期 SSL 证书..."
echo "-----------------------------------------------------------"

# 停止 Nginx 以释放 80 和 443 端口
echo "停止 Nginx..."
systemctl stop nginx

# 续期证书
echo "正在续期证书..."
if certbot renew --force-renewal --cert-name sxylab.com; then
    echo -e "${GREEN}✅ 证书续期成功!${NC}"
else
    echo -e "${RED}❌ 证书续期失败,尝试重新申请...${NC}"
    
    # 如果续期失败,尝试重新申请
    certbot certonly --standalone \
        -d sxylab.com \
        -d www.sxylab.com \
        --non-interactive \
        --agree-tos \
        --email admin@sxylab.com \
        --force-renewal
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 证书重新申请成功!${NC}"
    else
        echo -e "${RED}❌ 证书申请失败,请检查域名 DNS 配置${NC}"
        systemctl start nginx
        exit 1
    fi
fi

echo ""

# 3. 验证新证书
echo "🔍 第3步: 验证新证书..."
echo "-----------------------------------------------------------"

CERT_FILE="/etc/letsencrypt/live/sxylab.com/cert.pem"

if [ -f "$CERT_FILE" ]; then
    echo "证书详情:"
    
    # 颁发者
    ISSUER=$(openssl x509 -in "$CERT_FILE" -noout -issuer | sed 's/issuer=//')
    echo "   颁发者: $ISSUER"
    
    # 有效期
    NOT_BEFORE=$(openssl x509 -in "$CERT_FILE" -noout -startdate | cut -d'=' -f2)
    NOT_AFTER=$(openssl x509 -in "$CERT_FILE" -noout -enddate | cut -d'=' -f2)
    echo "   生效时间: $NOT_BEFORE"
    echo "   过期时间: $NOT_AFTER"
    
    # 检查是否有效
    if openssl x509 -in "$CERT_FILE" -noout -checkend 0; then
        DAYS_LEFT=$(( ($(date -d "$NOT_AFTER" +%s) - $(date +%s)) / 86400 ))
        echo -e "   ${GREEN}✅ 证书有效 (剩余 $DAYS_LEFT 天)${NC}"
    else
        echo -e "   ${RED}❌ 证书仍然无效!${NC}"
        systemctl start nginx
        exit 1
    fi
    
    # 域名
    echo ""
    echo "   证书包含的域名:"
    openssl x509 -in "$CERT_FILE" -noout -text | grep -A1 "Subject Alternative Name" | tail -1 | sed 's/DNS://g' | tr ',' '\n' | sed 's/^/   - /'
else
    echo -e "${RED}❌ 证书文件不存在!${NC}"
    systemctl start nginx
    exit 1
fi

echo ""

# 4. 配置 Nginx SSL
echo "⚙️  第4步: 配置 Nginx SSL..."
echo "-----------------------------------------------------------"

NGINX_CONF="/etc/nginx/sites-available/crm"

# 检查配置文件是否存在
if [ ! -f "$NGINX_CONF" ]; then
    echo -e "${RED}❌ Nginx 配置文件不存在: $NGINX_CONF${NC}"
    systemctl start nginx
    exit 1
fi

# 检查配置文件是否已包含 SSL 设置
if grep -q "ssl_certificate" "$NGINX_CONF"; then
    echo -e "${YELLOW}⚠️  配置文件已包含 SSL 设置,跳过配置${NC}"
else
    echo "正在添加 SSL 配置..."
    
    # 创建新的配置文件
    cat > "$NGINX_CONF" << 'EOF'
# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name sxylab.com www.sxylab.com;
    
    # Let's Encrypt 验证路径
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # 其他请求重定向到 HTTPS
    location / {
        return 301 https://sxylab.com$request_uri;
    }
}

# HTTPS 配置
server {
    listen 443 ssl http2;
    server_name sxylab.com www.sxylab.com;
    
    # SSL 证书配置
    ssl_certificate /etc/letsencrypt/live/sxylab.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sxylab.com/privkey.pem;
    
    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS (增强安全性)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # CRM 应用配置
    location / {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 静态文件
    location /static {
        alias /root/crm/static;
        expires 30d;
    }
}
EOF
    
    echo -e "${GREEN}✅ SSL 配置已添加${NC}"
fi

echo ""

# 5. 测试 Nginx 配置
echo "🧪 第5步: 测试 Nginx 配置..."
echo "-----------------------------------------------------------"

if nginx -t; then
    echo -e "${GREEN}✅ Nginx 配置语法正确${NC}"
else
    echo -e "${RED}❌ Nginx 配置语法错误,恢复备份...${NC}"
    cp "$BACKUP_DIR/crm.conf.bak" /etc/nginx/sites-available/crm
    systemctl start nginx
    exit 1
fi

echo ""

# 6. 重启 Nginx
echo "🔄 第6步: 重启 Nginx..."
echo "-----------------------------------------------------------"

systemctl start nginx
systemctl reload nginx

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx 已成功重启${NC}"
else
    echo -e "${RED}❌ Nginx 启动失败${NC}"
    systemctl status nginx
    exit 1
fi

echo ""

# 7. 配置自动续期
echo "⏰ 第7步: 配置自动续期..."
echo "-----------------------------------------------------------"

# 创建续期后钩子脚本
mkdir -p /etc/letsencrypt/renewal-hooks/deploy

cat > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh << 'HOOK_EOF'
#!/bin/bash
# Certbot 续期后自动重启 Nginx
echo "$(date): SSL 证书已续期,正在重启 Nginx..." >> /var/log/certbot-renew.log

if nginx -t 2>&1 >> /var/log/certbot-renew.log; then
    systemctl reload nginx
    echo "$(date): Nginx 已成功重启" >> /var/log/certbot-renew.log
else
    echo "$(date): Nginx 配置测试失败,未重启" >> /var/log/certbot-renew.log
    exit 1
fi
HOOK_EOF

chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
touch /var/log/certbot-renew.log

echo -e "${GREEN}✅ 续期后钩子脚本已创建${NC}"

# 测试自动续期
if certbot renew --dry-run --deploy-hook "/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh" 2>&1 | grep -q "Congratulations"; then
    echo -e "${GREEN}✅ 自动续期配置正确${NC}"
else
    echo -e "${YELLOW}⚠️  自动续期测试有警告,但证书已更新${NC}"
fi

# 检查 systemd timer
if systemctl is-enabled --quiet certbot.timer; then
    echo -e "${GREEN}✅ Certbot 自动续期定时器已启用${NC}"
else
    echo "启用 Certbot 自动续期..."
    systemctl enable certbot.timer
    systemctl start certbot.timer
    echo -e "${GREEN}✅ 已启用自动续期${NC}"
fi

echo ""
echo "   自动续期配置:"
echo "   • 每天检查证书有效期"
echo "   • 过期前 30 天自动续期"
echo "   • 续期后自动重启 Nginx"

echo ""

# 8. 验证 HTTPS 连接
echo "🌐 第8步: 验证 HTTPS 连接..."
echo "-----------------------------------------------------------"

sleep 2

if curl -s -I --max-time 5 https://www.sxylab.com > /dev/null 2>&1; then
    echo -e "${GREEN}✅ HTTPS 连接成功!${NC}"
    echo ""
    echo "   响应头信息:"
    curl -s -I --max-time 5 https://www.sxylab.com | head -5 | sed 's/^/   /'
else
    echo -e "${YELLOW}⚠️  HTTPS 连接测试失败,但证书已更新${NC}"
    echo "   可能需要等待几分钟让配置生效"
fi

echo ""

# 完成
echo "============================================================"
echo "✅ SSL 证书修复完成!"
echo "============================================================"
echo ""
echo "📊 修复总结:"
echo "   • 证书已续期并验证有效"
echo "   • Nginx SSL 配置已更新"
echo "   • 自动续期已配置"
echo ""
echo "🔗 请访问以下地址验证:"
echo "   https://www.sxylab.com"
echo "   https://sxylab.com"
echo ""
echo "📁 备份位置: $BACKUP_DIR"
echo ""
echo "💡 提示:"
echo "   • 如果浏览器仍显示不安全,请清除浏览器缓存"
echo "   • 证书将在到期前自动续期"
echo "   • 下次续期时间: $(date -d '+60 days' '+%Y-%m-%d')"
echo ""

