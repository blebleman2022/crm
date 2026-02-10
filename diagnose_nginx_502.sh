#!/bin/bash

echo "=========================================="
echo "🔍 诊断 Nginx 502 错误"
echo "=========================================="
echo ""

echo "1. 检查 SELinux 状态"
echo "----------------------------------------"
getenforce 2>/dev/null || echo "SELinux 未安装"
echo ""

echo "2. 检查 AppArmor 状态"
echo "----------------------------------------"
sudo aa-status 2>/dev/null | grep nginx || echo "AppArmor 未限制 nginx 或未安装"
echo ""

echo "3. 测试 TCP 连接到 5002 端口"
echo "----------------------------------------"
timeout 2 bash -c 'exec 3<>/dev/tcp/127.0.0.1/5002 && echo "✅ TCP 连接成功" || echo "❌ TCP 连接失败"'
echo ""

echo "4. 测试 www-data 用户的 TCP 连接"
echo "----------------------------------------"
sudo -u www-data timeout 2 bash -c 'exec 3<>/dev/tcp/127.0.0.1/5002 && echo "✅ www-data TCP 连接成功" || echo "❌ www-data TCP 连接失败"'
echo ""

echo "5. 查看最近的 502 访问记录"
echo "----------------------------------------"
sudo grep "502" /var/log/nginx/access.log | tail -5
echo ""

echo "6. 检查 Nginx upstream 配置"
echo "----------------------------------------"
sudo nginx -T 2>/dev/null | grep -A 5 "proxy_pass"
echo ""

echo "7. 启用 Nginx 调试日志"
echo "----------------------------------------"
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup
sudo sed -i 's/error_log.*/error_log \/var\/log\/nginx\/error.log debug;/' /etc/nginx/nginx.conf
echo "✅ 已启用调试日志"
echo ""

echo "8. 重新加载 Nginx"
echo "----------------------------------------"
sudo systemctl reload nginx
sleep 2
echo "✅ Nginx 已重新加载"
echo ""

echo "9. 测试 HTTPS 访问并捕获错误"
echo "----------------------------------------"
curl -I https://www.sxylab.com/ 2>&1
echo ""

echo "10. 查看 Nginx 调试日志 (upstream 相关)"
echo "----------------------------------------"
sudo tail -100 /var/log/nginx/error.log | grep -E "upstream|connect|502|proxy" | tail -30
echo ""

echo "11. 查看 Nginx 调试日志 (完整最后 50 行)"
echo "----------------------------------------"
sudo tail -50 /var/log/nginx/error.log
echo ""

echo "12. 恢复正常日志级别"
echo "----------------------------------------"
sudo sed -i 's/error_log.*debug;/error_log \/var\/log\/nginx\/error.log;/' /etc/nginx/nginx.conf
sudo systemctl reload nginx
echo "✅ 已恢复正常日志级别"
echo ""

echo "13. 检查防火墙规则"
echo "----------------------------------------"
sudo iptables -L -n -v | grep -E "5002|REJECT|DROP" || echo "没有相关防火墙规则"
echo ""

echo "14. 检查系统连接跟踪"
echo "----------------------------------------"
sudo ss -tlnp | grep 5002
echo ""

echo "15. 尝试修复 SELinux 权限 (如果适用)"
echo "----------------------------------------"
sudo setsebool -P httpd_can_network_connect 1 2>/dev/null && echo "✅ SELinux 权限已设置" || echo "⚠️  不是 SELinux 系统或已设置"
echo ""

echo "16. 最终测试"
echo "----------------------------------------"
echo "=== 本地 HTTP 测试 ==="
curl -I http://127.0.0.1:5002/ 2>&1 | head -10
echo ""
echo "=== HTTPS 测试 ==="
curl -I https://www.sxylab.com/ 2>&1 | head -10
echo ""

echo "=========================================="
echo "诊断完成"
echo "=========================================="
echo ""
echo "📋 诊断总结:"
echo "1. 如果看到 'upstream' 相关错误,说明 Nginx 无法连接到 Gunicorn"
echo "2. 如果看到 'permission denied',可能是 SELinux/AppArmor 问题"
echo "3. 如果看到 'connection refused',检查 Gunicorn 是否真的在监听"
echo "4. 如果日志完全为空,可能是 Nginx 配置问题"
echo ""

