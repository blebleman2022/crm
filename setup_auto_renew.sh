#!/bin/bash
# SSL 证书自动续期配置脚本
# 配置 Certbot 自动续期并在续期后自动重启 Nginx
# 使用方法: sudo bash setup_auto_renew.sh

set -e

echo "============================================================"
echo "⏰ SSL 证书自动续期配置脚本"
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
    echo "   sudo bash setup_auto_renew.sh"
    exit 1
fi

echo "📋 本脚本将配置:"
echo "   • Certbot 自动续期定时器"
echo "   • 续期后自动重启 Nginx"
echo "   • 每日检查证书有效期"
echo "   • 证书过期前 30 天自动续期"
echo ""

# 1. 检查 Certbot 是否安装
echo "🔍 第1步: 检查 Certbot..."
echo "-----------------------------------------------------------"

if ! command -v certbot &> /dev/null; then
    echo -e "${RED}❌ Certbot 未安装${NC}"
    echo "正在安装 Certbot..."
    apt update
    apt install certbot python3-certbot-nginx -y
    echo -e "${GREEN}✅ Certbot 已安装${NC}"
else
    echo -e "${GREEN}✅ Certbot 已安装${NC}"
    echo "   版本: $(certbot --version 2>&1)"
fi

echo ""

# 2. 创建续期后钩子脚本
echo "📝 第2步: 创建续期后钩子脚本..."
echo "-----------------------------------------------------------"

# 创建 renewal hooks 目录
mkdir -p /etc/letsencrypt/renewal-hooks/deploy

# 创建 Nginx 重启脚本
cat > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh << 'EOF'
#!/bin/bash
# Certbot 续期后自动重启 Nginx
# 此脚本会在证书成功续期后自动执行

echo "$(date): SSL 证书已续期,正在重启 Nginx..." >> /var/log/certbot-renew.log

# 测试 Nginx 配置
if nginx -t 2>&1 >> /var/log/certbot-renew.log; then
    # 重启 Nginx
    systemctl reload nginx
    echo "$(date): Nginx 已成功重启" >> /var/log/certbot-renew.log
else
    echo "$(date): Nginx 配置测试失败,未重启" >> /var/log/certbot-renew.log
    exit 1
fi

# 发送通知 (可选)
# echo "SSL 证书已自动续期并重启 Nginx" | mail -s "SSL 证书续期成功" admin@sxylab.com
EOF

# 添加执行权限
chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh

echo -e "${GREEN}✅ 续期后钩子脚本已创建${NC}"
echo "   路径: /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh"

echo ""

# 3. 配置 Certbot 自动续期
echo "⚙️  第3步: 配置 Certbot 自动续期..."
echo "-----------------------------------------------------------"

# 检查 systemd timer 是否存在
if [ -f "/lib/systemd/system/certbot.timer" ]; then
    echo -e "${GREEN}✅ Certbot systemd timer 已存在${NC}"
else
    echo "创建 Certbot systemd timer..."
    
    # 创建 timer 文件
    cat > /lib/systemd/system/certbot.timer << 'EOF'
[Unit]
Description=Run certbot twice daily
After=network.target

[Timer]
OnCalendar=*-*-* 00,12:00:00
RandomizedDelaySec=43200
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # 创建 service 文件
    cat > /lib/systemd/system/certbot.service << 'EOF'
[Unit]
Description=Certbot
Documentation=https://certbot.eff.org/docs/

[Service]
Type=oneshot
ExecStart=/usr/bin/certbot renew --quiet --deploy-hook "/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh"
PrivateTmp=true
EOF

    systemctl daemon-reload
    echo -e "${GREEN}✅ Certbot systemd timer 已创建${NC}"
fi

# 启用并启动 timer
systemctl enable certbot.timer
systemctl start certbot.timer

echo -e "${GREEN}✅ Certbot 自动续期已启用${NC}"

# 显示 timer 状态
echo ""
echo "   Timer 状态:"
systemctl status certbot.timer --no-pager | grep -E "Active|Trigger" | sed 's/^/   /'

echo ""

