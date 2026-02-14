#!/bin/bash

# SSL证书自动续期一键配置脚本
# 适用于 sxylab.com

set -e  # 遇到错误立即退出

echo "=========================================="
echo "SSL证书自动续期配置脚本"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. 检查是否以root运行
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ 请使用root权限运行此脚本${NC}"
    echo "使用: sudo bash setup_ssl_auto_renew.sh"
    exit 1
fi

echo -e "${GREEN}✅ 权限检查通过${NC}"
echo ""

# 2. 检查certbot是否已安装
echo "检查certbot安装状态..."
if ! command -v certbot &> /dev/null; then
    echo -e "${RED}❌ certbot未安装${NC}"
    echo "正在安装certbot..."
    apt update
    apt install certbot python3-certbot-nginx -y
    echo -e "${GREEN}✅ certbot安装完成${NC}"
else
    echo -e "${GREEN}✅ certbot已安装${NC}"
fi
echo ""

# 3. 检查证书是否存在
echo "检查SSL证书..."
if [ ! -f "/etc/letsencrypt/live/sxylab.com/fullchain.pem" ]; then
    echo -e "${RED}❌ SSL证书不存在${NC}"
    echo "请先运行以下命令申请证书："
    echo "certbot certonly --standalone -d sxylab.com -d www.sxylab.com"
    exit 1
fi
echo -e "${GREEN}✅ SSL证书存在${NC}"
echo ""

# 4. 测试证书续期
echo "测试证书续期（模拟）..."
if certbot renew --dry-run 2>&1 | grep -q "Congratulations"; then
    echo -e "${GREEN}✅ 证书续期测试成功${NC}"
else
    echo -e "${YELLOW}⚠️  证书续期测试失败，尝试修复...${NC}"
    
    # 创建webroot目录
    mkdir -p /var/www/certbot
    chmod 755 /var/www/certbot
    
    # 备份nginx配置
    cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)
    
    echo -e "${YELLOW}请检查nginx配置，确保HTTP服务器块包含以下内容：${NC}"
    echo ""
    echo "server {"
    echo "    listen 80;"
    echo "    server_name sxylab.com www.sxylab.com;"
    echo ""
    echo "    # certbot验证路径"
    echo "    location /.well-known/acme-challenge/ {"
    echo "        root /var/www/certbot;"
    echo "    }"
    echo ""
    echo "    # 其他路径重定向到HTTPS"
    echo "    location / {"
    echo "        return 301 https://\$server_name\$request_uri;"
    echo "    }"
    echo "}"
    echo ""
fi
echo ""

# 5. 配置systemd timer
echo "配置systemd自动续期..."

# 检查certbot.timer是否存在
if systemctl list-unit-files | grep -q "certbot.timer"; then
    echo -e "${GREEN}✅ certbot.timer已存在${NC}"
    
    # 启用并启动timer
    systemctl enable certbot.timer
    systemctl start certbot.timer
    
    echo -e "${GREEN}✅ certbot.timer已启用并启动${NC}"
else
    echo -e "${YELLOW}⚠️  certbot.timer不存在，创建systemd服务...${NC}"
    
    # 创建certbot续期服务
    cat > /etc/systemd/system/certbot-renew.service << 'EOF'
[Unit]
Description=Certbot Renewal
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/certbot renew --quiet --post-hook "systemctl reload nginx"
EOF

    # 创建certbot续期定时器
    cat > /etc/systemd/system/certbot-renew.timer << 'EOF'
[Unit]
Description=Certbot Renewal Timer

[Timer]
OnCalendar=daily
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # 重新加载systemd
    systemctl daemon-reload
    
    # 启用并启动timer
    systemctl enable certbot-renew.timer
    systemctl start certbot-renew.timer
    
    echo -e "${GREEN}✅ certbot续期服务已创建并启动${NC}"
fi
echo ""

# 6. 配置cron任务（备用方案）
echo "配置cron任务（备用）..."

