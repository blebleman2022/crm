#!/bin/bash

# Logo显示问题一键修复脚本
# 修复页面logo和标签栏favicon无法显示的问题

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "${BLUE}=========================================="
echo "Logo显示问题一键修复"
echo "==========================================${NC}"
echo ""

# 检查root权限
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ 请使用root权限运行${NC}"
    exit 1
fi

# 项目路径
PROJECT_DIR="/root/crm"
STATIC_DIR="$PROJECT_DIR/static"
IMAGES_DIR="$STATIC_DIR/images"

echo -e "${GREEN}✅ 权限检查通过${NC}"
echo ""

# 步骤1：检查项目目录
echo -e "${BLUE}[1/7] 检查项目目录...${NC}"
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ 项目目录不存在: $PROJECT_DIR${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 项目目录存在${NC}"
echo ""

# 步骤2：检查静态文件目录
echo -e "${BLUE}[2/7] 检查静态文件目录...${NC}"
if [ ! -d "$IMAGES_DIR" ]; then
    echo -e "${YELLOW}⚠️  images目录不存在，正在创建...${NC}"
    mkdir -p "$IMAGES_DIR"
    chmod 755 "$IMAGES_DIR"
fi
echo -e "${GREEN}✅ 静态文件目录存在${NC}"
echo ""

# 步骤3：检查logo文件
echo -e "${BLUE}[3/7] 检查logo文件...${NC}"
LOGO_FOUND=false
LOGO_FILE=""

for ext in png jpg jpeg gif; do
    if [ -f "$IMAGES_DIR/custom-logo.$ext" ]; then
        LOGO_FOUND=true
        LOGO_FILE="custom-logo.$ext"
        echo -e "${GREEN}✅ 找到logo文件: $LOGO_FILE${NC}"
        break
    fi
done

if [ "$LOGO_FOUND" = false ]; then
    echo -e "${YELLOW}⚠️  未找到custom-logo文件${NC}"
    echo "当前images目录内容："
    ls -lh "$IMAGES_DIR/" 2>/dev/null || echo "目录为空"
    echo ""
    
    # 检查是否有其他logo文件
    if [ -f "$IMAGES_DIR/logo1.png" ]; then
        echo -e "${YELLOW}发现logo1.png，复制为custom-logo.png...${NC}"
        cp "$IMAGES_DIR/logo1.png" "$IMAGES_DIR/custom-logo.png"
        LOGO_FILE="custom-logo.png"
        LOGO_FOUND=true
        echo -e "${GREEN}✅ 已创建custom-logo.png${NC}"
    elif [ -f "$IMAGES_DIR/logo.jpg" ]; then
        echo -e "${YELLOW}发现logo.jpg，复制为custom-logo.jpg...${NC}"
        cp "$IMAGES_DIR/logo.jpg" "$IMAGES_DIR/custom-logo.jpg"
        LOGO_FILE="custom-logo.jpg"
        LOGO_FOUND=true
        echo -e "${GREEN}✅ 已创建custom-logo.jpg${NC}"
    else
        echo -e "${RED}❌ 未找到任何logo文件${NC}"
        echo "请手动上传logo文件到: $IMAGES_DIR/custom-logo.png"
        echo "或者通过系统管理 -> Logo管理上传"
    fi
fi
echo ""

# 步骤4：检查favicon文件
echo -e "${BLUE}[4/7] 检查favicon文件...${NC}"
FAVICON_FILE="$IMAGES_DIR/logo1.png"

if [ -f "$FAVICON_FILE" ]; then
    echo -e "${GREEN}✅ favicon文件存在: logo1.png${NC}"
else
    echo -e "${YELLOW}⚠️  favicon文件不存在${NC}"
    
    # 尝试从custom-logo创建favicon
    if [ "$LOGO_FOUND" = true ]; then
        echo -e "${YELLOW}从custom-logo创建favicon...${NC}"
        cp "$IMAGES_DIR/$LOGO_FILE" "$FAVICON_FILE"
        echo -e "${GREEN}✅ 已创建favicon: logo1.png${NC}"
    else
        echo -e "${RED}❌ 无法创建favicon${NC}"
    fi
fi
echo ""

# 步骤5：修复文件权限
echo -e "${BLUE}[5/7] 修复文件权限...${NC}"

# 修复目录权限
chmod 755 "$STATIC_DIR"
chmod 755 "$IMAGES_DIR"

# 修复文件权限
if [ -f "$IMAGES_DIR/custom-logo.png" ]; then
    chmod 644 "$IMAGES_DIR/custom-logo.png"
    echo -e "${GREEN}✅ custom-logo.png 权限已修复${NC}"
fi

if [ -f "$IMAGES_DIR/custom-logo.jpg" ]; then
    chmod 644 "$IMAGES_DIR/custom-logo.jpg"
    echo -e "${GREEN}✅ custom-logo.jpg 权限已修复${NC}"
fi

if [ -f "$IMAGES_DIR/logo1.png" ]; then
    chmod 644 "$IMAGES_DIR/logo1.png"
    echo -e "${GREEN}✅ logo1.png 权限已修复${NC}"
fi

echo ""

# 步骤6：测试静态文件访问
echo -e "${BLUE}[6/7] 测试静态文件访问...${NC}"

# 测试logo访问
if [ "$LOGO_FOUND" = true ]; then
    echo "测试logo访问: http://localhost/static/images/$LOGO_FILE"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost/static/images/$LOGO_FILE" 2>/dev/null || echo "000")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✅ Logo可以访问 (HTTP $HTTP_CODE)${NC}"
    else
        echo -e "${RED}❌ Logo无法访问 (HTTP $HTTP_CODE)${NC}"
        echo "可能的原因："
        echo "1. Nginx配置错误"
        echo "2. Nginx未运行"
        echo "3. 文件路径不正确"
    fi
fi

# 测试favicon访问
if [ -f "$FAVICON_FILE" ]; then
    echo "测试favicon访问: http://localhost/static/images/logo1.png"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost/static/images/logo1.png" 2>/dev/null || echo "000")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✅ Favicon可以访问 (HTTP $HTTP_CODE)${NC}"
    else
        echo -e "${RED}❌ Favicon无法访问 (HTTP $HTTP_CODE)${NC}"
    fi
fi

echo ""

# 步骤7：检查Nginx配置
echo -e "${BLUE}[7/7] 检查Nginx配置...${NC}"

# 检查静态文件配置
if grep -q "location /static/" /etc/nginx/nginx.conf 2>/dev/null; then
    echo -e "${GREEN}✅ Nginx静态文件配置存在${NC}"
    
    # 显示配置
    echo "当前配置："
    grep -A 3 "location /static/" /etc/nginx/nginx.conf | head -5
    
    # 检查alias路径
    if grep "location /static/" /etc/nginx/nginx.conf | grep -q "alias /root/crm/static/"; then
        echo -e "${GREEN}✅ alias路径正确${NC}"
    else
        echo -e "${YELLOW}⚠️  alias路径可能不正确${NC}"
        echo "应该是: alias /root/crm/static/;"
    fi
else
    echo -e "${RED}❌ Nginx静态文件配置不存在${NC}"
    echo "请在nginx.conf中添加："
    echo ""
    echo "location /static/ {"
    echo "    alias /root/crm/static/;"
    echo "    expires 7d;"
    echo "    add_header Cache-Control \"public\";"
    echo "}"
fi

echo ""

# 显示诊断结果
echo -e "${BLUE}=========================================="
echo "诊断结果"
echo "==========================================${NC}"
echo ""

echo -e "${YELLOW}文件状态：${NC}"
ls -lh "$IMAGES_DIR/" | grep -E "custom-logo|logo1" || echo "未找到logo文件"
echo ""

echo -e "${YELLOW}文件权限：${NC}"
echo "static目录: $(stat -c '%a' $STATIC_DIR 2>/dev/null || echo '未知')"
echo "images目录: $(stat -c '%a' $IMAGES_DIR 2>/dev/null || echo '未知')"
if [ -f "$IMAGES_DIR/custom-logo.png" ]; then
    echo "custom-logo.png: $(stat -c '%a' $IMAGES_DIR/custom-logo.png)"
fi
if [ -f "$IMAGES_DIR/logo1.png" ]; then
    echo "logo1.png: $(stat -c '%a' $IMAGES_DIR/logo1.png)"
fi
echo ""

# 提供解决方案
echo -e "${BLUE}=========================================="
echo "解决方案"
echo "==========================================${NC}"
echo ""

if [ "$LOGO_FOUND" = false ]; then
    echo -e "${RED}❌ Logo文件缺失${NC}"
    echo ""
    echo "解决方法1：从本地上传"
    echo "  scp static/images/custom-logo.png root@47.100.238.50:/root/crm/static/images/"
    echo ""
    echo "解决方法2：通过系统管理界面上传"
    echo "  1. 登录系统"
    echo "  2. 进入 系统管理 -> Logo管理"
    echo "  3. 上传logo文件"
    echo ""
else
    echo -e "${GREEN}✅ Logo文件存在${NC}"
    echo ""
    echo "如果浏览器仍然看不到logo，请尝试："
    echo "1. 清除浏览器缓存（Ctrl+Shift+Delete）"
    echo "2. 强制刷新页面（Ctrl+F5 或 Cmd+Shift+R）"
    echo "3. 检查浏览器控制台是否有错误"
    echo ""
fi

echo -e "${YELLOW}测试URL：${NC}"
echo "Logo: https://sxylab.com/static/images/$LOGO_FILE"
echo "Favicon: https://sxylab.com/static/images/logo1.png"
echo ""

echo -e "${YELLOW}常用命令：${NC}"
echo "查看logo文件:     ls -lh /root/crm/static/images/"
echo "测试logo访问:     curl -I https://sxylab.com/static/images/custom-logo.png"
echo "重新加载nginx:    systemctl reload nginx"
echo "查看nginx日志:    tail -f /var/log/nginx/sxylab_error.log"
echo ""

echo -e "${GREEN}🎉 诊断完成！${NC}"
echo ""

