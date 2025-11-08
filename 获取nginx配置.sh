#!/bin/bash

echo "=========================================="
echo "获取Nginx配置信息"
echo "=========================================="
echo ""

echo "1. 查看所有server配置："
echo "---"
grep -n "server {" /etc/nginx/nginx.conf
echo ""

echo "2. 查看IP访问的server配置（默认配置）："
echo "---"
grep -A 30 "server {" /etc/nginx/nginx.conf | head -35
echo ""

echo "3. 查看sxylab.com的server配置："
echo "---"
if [ -f "/etc/nginx/sites-enabled/sxylab.com" ]; then
    cat /etc/nginx/sites-enabled/sxylab.com
else
    echo "文件不存在"
fi
echo ""

echo "4. 查看nginx.conf中是否包含sxylab.com配置："
echo "---"
grep -n "sxylab.com" /etc/nginx/nginx.conf
echo ""

echo "=========================================="
echo "完成"
echo "=========================================="

