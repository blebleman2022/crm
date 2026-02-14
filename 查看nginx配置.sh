#!/bin/bash

# 快速查看Nginx配置
# 用于诊断301重定向问题

echo "=========================================="
echo "Nginx配置查看工具"
echo "=========================================="
echo ""

echo "1. 查找Nginx配置文件..."
echo ""

# 查找所有可能的配置文件
echo "主配置文件:"
ls -lh /etc/nginx/nginx.conf 2>/dev/null || echo "  未找到"

echo ""
echo "站点配置文件:"
ls -lh /etc/nginx/sites-enabled/ 2>/dev/null || echo "  目录不存在"
ls -lh /etc/nginx/sites-available/ 2>/dev/null || echo "  目录不存在"
ls -lh /etc/nginx/conf.d/ 2>/dev/null || echo "  目录不存在"

echo ""
echo "=========================================="
echo "2. 显示nginx.conf内容"
echo "=========================================="
echo ""

if [ -f /etc/nginx/nginx.conf ]; then
    cat /etc/nginx/nginx.conf
else
    echo "配置文件不存在"
fi

echo ""
echo "=========================================="
echo "3. 查找sxylab.com相关配置"
echo "=========================================="
echo ""

# 在所有配置文件中查找sxylab.com
find /etc/nginx -type f -name "*.conf" -o -name "sxylab*" 2>/dev/null | while read file; do
    if grep -q "sxylab" "$file" 2>/dev/null; then
        echo "文件: $file"
        echo "---"
        cat "$file"
        echo ""
    fi
done

echo ""
echo "=========================================="
echo "4. 测试访问"
echo "=========================================="
echo ""

echo "HTTP访问测试:"
curl -I http://localhost/static/images/custom-logo.png 2>&1 | head -10

echo ""
echo "HTTPS访问测试:"
curl -Ik https://localhost/static/images/custom-logo.png 2>&1 | head -10

echo ""
echo "=========================================="
echo "完成"
echo "=========================================="

