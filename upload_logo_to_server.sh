#!/bin/bash

# 从本地上传logo文件到服务器
# 使用方法：bash upload_logo_to_server.sh

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "${BLUE}=========================================="
echo "上传Logo到服务器"
echo "==========================================${NC}"
echo ""

# 服务器配置
SERVER="root@47.100.238.50"
SERVER_PATH="/root/crm/static/images/"
LOCAL_IMAGES_DIR="static/images"

# 步骤1：检查本地logo文件
echo -e "${BLUE}[1/4] 检查本地logo文件...${NC}"

if [ ! -d "$LOCAL_IMAGES_DIR" ]; then
    echo -e "${RED}❌ 本地images目录不存在: $LOCAL_IMAGES_DIR${NC}"
    exit 1
fi

echo "本地images目录内容："
ls -lh "$LOCAL_IMAGES_DIR/" | grep -E "\.png|\.jpg|\.jpeg|\.gif" || echo "未找到图片文件"
echo ""

# 查找logo文件
LOGO_FILES=()

if [ -f "$LOCAL_IMAGES_DIR/custom-logo.png" ]; then
    LOGO_FILES+=("custom-logo.png")
fi

if [ -f "$LOCAL_IMAGES_DIR/custom-logo.jpg" ]; then
    LOGO_FILES+=("custom-logo.jpg")
fi

if [ -f "$LOCAL_IMAGES_DIR/logo1.png" ]; then
    LOGO_FILES+=("logo1.png")
fi

if [ -f "$LOCAL_IMAGES_DIR/logo.jpg" ]; then
    LOGO_FILES+=("logo.jpg")
fi

if [ ${#LOGO_FILES[@]} -eq 0 ]; then
    echo -e "${RED}❌ 未找到logo文件${NC}"
    echo ""
    echo "请确保以下文件之一存在："
    echo "  - static/images/custom-logo.png"
    echo "  - static/images/custom-logo.jpg"
    echo "  - static/images/logo1.png"
    echo "  - static/images/logo.jpg"
    exit 1
fi

echo -e "${GREEN}✅ 找到 ${#LOGO_FILES[@]} 个logo文件${NC}"
for file in "${LOGO_FILES[@]}"; do
    echo "  - $file"
done
echo ""

# 步骤2：选择要上传的文件
echo -e "${BLUE}[2/4] 选择要上传的文件...${NC}"

if [ ${#LOGO_FILES[@]} -eq 1 ]; then
    SELECTED_FILE="${LOGO_FILES[0]}"
    echo -e "${GREEN}自动选择: $SELECTED_FILE${NC}"
else
    echo "请选择要上传的文件："
    for i in "${!LOGO_FILES[@]}"; do
        echo "  $((i+1)). ${LOGO_FILES[$i]}"
    done
    echo ""
    read -p "请输入序号 [1-${#LOGO_FILES[@]}]: " choice
    
    if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le ${#LOGO_FILES[@]} ]; then
        SELECTED_FILE="${LOGO_FILES[$((choice-1))]}"
        echo -e "${GREEN}已选择: $SELECTED_FILE${NC}"
    else
        echo -e "${RED}❌ 无效的选择${NC}"
        exit 1
    fi
fi
echo ""

# 步骤3：上传文件
echo -e "${BLUE}[3/4] 上传文件到服务器...${NC}"

LOCAL_FILE="$LOCAL_IMAGES_DIR/$SELECTED_FILE"
REMOTE_FILE="$SERVER:$SERVER_PATH$SELECTED_FILE"

echo "本地文件: $LOCAL_FILE"
echo "远程路径: $REMOTE_FILE"
echo ""

# 检查SSH连接
echo "测试SSH连接..."
if ssh -o ConnectTimeout=5 "$SERVER" "echo '连接成功'" 2>/dev/null; then
    echo -e "${GREEN}✅ SSH连接正常${NC}"
else
    echo -e "${RED}❌ SSH连接失败${NC}"
    echo "请检查："
    echo "1. 服务器IP是否正确"
    echo "2. SSH密钥是否配置"
    echo "3. 网络连接是否正常"
    exit 1
fi
echo ""

# 上传文件
echo "正在上传..."
if scp "$LOCAL_FILE" "$REMOTE_FILE"; then
    echo -e "${GREEN}✅ 文件上传成功${NC}"
else
    echo -e "${RED}❌ 文件上传失败${NC}"
    exit 1
fi
echo ""

# 如果上传的不是custom-logo，创建副本
if [[ "$SELECTED_FILE" != custom-logo* ]]; then
    echo "创建custom-logo副本..."
    EXT="${SELECTED_FILE##*.}"
    ssh "$SERVER" "cp $SERVER_PATH$SELECTED_FILE ${SERVER_PATH}custom-logo.$EXT"
    echo -e "${GREEN}✅ 已创建 custom-logo.$EXT${NC}"
    echo ""
fi

# 步骤4：修复权限并测试
echo -e "${BLUE}[4/4] 修复权限并测试...${NC}"

echo "修复文件权限..."
ssh "$SERVER" "chmod 755 /root/crm/static/images/ && chmod 644 /root/crm/static/images/*"
echo -e "${GREEN}✅ 权限已修复${NC}"
echo ""

echo "测试文件访问..."
HTTP_CODE=$(ssh "$SERVER" "curl -s -o /dev/null -w '%{http_code}' http://localhost/static/images/$SELECTED_FILE" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ 文件可以访问 (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${YELLOW}⚠️  文件访问测试失败 (HTTP $HTTP_CODE)${NC}"
    echo "可能需要重新加载nginx"
fi
echo ""

# 显示结果
echo -e "${BLUE}=========================================="
echo "上传完成"
echo "==========================================${NC}"
echo ""

echo -e "${GREEN}✅ Logo文件已上传到服务器${NC}"
echo ""

echo -e "${YELLOW}服务器文件列表：${NC}"
ssh "$SERVER" "ls -lh /root/crm/static/images/ | grep -E 'custom-logo|logo1|logo\.'"
echo ""

echo -e "${YELLOW}访问URL：${NC}"
echo "Logo: https://sxylab.com/static/images/$SELECTED_FILE"
if [[ "$SELECTED_FILE" != custom-logo* ]]; then
    EXT="${SELECTED_FILE##*.}"
    echo "Logo: https://sxylab.com/static/images/custom-logo.$EXT"
fi
echo ""

echo -e "${YELLOW}后续步骤：${NC}"
echo "1. 清除浏览器缓存"
echo "2. 访问 https://sxylab.com 查看效果"
echo "3. 如果仍然看不到，运行服务器端修复脚本："
echo "   ssh $SERVER 'bash /root/fix_logo_display.sh'"
echo ""

echo -e "${GREEN}🎉 完成！${NC}"
echo ""

