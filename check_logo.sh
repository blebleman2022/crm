#!/bin/bash

# Logo显示问题诊断脚本

echo "=========================================="
echo "Logo显示问题诊断"
echo "=========================================="
echo ""

# 1. 检查logo文件是否存在
echo "1. 检查logo文件..."
if [ -f "/root/crm/static/images/custom-logo.png" ]; then
    echo "✅ custom-logo.png 存在"
    ls -lh /root/crm/static/images/custom-logo.png
elif [ -f "/root/crm/static/images/custom-logo.jpg" ]; then
    echo "✅ custom-logo.jpg 存在"
    ls -lh /root/crm/static/images/custom-logo.jpg
elif [ -f "/root/crm/static/images/custom-logo.jpeg" ]; then
    echo "✅ custom-logo.jpeg 存在"
    ls -lh /root/crm/static/images/custom-logo.jpeg
else
    echo "❌ 未找到custom-logo文件"
    echo "当前images目录内容："
    ls -la /root/crm/static/images/
fi
echo ""

# 2. 检查目录权限
echo "2. 检查目录权限..."
ls -ld /root/crm/static/
ls -ld /root/crm/static/images/
echo ""

# 3. 检查Nginx配置
echo "3. 检查Nginx配置..."
if [ -f "/etc/nginx/sites-enabled/sxylab.com" ]; then
    echo "✅ Nginx配置文件存在"
    echo "静态文件配置："
    grep -A 3 "location /static" /etc/nginx/sites-enabled/sxylab.com
else
    echo "❌ Nginx配置文件不存在"
fi
echo ""

# 4. 测试静态文件访问
echo "4. 测试静态文件访问..."
echo "测试URL: http://localhost/static/images/custom-logo.png"
curl -I http://localhost/static/images/custom-logo.png 2>&1 | head -5
echo ""

# 5. 检查Nginx错误日志
echo "5. 检查Nginx错误日志（最近10条）..."
if [ -f "/var/log/nginx/sxylab_error.log" ]; then
    tail -10 /var/log/nginx/sxylab_error.log
else
    echo "错误日志文件不存在"
fi
echo ""

# 6. 检查CRM服务状态
echo "6. 检查CRM服务状态..."
systemctl status crm --no-pager | head -10
echo ""

echo "=========================================="
echo "诊断完成"
echo "=========================================="

