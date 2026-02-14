#!/bin/bash

# SSL证书自动续期一键配置脚本
# 使用方法：
#   1. 上传到服务器: scp 一键配置SSL自动续期.sh root@47.100.238.50:/root/
#   2. SSH登录: ssh root@47.100.238.50
#   3. 执行: bash /root/一键配置SSL自动续期.sh

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "${BLUE}=========================================="
echo "SSL证书自动续期一键配置"
echo "==========================================${NC}"
echo ""

# 检查root权限
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ 请使用root权限运行${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 权限检查通过${NC}"
echo ""

# 步骤1：检查certbot
echo -e "${BLUE}[1/8] 检查certbot安装状态...${NC}"
if command -v certbot &> /dev/null; then
    echo -e "${GREEN}✅ certbot已安装${NC}"
else
    echo -e "${YELLOW}⚠️  certbot未安装，正在安装...${NC}"
    apt update -qq
    apt install certbot python3-certbot-nginx -y -qq
    echo -e "${GREEN}✅ certbot安装完成${NC}"
fi
echo ""

# 步骤2：检查证书
echo -e "${BLUE}[2/8] 检查SSL证书...${NC}"
if [ -f "/etc/letsencrypt/live/sxylab.com/fullchain.pem" ]; then
    echo -e "${GREEN}✅ SSL证书存在${NC}"
    
    # 显示证书信息
    EXPIRY_DATE=$(openssl x509 -in /etc/letsencrypt/live/sxylab.com/fullchain.pem -noout -enddate | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))
    echo -e "   过期时间: ${YELLOW}$EXPIRY_DATE${NC}"
    echo -e "   剩余天数: ${YELLOW}$DAYS_LEFT 天${NC}"
else
    echo -e "${RED}❌ SSL证书不存在${NC}"
    echo "请先申请证书："
    echo "  systemctl stop nginx"
    echo "  certbot certonly --standalone -d sxylab.com -d www.sxylab.com"
    echo "  systemctl start nginx"
    exit 1
fi
echo ""

# 步骤3：创建certbot验证目录
echo -e "${BLUE}[3/8] 创建certbot验证目录...${NC}"
mkdir -p /var/www/certbot
chmod 755 /var/www/certbot
echo -e "${GREEN}✅ 验证目录已创建: /var/www/certbot${NC}"
echo ""

# 步骤4：配置systemd timer
echo -e "${BLUE}[4/8] 配置systemd自动续期...${NC}"

if systemctl list-unit-files | grep -q "certbot.timer"; then
    # 使用系统自带的timer
    systemctl enable certbot.timer 2>/dev/null || true
    systemctl start certbot.timer 2>/dev/null || true
    echo -e "${GREEN}✅ certbot.timer已启用${NC}"
else
    # 创建自定义timer
    cat > /etc/systemd/system/certbot-renew.service << 'EOFSERVICE'
[Unit]
Description=Certbot Renewal
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/certbot renew --quiet --post-hook "systemctl reload nginx"
EOFSERVICE

    cat > /etc/systemd/system/certbot-renew.timer << 'EOFTIMER'
[Unit]
Description=Certbot Renewal Timer

[Timer]
OnCalendar=daily
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
EOFTIMER

    systemctl daemon-reload
    systemctl enable certbot-renew.timer
    systemctl start certbot-renew.timer
    echo -e "${GREEN}✅ certbot-renew.timer已创建并启用${NC}"
fi
echo ""

# 步骤5：配置cron任务（备用）
echo -e "${BLUE}[5/8] 配置cron任务（备用）...${NC}"
if crontab -l 2>/dev/null | grep -q "certbot renew"; then
    echo -e "${GREEN}✅ cron任务已存在${NC}"
else
    (crontab -l 2>/dev/null; echo "0 3 * * * /usr/bin/certbot renew --quiet --post-hook 'systemctl reload nginx' >> /var/log/certbot-cron.log 2>&1") | crontab -
    echo -e "${GREEN}✅ cron任务已添加（每天凌晨3点）${NC}"
fi
echo ""

# 步骤6：创建续期后钩子
echo -e "${BLUE}[6/8] 创建续期后钩子...${NC}"
mkdir -p /etc/letsencrypt/renewal-hooks/post

cat > /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh << 'EOFHOOK'
#!/bin/bash
# 证书续期后自动重新加载nginx

systemctl reload nginx

# 记录日志
echo "$(date '+%Y-%m-%d %H:%M:%S'): SSL证书已续期，nginx已重新加载" >> /var/log/certbot-renew.log
EOFHOOK

chmod +x /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh
echo -e "${GREEN}✅ 续期后钩子已创建${NC}"
echo ""

# 步骤7：创建监控脚本
echo -e "${BLUE}[7/8] 创建证书监控脚本...${NC}"
cat > /usr/local/bin/check-ssl-expiry.sh << 'EOFMONITOR'
#!/bin/bash

