#!/bin/bash

# ========================================
# 安装数据库备份定时任务脚本
# ========================================
# 功能：在 Ubuntu 服务器上安装 crontab 定时任务
# 执行时间：每天凌晨 3:00
# ========================================

echo "=========================================="
echo "安装 CRM 数据库自动备份定时任务"
echo "=========================================="
echo ""

# 检查是否以 root 或 sudo 权限运行
if [ "$EUID" -ne 0 ]; then 
    echo "警告：建议使用 sudo 运行此脚本以确保权限正确"
    echo "继续安装将使用当前用户的 crontab..."
    echo ""
fi

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="${SCRIPT_DIR}/backup-db.sh"

# 检查备份脚本是否存在
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo "错误：找不到备份脚本: $BACKUP_SCRIPT"
    echo "请确保 backup-db.sh 与本脚本在同一目录"
    exit 1
fi

# 给备份脚本添加执行权限
echo "1. 设置备份脚本执行权限..."
chmod +x "$BACKUP_SCRIPT"
if [ $? -eq 0 ]; then
    echo "   ✓ 权限设置成功"
else
    echo "   ✗ 权限设置失败"
    exit 1
fi

# 创建备份目录
echo ""
echo "2. 创建备份目录 /bak ..."
sudo mkdir -p /bak
if [ $? -eq 0 ]; then
    echo "   ✓ 备份目录已创建"
    # 设置目录权限（允许当前用户写入）
    sudo chown -R $USER:$USER /bak
    sudo chmod 755 /bak
else
    echo "   ✗ 创建备份目录失败"
    exit 1
fi

# 检查 crontab 是否已存在相同任务
echo ""
echo "3. 检查现有定时任务..."
CRON_ENTRY="0 3 * * * $BACKUP_SCRIPT >> /bak/backup.log 2>&1"

# 检查是否已存在
crontab -l 2>/dev/null | grep -F "$BACKUP_SCRIPT" > /dev/null
if [ $? -eq 0 ]; then
    echo "   ! 检测到已存在的备份任务"
    echo ""
    echo "当前相关的 crontab 任务："
    crontab -l 2>/dev/null | grep -F "$BACKUP_SCRIPT"
    echo ""
    read -p "是否要删除旧任务并重新安装？(y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 删除旧任务
        crontab -l 2>/dev/null | grep -v -F "$BACKUP_SCRIPT" | crontab -
        echo "   ✓ 已删除旧任务"
    else
        echo "   取消安装"
        exit 0
    fi
fi

# 添加新的 crontab 任务
echo ""
echo "4. 添加定时任务到 crontab..."
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

if [ $? -eq 0 ]; then
    echo "   ✓ 定时任务添加成功"
else
    echo "   ✗ 定时任务添加失败"
    exit 1
fi

# 验证安装
echo ""
echo "5. 验证安装结果..."
crontab -l | grep -F "$BACKUP_SCRIPT" > /dev/null
if [ $? -eq 0 ]; then
    echo "   ✓ 定时任务已成功安装"
else
    echo "   ✗ 验证失败"
    exit 1
fi

# 测试备份脚本
echo ""
read -p "是否要立即测试备份脚本？(y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "=========================================="
    echo "执行测试备份..."
    echo "=========================================="
    "$BACKUP_SCRIPT"
    echo ""
    echo "测试完成！请检查 /bak 目录和 /bak/backup.log 日志文件"
fi

# 显示安装摘要
echo ""
echo "=========================================="
echo "安装完成！"
echo "=========================================="
echo ""
echo "配置摘要："
echo "  • 备份脚本路径: $BACKUP_SCRIPT"
echo "  • 备份目录: /bak"
echo "  • 执行时间: 每天凌晨 3:00"
echo "  • 保留天数: 3 天"
echo "  • 日志文件: /bak/backup.log"
echo ""
echo "当前 crontab 任务："
crontab -l | grep -F "$BACKUP_SCRIPT"
echo ""
echo "管理命令："
echo "  • 查看所有定时任务: crontab -l"
echo "  • 编辑定时任务: crontab -e"
echo "  • 删除此任务: crontab -l | grep -v '$BACKUP_SCRIPT' | crontab -"
echo "  • 手动执行备份: $BACKUP_SCRIPT"
echo "  • 查看备份日志: tail -f /bak/backup.log"
echo "  • 查看备份文件: ls -lh /bak/edu_crm_*.db"
echo ""
echo "注意事项："
echo "  1. 确保 /crm/instance/edu_crm.db 路径正确"
echo "  2. 确保有足够的磁盘空间存储备份"
echo "  3. 定期检查 /bak/backup.log 确认备份正常"
echo "  4. 如需修改备份时间，请编辑 crontab: crontab -e"
echo ""

exit 0

