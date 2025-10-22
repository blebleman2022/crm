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

if [ -f "instance/edu_crm_1022.db" ]; then
    cp instance/edu_crm_1022.db "$BACKUP_DIR/edu_crm_1022_backup_$TIMESTAMP.db"
    echo -e "${GREEN}✓ 数据库已备份到: $BACKUP_DIR/edu_crm_1022_backup_$TIMESTAMP.db${NC}"
else
    echo -e "${RED}错误：找不到数据库文件 instance/edu_crm_1022.db${NC}"
    exit 1
fi

# 3. 停止当前运行的服务
echo -e "${YELLOW}步骤 2/7: 停止当前服务...${NC}"
pkill -f "python.*run.py" 2>/dev/null && echo -e "${GREEN}✓ 服务已停止${NC}" || echo -e "${YELLOW}! 没有运行中的服务${NC}"
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

# 6. 数据库迁移（添加新表）
echo -e "${YELLOW}步骤 5/7: 执行数据库迁移...${NC}"

# 检查是否需要添加 teachers 表
NEED_MIGRATION=$(sqlite3 instance/edu_crm_1022.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='teachers'")

if [ "$NEED_MIGRATION" -eq "0" ]; then
    echo -e "${YELLOW}检测到需要添加 teachers 表...${NC}"
    
    # 创建迁移脚本
    cat > /tmp/migrate_teachers.sql << 'EOF'
-- 创建 teachers 表
CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(120),
    specialization TEXT,
    education_background TEXT,
    work_experience TEXT,
    teaching_subjects TEXT,
    hourly_rate FLOAT,
    status VARCHAR(20) DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建 teacher_images 表
CREATE TABLE IF NOT EXISTS teacher_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    image_path VARCHAR(500) NOT NULL,
    image_type VARCHAR(50),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES teachers (id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_teachers_phone ON teachers(phone);
CREATE INDEX IF NOT EXISTS idx_teachers_status ON teachers(status);
CREATE INDEX IF NOT EXISTS idx_teacher_images_teacher_id ON teacher_images(teacher_id);
EOF

    # 执行迁移
    sqlite3 instance/edu_crm_1022.db < /tmp/migrate_teachers.sql
    rm /tmp/migrate_teachers.sql
    
    echo -e "${GREEN}✓ 数据库迁移完成（已添加 teachers 和 teacher_images 表）${NC}"
else
    echo -e "${GREEN}✓ 数据库结构已是最新，无需迁移${NC}"
fi

# 7. 验证数据库完整性
echo -e "${YELLOW}步骤 6/7: 验证数据库完整性...${NC}"
sqlite3 instance/edu_crm_1022.db "PRAGMA integrity_check;" > /tmp/db_check.txt
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

# 设置环境变量
export FLASK_ENV=production
export DATABASE_URL="sqlite:///$(pwd)/instance/edu_crm_1022.db"

# 后台启动服务
nohup python run.py > logs/app.log 2>&1 &
sleep 3

# 检查服务是否启动成功
if pgrep -f "python.*run.py" > /dev/null; then
    echo -e "${GREEN}✓ 服务启动成功${NC}"
    echo -e "${GREEN}  进程ID: $(pgrep -f 'python.*run.py')${NC}"
else
    echo -e "${RED}错误：服务启动失败，请检查日志${NC}"
    tail -20 logs/app.log
    exit 1
fi

# 9. 显示部署摘要
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "数据库备份: ${GREEN}$BACKUP_DIR/edu_crm_1022_backup_$TIMESTAMP.db${NC}"
echo -e "数据库文件: ${GREEN}instance/edu_crm_1022.db${NC}"
echo -e "日志文件: ${GREEN}logs/app.log${NC}"
echo ""
echo -e "查看日志: ${YELLOW}tail -f logs/app.log${NC}"
echo -e "停止服务: ${YELLOW}pkill -f 'python.*run.py'${NC}"
echo -e "查看进程: ${YELLOW}ps aux | grep 'python.*run.py'${NC}"
echo ""
echo -e "${GREEN}✓ 所有步骤完成！${NC}"

