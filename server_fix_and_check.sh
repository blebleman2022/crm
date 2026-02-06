#!/bin/bash
# 服务器端一键修复和检查脚本
# 使用方法: 
#   1. 上传此脚本到服务器
#   2. chmod +x server_fix_and_check.sh
#   3. ./server_fix_and_check.sh

set -e  # 遇到错误立即退出

echo "============================================================"
echo "🚀 开始修复外键约束问题"
echo "============================================================"

# 检查是否在正确的目录
if [ ! -f "run.py" ]; then
    echo "❌ 错误: 当前目录不是 CRM 项目根目录"
    echo "请先 cd 到项目目录,然后再运行此脚本"
    exit 1
fi

# 1. 备份数据库
echo ""
echo "📦 第1步: 备份数据库..."
mkdir -p backups
BACKUP_FILE="backups/edu_crm_backup_$(date +%Y%m%d_%H%M%S).db"
cp instance/edu_crm.db "$BACKUP_FILE"
echo "✅ 数据库已备份到: $BACKUP_FILE"

# 2. 拉取最新代码
echo ""
echo "📥 第2步: 拉取最新代码..."
git checkout bak
git pull origin bak
echo "✅ 代码已更新"

# 3. 验证代码更新
echo ""
echo "🔍 第3步: 验证 run.py 是否包含外键配置..."
if grep -q "PRAGMA foreign_keys" run.py; then
    echo "✅ run.py 包含外键配置"
    echo ""
    echo "外键配置代码:"
    grep -A 8 "启用 SQLite 外键约束" run.py || grep -A 8 "PRAGMA foreign_keys" run.py
else
    echo "❌ run.py 中没有找到外键配置!"
    echo "请检查 git pull 是否成功"
    exit 1
fi

# 4. 停止服务
echo ""
echo "🛑 第4步: 停止服务..."
if command -v systemctl &> /dev/null; then
    sudo systemctl stop crm
    echo "✅ 服务已停止 (systemctl)"
elif command -v supervisorctl &> /dev/null; then
    sudo supervisorctl stop crm
    echo "✅ 服务已停止 (supervisor)"
else
    echo "⚠️  未找到 systemctl 或 supervisorctl"
    echo "请手动停止服务,然后按回车继续..."
    read
fi

# 等待进程完全停止
sleep 2

# 5. 检查是否还有残留进程
echo ""
echo "🔍 第5步: 检查残留进程..."
if pgrep -f "python.*run" > /dev/null; then
    echo "⚠️  发现残留进程,正在清理..."
    sudo pkill -9 -f "python.*run" || true
    sleep 1
    echo "✅ 残留进程已清理"
else
    echo "✅ 没有残留进程"
fi

# 6. 启动服务
echo ""
echo "🚀 第6步: 启动服务..."
if command -v systemctl &> /dev/null; then
    sudo systemctl start crm
    echo "✅ 服务已启动 (systemctl)"
elif command -v supervisorctl &> /dev/null; then
    sudo supervisorctl start crm
    echo "✅ 服务已启动 (supervisor)"
else
    echo "⚠️  请手动启动服务,然后按回车继续..."
    read
fi

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 7. 检查服务状态
echo ""
echo "📊 第7步: 检查服务状态..."
if command -v systemctl &> /dev/null; then
    sudo systemctl status crm --no-pager -l || true
elif command -v supervisorctl &> /dev/null; then
    sudo supervisorctl status crm || true
fi

# 8. 运行诊断脚本
echo ""
echo "🔍 第8步: 运行诊断脚本..."
if [ -f "diagnose_fk_issue.py" ]; then
    python3 diagnose_fk_issue.py
else
    echo "⚠️  诊断脚本不存在,跳过诊断"
fi

# 9. 查看最新日志
echo ""
echo "📋 第9步: 查看最新日志 (最后20行)..."
if command -v journalctl &> /dev/null; then
    sudo journalctl -u crm -n 20 --no-pager
else
    echo "⚠️  无法获取日志 (journalctl 不可用)"
fi

echo ""
echo "============================================================"
echo "✅ 修复完成!"
echo "============================================================"
echo ""
echo "📝 后续步骤:"
echo "1. 检查上面的诊断结果,确认外键约束已启用"
echo "2. 登录系统测试班主任分配老师功能"
echo "3. 如果仍有问题,请查看完整日志:"
echo "   sudo journalctl -u crm -n 100 --no-pager"
echo ""
echo "💾 数据库备份位置: $BACKUP_FILE"
echo ""

