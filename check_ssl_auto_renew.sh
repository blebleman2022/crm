#!/bin/bash

# SSL证书自动续期检查脚本

echo "=========================================="
echo "SSL证书自动续期检查"
echo "=========================================="
echo ""

# 1. 测试证书续期
echo "1. 测试证书续期（模拟）..."
echo "---"
if certbot renew --dry-run 2>&1 | grep -q "Congratulations"; then
    echo "✅ 证书续期测试成功！"
else
    echo "❌ 证书续期测试失败！"
    echo "请查看详细输出："
    certbot renew --dry-run
fi
echo ""

# 2. 查看证书信息
echo "2. 查看证书信息..."
echo "---"
certbot certificates
echo ""

# 3. 检查certbot timer
echo "3. 检查certbot定时任务..."
echo "---"
if systemctl is-active --quiet certbot.timer; then
    echo "✅ certbot.timer 正在运行"
    systemctl status certbot.timer --no-pager | head -10
    echo ""
    echo "下次运行时间："
    systemctl list-timers certbot.timer --no-pager
else
    echo "⚠️  certbot.timer 未运行"
    echo "尝试启用..."
    systemctl enable certbot.timer
    systemctl start certbot.timer
fi
echo ""

# 4. 检查cron任务
echo "4. 检查cron任务..."
echo "---"
if [ -f "/etc/cron.d/certbot" ]; then
    echo "✅ 找到certbot cron任务："
    cat /etc/cron.d/certbot
else
    echo "⚠️  未找到certbot cron任务"
fi
echo ""

# 5. 检查证书有效期
echo "5. 检查证书有效期..."
echo "---"
if [ -f "/etc/letsencrypt/live/sxylab.com/fullchain.pem" ]; then
    echo "证书路径: /etc/letsencrypt/live/sxylab.com/fullchain.pem"
    openssl x509 -in /etc/letsencrypt/live/sxylab.com/fullchain.pem -noout -dates
    echo ""
    EXPIRY_DATE=$(openssl x509 -in /etc/letsencrypt/live/sxylab.com/fullchain.pem -noout -enddate | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))
    echo "剩余天数: $DAYS_LEFT 天"
    
    if [ $DAYS_LEFT -lt 30 ]; then
        echo "⚠️  证书即将过期，建议手动续期"
    else
        echo "✅ 证书有效期充足"
    fi
else
    echo "❌ 证书文件不存在"
fi
echo ""

# 6. 检查nginx配置
echo "6. 检查nginx SSL配置..."
echo "---"
if nginx -t 2>&1 | grep -q "successful"; then
    echo "✅ Nginx配置正确"
else
    echo "❌ Nginx配置有误"
    nginx -t
fi
echo ""

# 7. 测试HTTPS访问
echo "7. 测试HTTPS访问..."
echo "---"
if curl -I https://sxylab.com 2>&1 | grep -q "HTTP/2"; then
    echo "✅ HTTPS访问正常"
else
    echo "⚠️  HTTPS访问可能有问题"
fi
echo ""

echo "=========================================="
echo "检查完成"
echo "=========================================="
echo ""

# 总结
echo "📋 总结："
echo "---"
echo "如果所有检查都显示 ✅，说明自动续期配置正确。"
echo "certbot会在证书过期前30天自动续期。"
echo ""
echo "💡 建议："
echo "1. 每月检查一次证书状态"
echo "2. 确保收到certbot的邮件通知"
echo "3. 证书过期前手动测试续期"
echo ""

