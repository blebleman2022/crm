#!/bin/bash

# 修复域名访问时logo无法显示的问题
# IP访问正常，域名访问不正常 -> 通常是缓存或HTTPS问题

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "${BLUE}=========================================="
echo "修复域名访问Logo显示问题"
echo "==========================================${NC}"
echo ""

# 检查root权限
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ 请使用root权限运行${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 权限检查通过${NC}"
echo ""

# 步骤1：确认logo文件存在
echo -e "${BLUE}[1/5] 确认logo文件存在...${NC}"

LOGO_FOUND=false
LOGO_FILE=""

for ext in png jpg jpeg gif; do
    if [ -f "/root/crm/static/images/custom-logo.$ext" ]; then
        LOGO_FOUND=true
        LOGO_FILE="custom-logo.$ext"
        echo -e "${GREEN}✅ Logo文件存在: $LOGO_FILE${NC}"
        ls -lh "/root/crm/static/images/$LOGO_FILE"
        break
    fi
done

if [ "$LOGO_FOUND" = false ]; then
    echo -e "${RED}❌ Logo文件不存在${NC}"
    exit 1
fi
echo ""

# 步骤2：测试IP访问
echo -e "${BLUE}[2/5] 测试IP访问...${NC}"

IP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1/static/images/$LOGO_FILE" 2>/dev/null || echo "000")
echo "IP访问测试: http://127.0.0.1/static/images/$LOGO_FILE"
if [ "$IP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ IP访问正常 (HTTP $IP_CODE)${NC}"
else
    echo -e "${RED}❌ IP访问失败 (HTTP $IP_CODE)${NC}"
fi
echo ""

# 步骤3：测试域名HTTP访问
echo -e "${BLUE}[3/5] 测试域名HTTP访问...${NC}"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://sxylab.com/static/images/$LOGO_FILE" 2>/dev/null || echo "000")
echo "HTTP访问测试: http://sxylab.com/static/images/$LOGO_FILE"
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ HTTP访问正常 (HTTP $HTTP_CODE)${NC}"
elif [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
    echo -e "${YELLOW}⚠️  HTTP被重定向到HTTPS (HTTP $HTTP_CODE)${NC}"
    echo "这是正常的，继续检查HTTPS..."
else
    echo -e "${RED}❌ HTTP访问失败 (HTTP $HTTP_CODE)${NC}"
fi
echo ""

# 步骤4：测试域名HTTPS访问
echo -e "${BLUE}[4/5] 测试域名HTTPS访问...${NC}"

HTTPS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://sxylab.com/static/images/$LOGO_FILE" 2>/dev/null || echo "000")
echo "HTTPS访问测试: https://sxylab.com/static/images/$LOGO_FILE"
if [ "$HTTPS_CODE" = "200" ]; then
    echo -e "${GREEN}✅ HTTPS访问正常 (HTTP $HTTPS_CODE)${NC}"
else
    echo -e "${RED}❌ HTTPS访问失败 (HTTP $HTTPS_CODE)${NC}"
fi
echo ""

# 步骤5：清除Nginx缓存并优化配置
echo -e "${BLUE}[5/5] 优化Nginx配置...${NC}"

# 备份nginx配置
BACKUP_FILE="/etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)"
cp /etc/nginx/nginx.conf "$BACKUP_FILE"
echo -e "${GREEN}✅ 已备份nginx配置到: $BACKUP_FILE${NC}"
echo ""

# 检查并优化静态文件配置
echo "检查Nginx静态文件配置..."

if grep -q "location /static/" /etc/nginx/nginx.conf; then
    echo -e "${GREEN}✅ 静态文件配置存在${NC}"
    
    # 显示当前配置
    echo ""
    echo "当前配置："
    grep -A 5 "location /static/" /etc/nginx/nginx.conf | head -7
    echo ""
    
    # 检查是否有缓存配置导致问题
    if grep "location /static/" /etc/nginx/nginx.conf | grep -q "immutable"; then
        echo -e "${YELLOW}⚠️  发现immutable缓存配置，可能导致浏览器不更新${NC}"
        echo "建议修改为: add_header Cache-Control \"public\";"
    fi
else
    echo -e "${RED}❌ 静态文件配置不存在${NC}"
fi
echo ""

# 重新加载nginx
echo "重新加载Nginx..."
if nginx -t 2>&1 | grep -q "successful"; then
    systemctl reload nginx
    echo -e "${GREEN}✅ Nginx已重新加载${NC}"
else
    echo -e "${RED}❌ Nginx配置测试失败${NC}"
    nginx -t
fi
echo ""

# 诊断结果
echo -e "${BLUE}=========================================="
echo "诊断结果"
echo "==========================================${NC}"
echo ""

echo -e "${YELLOW}测试结果汇总：${NC}"
echo "IP访问 (127.0.0.1):     HTTP $IP_CODE"
echo "域名HTTP访问:           HTTP $HTTP_CODE"
echo "域名HTTPS访问:          HTTP $HTTPS_CODE"
echo ""

# 判断问题原因
if [ "$IP_CODE" = "200" ] && [ "$HTTPS_CODE" = "200" ]; then
    echo -e "${GREEN}✅ 服务器端配置正常！${NC}"
    echo ""
    echo -e "${YELLOW}问题原因：浏览器缓存${NC}"
    echo ""
    echo "解决方案："
    echo "1. 清除浏览器缓存"
    echo "   Chrome: Ctrl+Shift+Delete (Windows) 或 Cmd+Shift+Delete (Mac)"
    echo "   选择 '图片和文件' 并清除"
    echo ""
    echo "2. 强制刷新页面"
    echo "   Ctrl+F5 (Windows) 或 Cmd+Shift+R (Mac)"
    echo ""
    echo "3. 使用无痕模式测试"
    echo "   Ctrl+Shift+N (Chrome) 或 Ctrl+Shift+P (Firefox)"
    echo ""
    echo "4. 如果仍然不显示，检查浏览器控制台错误"
    echo "   按F12打开开发者工具 -> Console标签"
    echo ""
    
elif [ "$IP_CODE" = "200" ] && [ "$HTTPS_CODE" != "200" ]; then
    echo -e "${RED}❌ HTTPS访问有问题${NC}"
    echo ""
    echo "可能的原因："
    echo "1. SSL证书配置问题"
    echo "2. HTTPS server块中缺少静态文件配置"
    echo "3. 防火墙阻止443端口"
    echo ""
    echo "解决方案："
    echo "检查nginx.conf中HTTPS server块是否包含："
    echo ""
    echo "server {"
    echo "    listen 443 ssl http2;"
    echo "    server_name sxylab.com www.sxylab.com;"
    echo ""
    echo "    location /static/ {"
    echo "        alias /root/crm/static/;"
    echo "        expires 7d;"
    echo "        add_header Cache-Control \"public\";"
    echo "    }"
    echo "    ..."
    echo "}"
    echo ""
    
else
    echo -e "${RED}❌ 服务器配置有问题${NC}"
    echo ""
    echo "请检查："
    echo "1. Nginx是否正在运行: systemctl status nginx"
    echo "2. 静态文件路径是否正确"
    echo "3. 文件权限是否正确"
    echo ""
fi

# 提供快速测试命令
echo -e "${BLUE}=========================================="
echo "快速测试命令"
echo "==========================================${NC}"
echo ""

echo "在浏览器中直接访问logo："
echo "  https://sxylab.com/static/images/$LOGO_FILE"
echo ""

echo "查看Nginx错误日志："
echo "  tail -50 /var/log/nginx/sxylab_error.log"
echo ""

echo "查看Nginx访问日志："
echo "  tail -50 /var/log/nginx/sxylab_access.log | grep '$LOGO_FILE'"
echo ""

echo "测试favicon："
echo "  curl -I https://sxylab.com/static/images/logo1.png"
echo ""

# 创建浏览器缓存清除说明
cat > /root/清除浏览器缓存说明.txt << 'EOF'
========================================
清除浏览器缓存 - 详细步骤
========================================

Chrome浏览器：
1. 按 Ctrl+Shift+Delete (Windows) 或 Cmd+Shift+Delete (Mac)
2. 选择时间范围：全部时间
3. 勾选：缓存的图片和文件
4. 点击"清除数据"
5. 刷新页面 (F5)

Firefox浏览器：
1. 按 Ctrl+Shift+Delete (Windows) 或 Cmd+Shift+Delete (Mac)
2. 选择时间范围：全部
3. 勾选：缓存
4. 点击"立即清除"
5. 刷新页面 (F5)

Safari浏览器：
1. 按 Cmd+Option+E (清除缓存)
2. 或者：Safari菜单 -> 清除历史记录
3. 选择：所有历史记录
4. 点击"清除历史记录"
5. 刷新页面 (Cmd+R)

Edge浏览器：
1. 按 Ctrl+Shift+Delete
2. 选择时间范围：所有时间
3. 勾选：缓存的图像和文件
4. 点击"立即清除"
5. 刷新页面 (F5)

========================================
强制刷新（绕过缓存）
========================================

Windows:
  Ctrl+F5 或 Ctrl+Shift+R

Mac:
  Cmd+Shift+R

========================================
使用无痕模式测试
========================================

Chrome: Ctrl+Shift+N (Windows) 或 Cmd+Shift+N (Mac)
Firefox: Ctrl+Shift+P (Windows) 或 Cmd+Shift+P (Mac)
Safari: Cmd+Shift+N
Edge: Ctrl+Shift+N

无痕模式不使用缓存，可以验证是否是缓存问题。

========================================
检查浏览器控制台错误
========================================

1. 按 F12 打开开发者工具
2. 切换到 Console (控制台) 标签
3. 刷新页面
4. 查看是否有红色错误信息
5. 切换到 Network (网络) 标签
6. 刷新页面
7. 搜索 "custom-logo" 或 "logo1"
8. 查看HTTP状态码（应该是200）

常见错误：
- 404 Not Found: 文件不存在
- 403 Forbidden: 权限问题
- Mixed Content: HTTPS页面加载HTTP资源
- ERR_CERT_*: SSL证书问题

EOF

echo -e "${GREEN}✅ 已创建浏览器缓存清除说明: /root/清除浏览器缓存说明.txt${NC}"
echo ""

echo -e "${GREEN}🎉 诊断完成！${NC}"
echo ""

if [ "$IP_CODE" = "200" ] && [ "$HTTPS_CODE" = "200" ]; then
    echo -e "${BLUE}=========================================="
    echo "结论：服务器配置正常"
    echo "==========================================${NC}"
    echo ""
    echo "Logo文件可以正常访问，问题出在浏览器缓存。"
    echo ""
    echo "请按照以下步骤操作："
    echo "1. 清除浏览器缓存（参考 /root/清除浏览器缓存说明.txt）"
    echo "2. 强制刷新页面（Ctrl+F5 或 Cmd+Shift+R）"
    echo "3. 或使用无痕模式访问 https://sxylab.com"
    echo ""
    echo "如果清除缓存后仍然不显示，请检查浏览器控制台错误。"
    echo ""
fi

