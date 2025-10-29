#!/bin/bash
# EduConnect CRM 服务器部署更新脚本
# 用途：安全地部署代码更新并迁移数据库
# 使用方法：bash deploy_update.sh

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}EduConnect CRM 服务器部署更新脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 1. 检查当前目录
if [ ! -f "run.py" ]; then
    echo -e "${RED}错误：请在项目根目录下运行此脚本${NC}"
    exit 1
fi

# 2. 备份当前数据库
echo -e "${YELLOW}步骤 1/7: 备份数据库...${NC}"
BACKUP_DIR="backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p $BACKUP_DIR

if [ -f "instance/edu_crm.db" ]; then
    cp instance/edu_crm.db "$BACKUP_DIR/edu_crm_backup_$TIMESTAMP.db"
    echo -e "${GREEN}✓ 数据库已备份到: $BACKUP_DIR/edu_crm_backup_$TIMESTAMP.db${NC}"
else
    echo -e "${RED}错误：找不到数据库文件 instance/edu_crm.db${NC}"
    exit 1
fi

# 3. 停止当前运行的服务
echo -e "${YELLOW}步骤 2/7: 停止当前服务...${NC}"

# 优先使用 systemd 停止服务
if systemctl is-active --quiet crm 2>/dev/null; then
    echo -e "${GREEN}使用 systemctl 停止服务...${NC}"
    sudo systemctl stop crm
    echo -e "${GREEN}✓ systemd 服务已停止${NC}"
else
    # 如果没有 systemd 服务，使用 pkill
    pkill -f "gunicorn.*run:app" 2>/dev/null && echo -e "${GREEN}✓ Gunicorn服务已停止${NC}"
    pkill -f "python.*run.py" 2>/dev/null && echo -e "${GREEN}✓ Python服务已停止${NC}"
    if ! pgrep -f "gunicorn.*run:app\|python.*run.py" > /dev/null; then
        echo -e "${YELLOW}! 没有运行中的服务${NC}"
    fi
fi
sleep 2

# 4. 拉取最新代码
echo -e "${YELLOW}步骤 3/7: 拉取最新代码...${NC}"
git fetch origin
git pull origin master
echo -e "${GREEN}✓ 代码已更新${NC}"

# 5. 激活虚拟环境并安装依赖
echo -e "${YELLOW}步骤 4/7: 检查并安装依赖...${NC}"
if [ ! -d "venv" ]; then
    echo -e "${RED}错误：找不到虚拟环境目录 venv${NC}"
    exit 1
fi

source venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
echo -e "${GREEN}✓ 依赖已安装${NC}"

# 6. 数据库迁移（使用 Python 脚本）
echo -e "${YELLOW}步骤 5/7: 执行数据库迁移...${NC}"

# 使用 Python 迁移脚本（更安全、更完整）
python migrate_database.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 基础数据库迁移完成${NC}"
else
    echo -e "${RED}错误：数据库迁移失败${NC}"
    exit 1
fi

# 执行老师表的 created_by_user_id 字段迁移
echo -e "${YELLOW}执行老师数据隔离迁移...${NC}"
if [ -f "migrations/add_created_by_to_teachers.py" ]; then
    python migrations/add_created_by_to_teachers.py
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 老师数据隔离迁移完成${NC}"
    else
        echo -e "${RED}错误：老师数据隔离迁移失败${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}! 未找到老师数据隔离迁移脚本，跳过${NC}"
fi

# 7. 验证数据库完整性
echo -e "${YELLOW}步骤 6/7: 验证数据库完整性...${NC}"
sqlite3 instance/edu_crm.db "PRAGMA integrity_check;" > /tmp/db_check.txt
if grep -q "ok" /tmp/db_check.txt; then
    echo -e "${GREEN}✓ 数据库完整性检查通过${NC}"
else
    echo -e "${RED}错误：数据库完整性检查失败${NC}"
    cat /tmp/db_check.txt
    exit 1
fi
rm /tmp/db_check.txt

