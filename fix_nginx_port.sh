#!/bin/bash

echo "=========================================="
echo "🔧 修复 Nginx 端口配置"
echo "=========================================="
echo ""

echo "1. 查找所有包含 5000 端口的 Nginx 配置"
echo "----------------------------------------"
sudo grep -r "proxy_pass.*5000" /etc/nginx/ 2>/dev/null || echo "没有找到 5000 端口配置"
echo ""

echo "2. 查看当前 Nginx 实际使用的配置"
echo "----------------------------------------"
sudo nginx -T 2>/dev/null | grep -B 5 -A 2 "proxy_pass"
echo ""

echo "3. 修复所有 Nginx 配置文件中的端口"
echo "----------------------------------------"
# 修复 sites-available
sudo sed -i 's/proxy_pass http:\/\/127.0.0.1:5000/proxy_pass http:\/\/127.0.0.1:5002/g' /etc/nginx/sites-available/* 2>/dev/null
# 修复 sites-enabled
sudo sed -i 's/proxy_pass http:\/\/127.0.0.1:5000/proxy_pass http:\/\/127.0.0.1:5002/g' /etc/nginx/sites-enabled/* 2>/dev/null
# 修复 conf.d
sudo sed -i 's/proxy_pass http:\/\/127.0.0.1:5000/proxy_pass http:\/\/127.0.0.1:5002/g' /etc/nginx/conf.d/* 2>/dev/null
echo "✅ 已修复所有配置文件"
echo ""

echo "4. 验证修改后的配置"
echo "----------------------------------------"
sudo grep -r "proxy_pass" /etc/nginx/sites-available/ /etc/nginx/sites-enabled/ 2>/dev/null | grep -v "#"
echo ""

echo "5. 测试 Nginx 配置"
echo "----------------------------------------"
sudo nginx -t
echo ""

echo "6. 停止 Nginx"
echo "----------------------------------------"
sudo systemctl stop nginx
sleep 2
echo "✅ Nginx 已停止"
echo ""

echo "7. 清除 Nginx 缓存"
echo "----------------------------------------"
sudo rm -rf /var/cache/nginx/* 2>/dev/null || echo "没有缓存需要清除"
echo "✅ 缓存已清除"
echo ""

echo "8. 启动 Nginx"
echo "----------------------------------------"
sudo systemctl start nginx
sleep 2
sudo systemctl status nginx --no-pager | head -15
echo ""

echo "9. 验证 Nginx 实际使用的配置"
echo "----------------------------------------"
sudo nginx -T 2>/dev/null | grep -A 2 "proxy_pass" | head -20
echo ""

echo "10. 测试本地访问"
echo "----------------------------------------"
curl -I http://127.0.0.1:5002/ 2>&1 | head -10
echo ""

echo "11. 测试 HTTPS 访问"
echo "----------------------------------------"
curl -I https://www.sxylab.com/ 2>&1 | head -10
echo ""

echo "12. 查看 Nginx 错误日志"
echo "----------------------------------------"
sudo tail -30 /var/log/nginx/error.log
echo ""

echo "13. 检查所有监听端口"
echo "----------------------------------------"
sudo netstat -tlnp | grep -E "nginx|gunicorn|5002|5000"
echo ""

echo "=========================================="
echo "修复完成"
echo "=========================================="
echo ""
echo "📋 如果还是 502 错误:"
echo "1. 检查上面第 2 步和第 9 步的输出,确认 proxy_pass 是 5002"
echo "2. 检查第 12 步的错误日志,查看具体错误"
echo "3. 确认 Gunicorn 在 5002 端口运行"
echo ""