CERT_FILE="/etc/letsencrypt/live/sxylab.com/fullchain.pem"

if [ ! -f "$CERT_FILE" ]; then
    echo "❌ 证书文件不存在: $CERT_FILE"
    exit 1
fi

EXPIRY_DATE=$(openssl x509 -in "$CERT_FILE" -noout -enddate | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))

echo "=========================================="
echo "SSL证书状态"
echo "=========================================="
echo "域名: sxylab.com"
echo "过期时间: $EXPIRY_DATE"
echo "剩余天数: $DAYS_LEFT 天"
echo ""

if [ $DAYS_LEFT -lt 7 ]; then
    echo "❌ 紧急：证书即将过期！"
    exit 2
elif [ $DAYS_LEFT -lt 30 ]; then
    echo "⚠️  警告：证书即将过期！"
    exit 1
else
    echo "✅ 证书有效期充足"
    exit 0
fi
EOFMONITOR

chmod +x /usr/local/bin/check-ssl-expiry.sh
echo -e "${GREEN}✅ 监控脚本已创建: /usr/local/bin/check-ssl-expiry.sh${NC}"
echo ""

# 步骤8：测试续期
echo -e "${BLUE}[8/8] 测试证书续期...${NC}"
if certbot renew --dry-run 2>&1 | grep -q "Congratulations"; then
    echo -e "${GREEN}✅ 证书续期测试成功！${NC}"
else
    echo -e "${YELLOW}⚠️  证书续期测试失败${NC}"
    echo ""
    echo "可能的原因："
    echo "1. nginx配置中HTTP完全重定向到HTTPS，导致certbot无法验证"
    echo "2. 防火墙阻止了80端口"
    echo ""
    echo "解决方案："
    echo "在nginx.conf的HTTP服务器块中添加："
    echo ""
    echo "    location /.well-known/acme-challenge/ {"
    echo "        root /var/www/certbot;"
    echo "    }"
    echo ""
    echo "然后执行: nginx -t && systemctl reload nginx"
    echo ""
fi
echo ""

# 显示配置状态
echo -e "${BLUE}=========================================="
echo "配置完成！当前状态："
echo "==========================================${NC}"
echo ""

echo -e "${YELLOW}1. 证书信息：${NC}"
certbot certificates 2>/dev/null | grep -A 5 "Certificate Name: sxylab.com" || echo "无法获取证书信息"
echo ""

echo -e "${YELLOW}2. 自动续期任务：${NC}"
if systemctl is-active --quiet certbot.timer 2>/dev/null; then
    echo -e "   ${GREEN}✅ certbot.timer 运行中${NC}"
    systemctl list-timers certbot.timer --no-pager 2>/dev/null | grep certbot || true
elif systemctl is-active --quiet certbot-renew.timer 2>/dev/null; then
    echo -e "   ${GREEN}✅ certbot-renew.timer 运行中${NC}"
    systemctl list-timers certbot-renew.timer --no-pager 2>/dev/null | grep certbot || true
else
    echo -e "   ${YELLOW}⚠️  systemd timer未运行${NC}"
fi
echo ""

echo -e "${YELLOW}3. Cron任务：${NC}"
if crontab -l 2>/dev/null | grep certbot; then
    echo -e "   ${GREEN}✅ cron任务已配置${NC}"
else
    echo -e "   ${YELLOW}⚠️  cron任务未配置${NC}"
fi
echo ""

echo -e "${YELLOW}4. 证书有效期：${NC}"
/usr/local/bin/check-ssl-expiry.sh
echo ""

# 显示使用说明
echo -e "${BLUE}=========================================="
echo "使用说明"
echo "==========================================${NC}"
echo ""
echo -e "${GREEN}✅ SSL自动续期已配置完成！${NC}"
echo ""
echo "📋 工作原理："
echo "   • systemd timer每天自动检查证书"
echo "   • cron任务每天凌晨3点检查（备用）"
echo "   • 证书在过期前30天自动续期"
echo "   • 续期成功后自动重新加载nginx"
echo ""
echo "💡 常用命令："
echo "   查看证书状态:     certbot certificates"
echo "   手动续期:         certbot renew"
echo "   测试续期:         certbot renew --dry-run"
echo "   查看timer状态:    systemctl status certbot.timer"
echo "   查看证书过期时间: /usr/local/bin/check-ssl-expiry.sh"
echo "   查看续期日志:     tail -f /var/log/certbot-renew.log"
echo ""
echo "📧 提醒："
echo "   • 确保能收到certbot的邮件通知"
echo "   • 建议每月检查一次证书状态"
echo "   • 证书过期前会自动续期，无需手动操作"
echo ""
echo -e "${GREEN}🎉 配置完成！您的SSL证书将自动续期。${NC}"
echo ""