# 8. 启动服务
echo -e "${YELLOW}步骤 7/7: 启动服务...${NC}"

# 创建日志目录
mkdir -p logs

# 检查是否使用 systemd 管理服务
if systemctl is-active --quiet crm 2>/dev/null || [ -f /etc/systemd/system/crm.service ]; then
    echo -e "${GREEN}检测到 systemd 服务配置，使用 systemctl 重启服务...${NC}"
    sudo systemctl restart crm
    sleep 3

    # 检查服务状态
    if systemctl is-active --quiet crm; then
        echo -e "${GREEN}✓ 服务启动成功${NC}"
        sudo systemctl status crm --no-pager -l
    else
        echo -e "${RED}错误：服务启动失败${NC}"
        sudo systemctl status crm --no-pager -l
        exit 1
    fi
else
    echo -e "${YELLOW}未检测到 systemd 服务，使用 Gunicorn 直接启动...${NC}"
    echo -e "${YELLOW}提示：建议使用 systemd 管理服务，运行以下命令安装：${NC}"
    echo -e "${YELLOW}  sudo cp crm.service /etc/systemd/system/${NC}"
    echo -e "${YELLOW}  sudo systemctl daemon-reload${NC}"
    echo -e "${YELLOW}  sudo systemctl enable crm${NC}"
    echo -e "${YELLOW}  sudo systemctl start crm${NC}"
    echo ""

    # 设置环境变量
    export FLASK_ENV=production
    export DATABASE_URL="sqlite:///$(pwd)/instance/edu_crm.db"

    # 使用 Gunicorn 启动服务（生产环境推荐）
    nohup gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 --access-logfile logs/access.log --error-logfile logs/error.log run:app > logs/app.log 2>&1 &
    sleep 3

    # 检查服务是否启动成功
    if pgrep -f "gunicorn.*run:app" > /dev/null; then
        echo -e "${GREEN}✓ 服务启动成功${NC}"
        echo -e "${GREEN}  进程ID: $(pgrep -f 'gunicorn.*run:app' | head -1)${NC}"
        echo -e "${GREEN}  工作进程数: $(pgrep -f 'gunicorn.*run:app' | wc -l)${NC}"
    else
        echo -e "${RED}错误：服务启动失败，请检查日志${NC}"
        tail -20 logs/app.log
        exit 1
    fi
fi

# 9. 显示部署摘要
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "数据库备份: ${GREEN}$BACKUP_DIR/edu_crm_backup_$TIMESTAMP.db${NC}"
echo -e "数据库文件: ${GREEN}instance/edu_crm.db${NC}"
echo -e "日志文件: ${GREEN}logs/app.log${NC}"
echo ""
echo -e "查看应用日志: ${YELLOW}tail -f logs/app.log${NC}"
echo -e "查看访问日志: ${YELLOW}tail -f logs/access.log${NC}"
echo -e "查看错误日志: ${YELLOW}tail -f logs/error.log${NC}"
echo ""

# 根据服务管理方式显示不同的命令
if systemctl is-active --quiet crm 2>/dev/null || [ -f /etc/systemd/system/crm.service ]; then
    echo -e "${GREEN}Systemd 服务管理命令：${NC}"
    echo -e "查看服务状态: ${YELLOW}sudo systemctl status crm${NC}"
    echo -e "停止服务: ${YELLOW}sudo systemctl stop crm${NC}"
    echo -e "启动服务: ${YELLOW}sudo systemctl start crm${NC}"
    echo -e "重启服务: ${YELLOW}sudo systemctl restart crm${NC}"
    echo -e "查看服务日志: ${YELLOW}sudo journalctl -u crm -f${NC}"
else
    echo -e "${GREEN}手动服务管理命令：${NC}"
    echo -e "停止服务: ${YELLOW}pkill -f 'gunicorn.*run:app'${NC}"
    echo -e "查看进程: ${YELLOW}ps aux | grep gunicorn${NC}"
fi
echo ""
echo -e "${GREEN}✓ 所有步骤完成！${NC}"

