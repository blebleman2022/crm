#!/bin/bash

echo "=========================================="
echo "🔧 修复 502 Bad Gateway 错误"
echo "=========================================="
echo ""

cd /root/crm

echo "1. 验证数据库字段"
echo "----------------------------------------"
sqlite3 instance/edu_crm.db "PRAGMA table_info(users);" | grep -E "is_private_owner|teacher_scope"
echo ""

echo "2. 停止所有服务"
echo "----------------------------------------"
sudo systemctl stop crm
sudo systemctl stop nginx
sleep 3
echo "✅ 服务已停止"
echo ""

echo "3. 检查端口占用"
echo "----------------------------------------"
sudo netstat -tlnp | grep -E "5002|80|443" || echo "没有端口占用"
echo ""

echo "4. 启动 Gunicorn"
echo "----------------------------------------"
sudo systemctl start crm
sleep 3
sudo systemctl status crm --no-pager | head -20
echo ""

echo "5. 验证 Gunicorn 监听"
echo "----------------------------------------"
sudo netstat -tlnp | grep 5002
echo ""

echo "6. 测试本地访问 Gunicorn"
echo "----------------------------------------"
curl -I http://127.0.0.1:5002/ 2>&1 | head -10
echo ""

echo "7. 重新加载 Nginx 配置"
echo "----------------------------------------"
sudo nginx -t
sudo systemctl start nginx
sleep 2
sudo systemctl status nginx --no-pager | head -20
echo ""

echo "8. 测试 Nginx 到 Gunicorn 的连接"
echo "----------------------------------------"
sudo -u www-data curl -I http://127.0.0.1:5002/ 2>&1 | head -10
echo ""

echo "9. 测试 HTTPS 访问"
echo "----------------------------------------"
curl -I https://www.sxylab.com/ 2>&1 | head -15
echo ""

echo "10. 查看最新日志"
echo "----------------------------------------"
echo "=== Gunicorn 错误日志 ==="
tail -20 /root/crm/logs/error.log
echo ""
echo "=== Nginx 错误日志 ==="
sudo tail -20 /var/log/nginx/error.log
echo ""

echo "=========================================="
echo "修复完成"
echo "=========================================="

