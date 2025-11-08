#!/bin/bash

# 修复403 Forbidden权限问题
# HTTPS访问静态文件返回403错误

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "${BLUE}=========================================="
echo "修复403 Forbidden权限问题"
echo "==========================================${NC}"
echo ""

# 检查root权限
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ 请使用root权限运行${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 权限检查通过${NC}"
echo ""

# 步骤1：检查nginx用户
echo -e "${BLUE}[1/6] 检查nginx运行用户...${NC}"

NGINX_USER=$(ps aux | grep nginx | grep -v grep | grep worker | awk '{print $1}' | head -1)
echo "Nginx worker进程用户: $NGINX_USER"

if [ -z "$NGINX_USER" ]; then
    echo -e "${YELLOW}⚠️  无法检测nginx用户，使用默认值: www-data${NC}"
    NGINX_USER="www-data"
fi

# 检查nginx配置中的用户
CONFIG_USER=$(grep "^user " /etc/nginx/nginx.conf | awk '{print $2}' | sed 's/;//')
if [ -n "$CONFIG_USER" ]; then
    echo "Nginx配置文件用户: $CONFIG_USER"
    NGINX_USER="$CONFIG_USER"
fi

echo -e "${GREEN}✅ Nginx用户: $NGINX_USER${NC}"
echo ""

# 步骤2：检查目录权限
echo -e "${BLUE}[2/6] 检查目录权限...${NC}"

echo "当前权限状态："
ls -ld /root
ls -ld /root/crm
ls -ld /root/crm/static
ls -ld /root/crm/static/images
echo ""

# 检查nginx用户是否能访问/root目录
echo "测试nginx用户访问权限..."
if sudo -u "$NGINX_USER" test -r /root/crm/static/images/custom-logo.png 2>/dev/null; then
    echo -e "${GREEN}✅ Nginx用户可以访问文件${NC}"
else
    echo -e "${RED}❌ Nginx用户无法访问文件${NC}"
    echo "原因：/root目录默认权限是700，nginx用户无法访问"
fi
echo ""

# 步骤3：修复权限（方案1：修改目录权限）
echo -e "${BLUE}[3/6] 修复目录权限...${NC}"

echo "修改目录权限以允许nginx访问..."

# 给/root目录添加执行权限（允许其他用户进入）
chmod 755 /root
echo "✅ /root: 755"

# 修改项目目录权限
chmod 755 /root/crm
echo "✅ /root/crm: 755"

chmod 755 /root/crm/static
echo "✅ /root/crm/static: 755"

chmod 755 /root/crm/static/images
echo "✅ /root/crm/static/images: 755"

# 修改所有静态文件权限
find /root/crm/static -type f -exec chmod 644 {} \;
echo "✅ 所有静态文件: 644"

echo ""

# 步骤4：验证权限修复
echo -e "${BLUE}[4/6] 验证权限修复...${NC}"

echo "测试nginx用户访问..."
if sudo -u "$NGINX_USER" test -r /root/crm/static/images/custom-logo.png 2>/dev/null; then
    echo -e "${GREEN}✅ Nginx用户现在可以访问文件了！${NC}"
else
    echo -e "${RED}❌ Nginx用户仍然无法访问文件${NC}"
    echo ""
    echo "可能需要使用方案2：移动静态文件到/var/www/"
    echo "是否继续？(y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "执行方案2..."
        
        # 创建新的静态文件目录
        mkdir -p /var/www/crm/static
        
        # 复制静态文件
        cp -r /root/crm/static/* /var/www/crm/static/
        
        # 修改权限
        chown -R "$NGINX_USER:$NGINX_USER" /var/www/crm
        chmod -R 755 /var/www/crm
        
        echo ""
        echo -e "${YELLOW}⚠️  需要修改nginx配置：${NC}"
        echo "将 alias /root/crm/static/; 改为 alias /var/www/crm/static/;"
        echo ""
    fi
fi
echo ""

# 步骤5：测试访问
echo -e "${BLUE}[5/6] 测试静态文件访问...${NC}"

# 重新加载nginx
systemctl reload nginx
echo "✅ Nginx已重新加载"
echo ""

# 测试访问
echo "测试HTTPS访问..."
sleep 2

HTTPS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://sxylab.com/static/images/custom-logo.png" 2>/dev/null || echo "000")
echo "HTTPS访问: https://sxylab.com/static/images/custom-logo.png"

if [ "$HTTPS_CODE" = "200" ]; then
    echo -e "${GREEN}✅ HTTPS访问成功 (HTTP $HTTPS_CODE)${NC}"
elif [ "$HTTPS_CODE" = "403" ]; then
    echo -e "${RED}❌ 仍然是403错误${NC}"
    echo ""
    echo "查看nginx错误日志："
    tail -10 /var/log/nginx/sxylab_error.log
else
    echo -e "${YELLOW}⚠️  HTTP状态码: $HTTPS_CODE${NC}"
fi
echo ""

# 步骤6：显示最终权限状态
echo -e "${BLUE}[6/6] 最终权限状态...${NC}"

echo "目录权限："
ls -ld /root | awk '{print "/root: " $1 " " $3 ":" $4}'
ls -ld /root/crm | awk '{print "/root/crm: " $1 " " $3 ":" $4}'
ls -ld /root/crm/static | awk '{print "/root/crm/static: " $1 " " $3 ":" $4}'
ls -ld /root/crm/static/images | awk '{print "/root/crm/static/images: " $1 " " $3 ":" $4}'
echo ""

echo "Logo文件权限："
ls -l /root/crm/static/images/custom-logo.png | awk '{print $1 " " $3 ":" $4 " " $9}'
echo ""

# 诊断结果
echo -e "${BLUE}=========================================="
echo "诊断结果"
echo "==========================================${NC}"
echo ""

if [ "$HTTPS_CODE" = "200" ]; then
    echo -e "${GREEN}✅ 问题已解决！${NC}"
    echo ""
    echo "Logo现在可以正常访问了："
    echo "  https://sxylab.com/static/images/custom-logo.png"
    echo ""
    echo "如果浏览器仍然看不到，请清除缓存："
    echo "  1. Ctrl+Shift+Delete (Chrome)"
    echo "  2. 选择'缓存的图片和文件'"
    echo "  3. 清除数据"
    echo "  4. 强制刷新 (Ctrl+F5)"
    echo ""
else
    echo -e "${RED}❌ 问题未完全解决${NC}"
    echo ""
    echo "当前状态："
    echo "  HTTP状态码: $HTTPS_CODE"
    echo ""
    echo "可能的原因："
    echo "  1. SELinux阻止访问"
    echo "  2. AppArmor限制"
    echo "  3. 需要移动静态文件到/var/www/"
    echo ""
    echo "建议操作："
    echo ""
    echo "1. 检查SELinux状态："
    echo "   getenforce"
    echo ""
    echo "2. 如果是Enforcing，临时禁用测试："
    echo "   setenforce 0"
    echo ""
    echo "3. 查看详细错误日志："
    echo "   tail -50 /var/log/nginx/sxylab_error.log"
    echo ""
    echo "4. 或者移动静态文件到/var/www/："
    echo "   mkdir -p /var/www/crm/static"
    echo "   cp -r /root/crm/static/* /var/www/crm/static/"
    echo "   chown -R $NGINX_USER:$NGINX_USER /var/www/crm"
    echo "   然后修改nginx配置中的alias路径"
    echo ""
fi

echo -e "${GREEN}🎉 脚本执行完成！${NC}"
echo ""

