#!/bin/bash

# 设置数据库自动备份定时任务
# 用途：配置 crontab，每天凌晨3点自动备份数据库
# 作者：CRM Team
# 最后更新：2025-10-04

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  CRM 数据库自动备份配置工具"
echo "=========================================="
echo ""

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="$SCRIPT_DIR/backup_database.sh"

# 检查备份脚本是否存在
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo -e "${RED}❌ 错误：找不到备份脚本 $BACKUP_SCRIPT${NC}"
    exit 1
fi

# 确保备份脚本有执行权限
chmod +x "$BACKUP_SCRIPT"
echo -e "${GREEN}✅ 备份脚本已设置执行权限${NC}"

# 定义 cron 任务
CRON_TIME="0 3 * * *"  # 每天凌晨3点
CRON_JOB="$CRON_TIME $BACKUP_SCRIPT >> $SCRIPT_DIR/bak/backup.log 2>&1"

# 检查是否已存在相同的 cron 任务
if crontab -l 2>/dev/null | grep -F "$BACKUP_SCRIPT" > /dev/null; then
    echo -e "${YELLOW}⚠️  检测到已存在的备份任务${NC}"
    echo ""
    echo "当前的备份任务："
    crontab -l | grep -F "$BACKUP_SCRIPT"
    echo ""
    read -p "是否要替换现有任务？[y/N] " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}⚠️  已取消配置${NC}"
        exit 0
    fi
    
    # 删除旧任务
    crontab -l 2>/dev/null | grep -v -F "$BACKUP_SCRIPT" | crontab -
    echo -e "${GREEN}✅ 已删除旧任务${NC}"
fi

# 添加新的 cron 任务
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 定时任务配置成功！${NC}"
    echo ""
    echo "=========================================="
    echo "  配置详情"
    echo "=========================================="
    echo ""
    echo "执行时间：每天凌晨 3:00"
    echo "备份脚本：$BACKUP_SCRIPT"
    echo "日志文件：$SCRIPT_DIR/bak/backup.log"
    echo "备份目录：$SCRIPT_DIR/bak/"
    echo ""
    echo "当前所有 cron 任务："
    echo "----------------------------------------"
    crontab -l
    echo "----------------------------------------"
    echo ""
else
    echo -e "${RED}❌ 定时任务配置失败${NC}"
    exit 1
fi

# 询问是否立即测试备份
echo ""
read -p "是否立即运行一次备份测试？[Y/n] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    echo ""
    echo "正在运行备份测试..."
    echo "=========================================="
    bash "$BACKUP_SCRIPT"
    echo ""
    echo -e "${GREEN}✅ 备份测试完成${NC}"
    echo ""
    echo "请检查备份目录：$SCRIPT_DIR/bak/"
    ls -lh "$SCRIPT_DIR/bak/" | grep "edu_crm_"
fi

echo ""
echo "=========================================="
echo "  配置完成"
echo "=========================================="
echo ""
echo "下一步："
echo "  1. 备份将在每天凌晨3点自动运行"
echo "  2. 查看备份日志：tail -f $SCRIPT_DIR/bak/backup.log"
echo "  3. 查看备份文件：ls -lh $SCRIPT_DIR/bak/"
echo "  4. 手动运行备份：bash $BACKUP_SCRIPT"
echo ""
echo "管理 cron 任务："
echo "  - 查看任务：crontab -l"
echo "  - 编辑任务：crontab -e"
echo "  - 删除任务：crontab -r"
echo ""

