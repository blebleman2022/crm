#!/bin/bash

# 数据库迁移部署脚本
# 用途：在服务器上添加 communication_records.user_id 字段

set -e  # 遇到错误立即退出

echo "=========================================="
echo "  CRM 数据库迁移脚本"
echo "  添加 communication_records.user_id 字段"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否在项目目录
if [ ! -f "run.py" ]; then
    echo -e "${RED}❌ 错误：请在项目根目录下运行此脚本${NC}"
    exit 1
fi

# 查找并激活虚拟环境
VENV_ACTIVATED=0

if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  虚拟环境未激活，正在查找虚拟环境...${NC}"

    # 尝试常见的虚拟环境目录名
    for venv_dir in venv env .venv virtualenv; do
        if [ -d "$venv_dir" ] && [ -f "$venv_dir/bin/activate" ]; then
            echo "找到虚拟环境：$venv_dir"
            source "$venv_dir/bin/activate"
            VENV_ACTIVATED=1
            echo -e "${GREEN}✅ 虚拟环境已激活${NC}"
            break
        fi
    done

    if [ $VENV_ACTIVATED -eq 0 ]; then
        echo -e "${RED}❌ 错误：找不到虚拟环境${NC}"
        echo "请手动激活虚拟环境后再运行此脚本："
        echo "  source venv/bin/activate"
        echo "  bash deploy_migration.sh"
        exit 1
    fi
else
    echo -e "${GREEN}✅ 虚拟环境已激活：$VIRTUAL_ENV${NC}"
fi

# 检查数据库文件
if [ ! -f "instance/crm.db" ]; then
    echo -e "${RED}❌ 错误：找不到数据库文件 instance/crm.db${NC}"
    exit 1
fi

# 备份数据库
BACKUP_FILE="instance/crm.db.backup.$(date +%Y%m%d_%H%M%S)"
echo "正在备份数据库..."
cp instance/crm.db "$BACKUP_FILE"
echo -e "${GREEN}✅ 数据库已备份到：$BACKUP_FILE${NC}"
echo ""

# 运行迁移脚本
echo "正在运行数据库迁移..."
python add_user_id_to_communications.py

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ 数据库迁移成功！${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}❌ 数据库迁移失败！${NC}"
    echo "正在恢复备份..."
    cp "$BACKUP_FILE" instance/crm.db
    echo -e "${YELLOW}⚠️  数据库已恢复到迁移前状态${NC}"
    exit 1
fi

# 询问是否重启服务
echo "=========================================="
echo "  迁移完成，需要重启服务"
echo "=========================================="
echo ""
echo "请选择重启方式："
echo "  1) systemd (sudo systemctl restart crm)"
echo "  2) supervisor (sudo supervisorctl restart crm)"
echo "  3) 手动重启（稍后自行重启）"
echo "  4) 跳过重启"
echo ""
read -p "请输入选项 [1-4]: " restart_option

case $restart_option in
    1)
        echo "正在使用 systemd 重启服务..."
        sudo systemctl restart crm
        echo -e "${GREEN}✅ 服务已重启${NC}"
        ;;
    2)
        echo "正在使用 supervisor 重启服务..."
        sudo supervisorctl restart crm
        echo -e "${GREEN}✅ 服务已重启${NC}"
        ;;
    3)
        echo -e "${YELLOW}⚠️  请手动重启服务${NC}"
        echo "提示：可以使用以下命令："
        echo "  pkill -f 'python run.py'"
        echo "  nohup python run.py > logs/app.log 2>&1 &"
        ;;
    4)
        echo -e "${YELLOW}⚠️  已跳过重启，请记得稍后重启服务${NC}"
        ;;
    *)
        echo -e "${YELLOW}⚠️  无效选项，已跳过重启${NC}"
        ;;
esac

echo ""
echo "=========================================="
echo "  部署完成"
echo "=========================================="
echo ""
echo "下一步："
echo "  1. 访问系统：http://47.100.238.50"
echo "  2. 登录账号：13900139001"
echo "  3. 测试学员详情页是否正常"
echo "  4. 测试新增沟通记录功能"
echo ""
echo "备份文件位置：$BACKUP_FILE"
echo ""

