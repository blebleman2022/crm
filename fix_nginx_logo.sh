#!/bin/bash

# Nginx Logo显示问题修复脚本
# 修复Nginx配置以支持静态文件访问

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "${BLUE}=========================================="
echo "Nginx Logo显示问题修复"
echo "==========================================${NC}"
echo ""

# 检查root权限
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ 请使用root权限运行${NC}"
    exit 1
fi

# 步骤1：检查Nginx配置文件位置
echo -e "${BLUE}[1/6] 检查Nginx配置...${NC}"

NGINX_CONF="/etc/nginx/nginx.conf"
SITES_AVAILABLE="/etc/nginx/sites-available"
SITES_ENABLED="/etc/nginx/sites-enabled"

if [ ! -f "$NGINX_CONF" ]; then
    echo -e "${RED}❌ Nginx配置文件不存在: $NGINX_CONF${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Nginx主配置文件存在${NC}"

# 步骤2：查找CRM相关配置
echo -e "${BLUE}[2/6] 查找CRM配置文件...${NC}"

CRM_CONF=""
if [ -f "$SITES_ENABLED/sxylab.com" ]; then
    CRM_CONF="$SITES_ENABLED/sxylab.com"
    echo -e "${GREEN}✅ 找到配置: $CRM_CONF${NC}"
elif [ -f "$SITES_AVAILABLE/sxylab.com" ]; then
    CRM_CONF="$SITES_AVAILABLE/sxylab.com"
    echo -e "${YELLOW}⚠️  配置存在但未启用: $CRM_CONF${NC}"
else
    echo -e "${YELLOW}⚠️  未找到sxylab.com配置文件${NC}"
    echo "将在nginx.conf中添加配置"
fi

# 步骤3：检查当前配置中是否有静态文件配置
echo -e "${BLUE}[3/6] 检查静态文件配置...${NC}"

HAS_STATIC_CONFIG=false

if [ -n "$CRM_CONF" ] && [ -f "$CRM_CONF" ]; then
    if grep -q "location /static/" "$CRM_CONF"; then
        echo -e "${GREEN}✅ 静态文件配置已存在${NC}"
        HAS_STATIC_CONFIG=true
        echo "当前配置："
        grep -A 3 "location /static/" "$CRM_CONF"
    fi
fi

if [ "$HAS_STATIC_CONFIG" = false ]; then
    if grep -q "location /static/" "$NGINX_CONF"; then
        echo -e "${GREEN}✅ 静态文件配置在nginx.conf中${NC}"
        HAS_STATIC_CONFIG=true
    fi
fi

# 步骤4：添加或修复静态文件配置
echo -e "${BLUE}[4/6] 配置静态文件访问...${NC}"

if [ "$HAS_STATIC_CONFIG" = false ]; then
    echo -e "${YELLOW}⚠️  静态文件配置缺失，正在添加...${NC}"
    
    # 备份nginx.conf
    cp "$NGINX_CONF" "$NGINX_CONF.bak.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}✅ 已备份nginx.conf${NC}"
    
    # 在http块中添加静态文件配置
    # 查找server块并在其中添加location配置
    cat >> /tmp/static_location.conf << 'EOF'
        location /static/ {
            alias /root/crm/static/;
            expires 7d;
            add_header Cache-Control "public";
            access_log off;
        }
EOF
    
    echo -e "${YELLOW}请手动将以下配置添加到Nginx server块中：${NC}"
    echo ""
    cat /tmp/static_location.conf
    echo ""
    echo -e "${YELLOW}配置文件位置：${NC}"
    if [ -n "$CRM_CONF" ]; then
        echo "$CRM_CONF"
    else
        echo "$NGINX_CONF"
    fi
    echo ""
    
else
    echo -e "${GREEN}✅ 静态文件配置已存在，无需修改${NC}"
fi

# 步骤5：检查并修复文件权限
echo -e "${BLUE}[5/6] 检查文件权限...${NC}"

chmod 755 /root/crm/static
chmod 755 /root/crm/static/images
chmod 644 /root/crm/static/images/*.png 2>/dev/null || true
chmod 644 /root/crm/static/images/*.jpg 2>/dev/null || true

echo -e "${GREEN}✅ 文件权限已修复${NC}"

# 步骤6：测试Nginx配置并重载
echo -e "${BLUE}[6/6] 测试并重载Nginx...${NC}"

if nginx -t 2>&1 | grep -q "successful"; then
    echo -e "${GREEN}✅ Nginx配置测试通过${NC}"
    
    echo "正在重载Nginx..."
    systemctl reload nginx
    echo -e "${GREEN}✅ Nginx已重载${NC}"
else
    echo -e "${RED}❌ Nginx配置测试失败${NC}"
    nginx -t
    exit 1
fi

# 最终测试
echo ""
echo -e "${BLUE}=========================================="
echo "测试结果"
echo "==========================================${NC}"
echo ""

echo "测试静态文件访问..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost/static/images/custom-logo.png" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Logo可以访问 (HTTP $HTTP_CODE)${NC}"
    echo ""
    echo -e "${GREEN}🎉 修复成功！${NC}"
    echo ""
    echo "测试URL："
    echo "  https://sxylab.com/static/images/custom-logo.png"
    echo ""
    echo "如果浏览器仍看不到，请清除缓存并强制刷新（Ctrl+F5）"
else
    echo -e "${RED}❌ Logo无法访问 (HTTP $HTTP_CODE)${NC}"
    echo ""
    echo "可能的原因："
    echo "1. Nginx配置需要手动添加（见上方提示）"
    echo "2. 需要检查Nginx错误日志："
    echo "   tail -f /var/log/nginx/error.log"
fi

echo ""

