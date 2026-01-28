#!/bin/bash

# 修复Nginx 301重定向导致的Logo无法访问问题
# 问题：静态文件配置存在，但返回301重定向

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "${BLUE}=========================================="
echo "修复Nginx 301重定向问题"
echo "==========================================${NC}"
echo ""

# 检查root权限
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ 请使用root权限运行${NC}"
    exit 1
fi

NGINX_CONF="/etc/nginx/nginx.conf"

echo -e "${BLUE}[1/5] 查看当前Nginx配置...${NC}"

# 查找所有server块
echo "查找server块配置..."
grep -n "server {" "$NGINX_CONF" || echo "未找到server块"

echo ""
echo -e "${BLUE}[2/5] 检查是否有HTTP到HTTPS重定向...${NC}"

# 检查是否有return 301重定向
if grep -q "return 301" "$NGINX_CONF"; then
    echo -e "${YELLOW}⚠️  发现301重定向配置${NC}"
    grep -n "return 301" "$NGINX_CONF"
    echo ""
    echo -e "${YELLOW}这可能导致静态文件访问被重定向${NC}"
else
    echo -e "${GREEN}✅ 未发现301重定向${NC}"
fi

echo ""
echo -e "${BLUE}[3/5] 显示完整的Nginx配置...${NC}"
echo "配置文件: $NGINX_CONF"
echo "---"
cat "$NGINX_CONF"
echo "---"

echo ""
echo -e "${BLUE}[4/5] 测试不同方式访问...${NC}"

# 测试HTTP
echo "测试 HTTP (localhost):"
curl -I http://localhost/static/images/custom-logo.png 2>&1 | head -5

echo ""
echo "测试 HTTP (127.0.0.1):"
curl -I http://127.0.0.1/static/images/custom-logo.png 2>&1 | head -5

echo ""
echo "测试 HTTPS (localhost):"
curl -Ik https://localhost/static/images/custom-logo.png 2>&1 | head -5

echo ""
echo -e "${BLUE}[5/5] 解决方案...${NC}"
echo ""

cat << 'EOF'
问题分析：
---------
返回301说明请求被重定向了，通常是因为：
1. HTTP被重定向到HTTPS
2. 静态文件配置的位置不对（在重定向之后）

解决方案：
---------
需要确保静态文件配置在重定向之前，或者在HTTPS server块中也配置静态文件。

推荐的Nginx配置结构：

# HTTP server块（端口80）
server {
    listen 80;
    server_name sxylab.com www.sxylab.com;

    # 静态文件配置（在重定向之前）
    location /static/ {
        alias /root/crm/static/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # 其他请求重定向到HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server块（端口443）
server {
    listen 443 ssl http2;
    server_name sxylab.com www.sxylab.com;

    ssl_certificate /etc/letsencrypt/live/sxylab.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sxylab.com/privkey.pem;

    # 静态文件配置
    location /static/ {
        alias /root/crm/static/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # 代理到Flask应用
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}

执行步骤：
---------
1. 备份当前配置：
   cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak.$(date +%Y%m%d_%H%M%S)

2. 编辑配置文件：
   nano /etc/nginx/nginx.conf

3. 按照上面的结构调整配置

4. 测试配置：
   nginx -t

5. 重载Nginx：
   systemctl reload nginx

6. 测试访问：
   curl -I https://sxylab.com/static/images/custom-logo.png

EOF

echo ""
echo -e "${YELLOW}=========================================="
echo "下一步操作"
echo "==========================================${NC}"
echo ""
echo "1. 查看上面显示的完整Nginx配置"
echo "2. 根据解决方案调整配置文件"
echo "3. 或者使用以下命令查看配置："
echo "   cat /etc/nginx/nginx.conf"
echo ""