# 检查是否已有cron任务
if crontab -l 2>/dev/null | grep -q "certbot renew"; then
    echo -e "${GREEN}✅ cron任务已存在${NC}"
else
    # 添加cron任务
    (crontab -l 2>/dev/null; echo "0 3 * * * /usr/bin/certbot renew --quiet --post-hook 'systemctl reload nginx'") | crontab -
    echo -e "${GREEN}✅ cron任务已添加（每天凌晨3点检查）${NC}"
fi
echo ""

# 7. 创建续期后钩子脚本
echo "创建续期后钩子脚本..."
mkdir -p /etc/letsencrypt/renewal-hooks/post

cat > /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh << 'EOF'
#!/bin/bash
# 证书续期后自动重新加载nginx

systemctl reload nginx

# 记录日志
echo "$(date): SSL证书已续期，nginx已重新加载" >> /var/log/certbot-renew.log
EOF

chmod +x /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh
echo -e "${GREEN}✅ 续期后钩子脚本已创建${NC}"
echo ""

# 8. 创建监控脚本
echo "创建证书监控脚本..."
cat > /usr/local/bin/check-ssl-expiry.sh << 'EOF'
#!/bin/bash

# 检查SSL证书过期时间
CERT_FILE="/etc/letsencrypt/live/sxylab.com/fullchain.pem"

if [ ! -f "$CERT_FILE" ]; then
    echo "证书文件不存在: $CERT_FILE"
    exit 1
fi

# 获取过期时间
EXPIRY_DATE=$(openssl x509 -in "$CERT_FILE" -noout -enddate | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))

echo "SSL证书状态："
echo "域名: sxylab.com"
echo "过期时间: $EXPIRY_DATE"
echo "剩余天数: $DAYS_LEFT 天"

if [ $DAYS_LEFT -lt 30 ]; then
    echo "⚠️  警告：证书即将过期！"
    exit 1
elif [ $DAYS_LEFT -lt 7 ]; then
    echo "❌ 紧急：证书即将过期！"
    exit 2
else
    echo "✅ 证书有效期充足"
    exit 0
fi
EOF

chmod +x /usr/local/bin/check-ssl-expiry.sh
echo -e "${GREEN}✅ 证书监控脚本已创建${NC}"
echo ""

# 9. 查看配置状态
echo "=========================================="
echo "配置完成！查看状态："
echo "=========================================="
echo ""

echo "1. 证书信息："
certbot certificates
echo ""

echo "2. systemd timer状态："
systemctl status certbot.timer --no-pager 2>/dev/null || systemctl status certbot-renew.timer --no-pager
echo ""

echo "3. 下次续期时间："
systemctl list-timers | grep certbot
echo ""

echo "4. cron任务："
crontab -l | grep certbot || echo "未配置cron任务"
echo ""

echo "5. 证书有效期："
/usr/local/bin/check-ssl-expiry.sh
echo ""

echo "=========================================="
echo "✅ SSL自动续期配置完成！"
echo "=========================================="
echo ""

echo "📋 配置说明："
echo "---"
echo "1. systemd timer: 每天自动检查并续期证书"
echo "2. cron任务: 每天凌晨3点检查并续期（备用）"
echo "3. 续期后自动重新加载nginx"
echo "4. 证书在过期前30天开始尝试续期"
echo ""

echo "💡 常用命令："
echo "---"
echo "查看证书状态:     certbot certificates"
echo "手动续期:         certbot renew"
echo "测试续期:         certbot renew --dry-run"
echo "查看timer状态:    systemctl status certbot.timer"
echo "查看证书过期时间: /usr/local/bin/check-ssl-expiry.sh"
echo ""

echo "📧 提醒："
echo "---"
echo "请确保您能收到certbot发送的邮件通知"
echo "建议每月运行一次: /usr/local/bin/check-ssl-expiry.sh"
echo ""

echo "🎉 完成！您的SSL证书将自动续期。"
echo ""