# 4. 创建日志文件
echo "📄 第4步: 创建日志文件..."
echo "-----------------------------------------------------------"

touch /var/log/certbot-renew.log
chmod 644 /var/log/certbot-renew.log

echo -e "${GREEN}✅ 日志文件已创建${NC}"
echo "   路径: /var/log/certbot-renew.log"

echo ""

# 5. 测试自动续期
echo "🧪 第5步: 测试自动续期配置..."
echo "-----------------------------------------------------------"

echo "正在测试续期流程 (不会实际更新证书)..."

if certbot renew --dry-run --deploy-hook "/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh" 2>&1 | tee /tmp/certbot-test.log; then
    echo -e "${GREEN}✅ 自动续期测试成功!${NC}"
else
    echo -e "${YELLOW}⚠️  自动续期测试有警告,但配置已完成${NC}"
fi

echo ""

# 6. 创建手动续期脚本
echo "🔧 第6步: 创建手动续期脚本..."
echo "-----------------------------------------------------------"

cat > /root/renew_ssl_now.sh << 'EOF'
#!/bin/bash
# 立即手动续期 SSL 证书
# 使用方法: sudo bash /root/renew_ssl_now.sh

echo "🔄 正在强制续期 SSL 证书..."
echo ""

certbot renew --force-renewal --deploy-hook "/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 证书续期成功!"
    echo ""
    echo "证书信息:"
    certbot certificates
else
    echo ""
    echo "❌ 证书续期失败,请检查日志"
    tail -20 /var/log/letsencrypt/letsencrypt.log
fi
EOF

chmod +x /root/renew_ssl_now.sh

echo -e "${GREEN}✅ 手动续期脚本已创建${NC}"
echo "   路径: /root/renew_ssl_now.sh"
echo "   使用: sudo bash /root/renew_ssl_now.sh"

echo ""

# 7. 创建证书监控脚本
echo "📊 第7步: 创建证书监控脚本..."
echo "-----------------------------------------------------------"

cat > /root/check_ssl_status.sh << 'EOF'
#!/bin/bash
# 检查 SSL 证书状态
# 使用方法: bash /root/check_ssl_status.sh

echo "============================================================"
echo "📊 SSL 证书状态检查"
echo "============================================================"
echo ""

# 检查所有证书
certbot certificates

echo ""
echo "-----------------------------------------------------------"
echo "下次自动续期时间:"
systemctl status certbot.timer | grep "Trigger:" | sed 's/^//'

echo ""
echo "最近的续期日志:"
tail -10 /var/log/certbot-renew.log 2>/dev/null || echo "暂无续期日志"

echo ""
echo "============================================================"
EOF

chmod +x /root/check_ssl_status.sh

echo -e "${GREEN}✅ 证书监控脚本已创建${NC}"
echo "   路径: /root/check_ssl_status.sh"
echo "   使用: bash /root/check_ssl_status.sh"

echo ""

# 完成
echo "============================================================"
echo "✅ SSL 证书自动续期配置完成!"
echo "============================================================"
echo ""
echo "📊 配置总结:"
echo ""
echo "1️⃣ 自动续期:"
echo "   • 每天 00:00 和 12:00 自动检查证书"
echo "   • 证书过期前 30 天自动续期"
echo "   • 续期后自动重启 Nginx"
echo ""
echo "2️⃣ 日志文件:"
echo "   • 续期日志: /var/log/certbot-renew.log"
echo "   • Certbot 日志: /var/log/letsencrypt/letsencrypt.log"
echo ""
echo "3️⃣ 实用脚本:"
echo "   • 立即续期: sudo bash /root/renew_ssl_now.sh"
echo "   • 检查状态: bash /root/check_ssl_status.sh"
echo ""
echo "4️⃣ 查看自动续期状态:"
echo "   • systemctl status certbot.timer"
echo "   • journalctl -u certbot.service"
echo ""
echo "💡 提示:"
echo "   • 证书会在到期前 30 天自动续期"
echo "   • 无需手动干预,完全自动化"
echo "   • 可以随时运行 /root/check_ssl_status.sh 检查状态"
echo ""

