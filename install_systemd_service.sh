#!/bin/bash
# EduConnect CRM Systemd 服务安装脚本
# 用途：将 CRM 应用配置为 systemd 服务，实现开机自启和便捷管理
# 使用方法：sudo bash install_systemd_service.sh

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}EduConnect CRM Systemd 服务安装${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查是否以 root 权限运行
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}错误：请使用 sudo 运行此脚本${NC}"
    echo -e "${YELLOW}使用方法：sudo bash install_systemd_service.sh${NC}"
    exit 1
fi

# 检查当前目录
if [ ! -f "run.py" ]; then
    echo -e "${RED}错误：请在项目根目录下运行此脚本${NC}"
    exit 1
fi

# 检查 crm.service 文件是否存在
if [ ! -f "crm.service" ]; then
    echo -e "${RED}错误：找不到 crm.service 文件${NC}"
    exit 1
fi

# 获取当前目录的绝对路径
PROJECT_DIR=$(pwd)
echo -e "${YELLOW}项目目录: ${PROJECT_DIR}${NC}"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${RED}错误：找不到虚拟环境目录 venv${NC}"
    exit 1
fi

# 检查 Gunicorn 是否已安装
if [ ! -f "venv/bin/gunicorn" ]; then
    echo -e "${YELLOW}警告：虚拟环境中未安装 Gunicorn，正在安装...${NC}"
    source venv/bin/activate
    pip install gunicorn -i https://pypi.tuna.tsinghua.edu.cn/simple
    deactivate
    echo -e "${GREEN}✓ Gunicorn 已安装${NC}"
fi

# 创建日志目录
mkdir -p logs
echo -e "${GREEN}✓ 日志目录已创建${NC}"

# 停止现有服务（如果存在）
echo -e "${YELLOW}检查并停止现有服务...${NC}"
if systemctl is-active --quiet crm 2>/dev/null; then
    systemctl stop crm
    echo -e "${GREEN}✓ 已停止现有 systemd 服务${NC}"
fi

# 停止手动启动的进程
pkill -f "gunicorn.*run:app" 2>/dev/null && echo -e "${GREEN}✓ 已停止手动启动的 Gunicorn 进程${NC}" || true
pkill -f "python.*run.py" 2>/dev/null && echo -e "${GREEN}✓ 已停止手动启动的 Python 进程${NC}" || true

# 复制服务文件到 systemd 目录
echo -e "${YELLOW}安装 systemd 服务文件...${NC}"
cp crm.service /etc/systemd/system/crm.service
echo -e "${GREEN}✓ 服务文件已复制到 /etc/systemd/system/crm.service${NC}"

# 重新加载 systemd 配置
echo -e "${YELLOW}重新加载 systemd 配置...${NC}"
systemctl daemon-reload
echo -e "${GREEN}✓ systemd 配置已重新加载${NC}"

# 启用服务（开机自启）
echo -e "${YELLOW}启用服务（开机自启）...${NC}"
systemctl enable crm
echo -e "${GREEN}✓ 服务已设置为开机自启${NC}"

# 启动服务
echo -e "${YELLOW}启动服务...${NC}"
systemctl start crm
sleep 3

# 检查服务状态
if systemctl is-active --quiet crm; then
    echo -e "${GREEN}✓ 服务启动成功！${NC}"
    echo ""
    systemctl status crm --no-pager -l
else
    echo -e "${RED}错误：服务启动失败${NC}"
    echo ""
    systemctl status crm --no-pager -l
    exit 1
fi

# 显示安装摘要
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}安装完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}服务管理命令：${NC}"
echo -e "查看服务状态: ${YELLOW}sudo systemctl status crm${NC}"
echo -e "停止服务: ${YELLOW}sudo systemctl stop crm${NC}"
echo -e "启动服务: ${YELLOW}sudo systemctl start crm${NC}"
echo -e "重启服务: ${YELLOW}sudo systemctl restart crm${NC}"
echo -e "查看实时日志: ${YELLOW}sudo journalctl -u crm -f${NC}"
echo -e "查看最近日志: ${YELLOW}sudo journalctl -u crm -n 100${NC}"
echo -e "禁用开机自启: ${YELLOW}sudo systemctl disable crm${NC}"
echo ""
echo -e "${GREEN}应用日志文件：${NC}"
echo -e "应用日志: ${YELLOW}${PROJECT_DIR}/logs/app.log${NC}"
echo -e "访问日志: ${YELLOW}${PROJECT_DIR}/logs/access.log${NC}"
echo -e "错误日志: ${YELLOW}${PROJECT_DIR}/logs/error.log${NC}"
echo ""
echo -e "${GREEN}✓ 现在可以使用 'sudo systemctl restart crm' 重启服务了！${NC}"

