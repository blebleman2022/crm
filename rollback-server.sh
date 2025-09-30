#!/bin/bash

# ============================================
# CRM 项目服务器回滚脚本
# ============================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否在项目目录
check_project_dir() {
    if [ ! -f "run.py" ] || [ ! -f "models.py" ]; then
        log_error "请在项目根目录下运行此脚本"
        exit 1
    fi
    log_success "项目目录检查通过"
}

# 检测部署方式
detect_deployment_type() {
    if docker ps -a | grep -q crm; then
        DEPLOYMENT_TYPE="docker"
        log_info "检测到 Docker 部署方式"
    elif systemctl list-units --all | grep -q crm; then
        DEPLOYMENT_TYPE="systemd"
        log_info "检测到 Systemd 部署方式"
    elif supervisorctl status 2>/dev/null | grep -q crm; then
        DEPLOYMENT_TYPE="supervisor"
        log_info "检测到 Supervisor 部署方式"
    else
        DEPLOYMENT_TYPE="direct"
        log_info "使用直接运行方式"
    fi
}

# 停止服务
stop_service() {
    log_info "停止服务..."
    
    case $DEPLOYMENT_TYPE in
        docker)
            if command -v docker-compose &> /dev/null; then
                docker-compose down 2>/dev/null || true
            else
                docker compose down 2>/dev/null || true
            fi
            log_success "Docker 容器已停止"
            ;;
        systemd)
            sudo systemctl stop crm 2>/dev/null || true
            log_success "Systemd 服务已停止"
            ;;
        supervisor)
            sudo supervisorctl stop crm 2>/dev/null || true
            log_success "Supervisor 服务已停止"
            ;;
        direct)
            PID=$(ps aux | grep -v grep | grep "python.*run.py" | awk '{print $2}')
            if [ -n "$PID" ]; then
                kill -15 $PID 2>/dev/null || true
                sleep 2
                log_success "Python 进程已停止"
            fi
            ;;
    esac
}

# 回滚代码
rollback_code() {
    log_info "回滚代码..."
    
    if [ -f ".last_commit" ]; then
        LAST_COMMIT=$(cat .last_commit)
        log_info "回滚到提交: $LAST_COMMIT"
        git reset --hard $LAST_COMMIT
        log_success "代码已回滚"
    else
        log_warning "未找到上次提交记录，请手动指定提交哈希"
        echo ""
        git log --oneline -10
        echo ""
        read -p "请输入要回滚到的提交哈希: " COMMIT_HASH
        git reset --hard $COMMIT_HASH
        log_success "代码已回滚到: $COMMIT_HASH"
    fi
}

# 回滚数据库
rollback_database() {
    log_info "回滚数据库..."
    
    if [ -f ".last_backup" ]; then
        BACKUP_FILE=$(cat .last_backup)
        
        if [ -f "instance/${BACKUP_FILE}" ]; then
            # 备份当前数据库（以防万一）
            if [ -f "instance/edu_crm.db" ]; then
                cp instance/edu_crm.db "instance/edu_crm_before_rollback_$(date +%Y%m%d_%H%M%S).db"
            fi
            
            # 恢复备份
            cp "instance/${BACKUP_FILE}" instance/edu_crm.db
            log_success "数据库已恢复到: ${BACKUP_FILE}"
        else
            log_error "备份文件不存在: instance/${BACKUP_FILE}"
            list_backups
            exit 1
        fi
    else
        log_warning "未找到上次备份记录"
        list_backups
    fi
}

# 列出可用备份
list_backups() {
    echo ""
    log_info "可用的数据库备份："
    echo "----------------------------------------"
    ls -lht instance/edu_crm_backup_*.db 2>/dev/null | head -10 || log_warning "未找到备份文件"
    echo "----------------------------------------"
    echo ""
    read -p "请输入要恢复的备份文件名（或按 Enter 跳过）: " BACKUP_NAME
    
    if [ -n "$BACKUP_NAME" ]; then
        if [ -f "instance/${BACKUP_NAME}" ]; then
            cp "instance/${BACKUP_NAME}" instance/edu_crm.db
            log_success "数据库已恢复到: ${BACKUP_NAME}"
        else
            log_error "备份文件不存在: instance/${BACKUP_NAME}"
            exit 1
        fi
    fi
}

# 启动服务
start_service() {
    log_info "启动服务..."
    
    case $DEPLOYMENT_TYPE in
        docker)
            if command -v docker-compose &> /dev/null; then
                docker-compose build --no-cache
                docker-compose up -d
            else
                docker compose build --no-cache
                docker compose up -d
            fi
            log_success "Docker 容器已启动"
            ;;
        systemd)
            sudo systemctl start crm
            log_success "Systemd 服务已启动"
            ;;
        supervisor)
            sudo supervisorctl start crm
            log_success "Supervisor 服务已启动"
            ;;
        direct)
            if [ -d "venv" ]; then
                source venv/bin/activate
            fi
            nohup python run.py > logs/app.log 2>&1 &
            log_success "Python 进程已启动"
            ;;
    esac
    
    # 等待服务启动
    sleep 5
}

# 验证服务
verify_service() {
    log_info "验证服务状态..."
    
    # 检查服务是否运行
    case $DEPLOYMENT_TYPE in
        docker)
            if docker ps | grep -q crm; then
                log_success "Docker 容器运行正常"
            else
                log_error "Docker 容器未运行"
                return 1
            fi
            ;;
        systemd)
            if systemctl is-active --quiet crm; then
                log_success "Systemd 服务运行正常"
            else
                log_error "Systemd 服务未运行"
                return 1
            fi
            ;;
        supervisor)
            if supervisorctl status crm | grep -q RUNNING; then
                log_success "Supervisor 服务运行正常"
            else
                log_error "Supervisor 服务未运行"
                return 1
            fi
            ;;
        direct)
            if ps aux | grep -v grep | grep -q "python.*run.py"; then
                log_success "Python 进程运行正常"
            else
                log_error "Python 进程未运行"
                return 1
            fi
            ;;
    esac
    
    # 检查应用响应
    log_info "检查应用响应..."
    sleep 3
    
    if curl -f http://localhost:5000/auth/login > /dev/null 2>&1; then
        log_success "应用响应正常"
    else
        log_warning "应用暂时无响应，请稍后检查"
    fi
}

# 显示日志
show_logs() {
    log_info "最近的应用日志："
    echo "----------------------------------------"
    
    case $DEPLOYMENT_TYPE in
        docker)
            if command -v docker-compose &> /dev/null; then
                docker-compose logs --tail=20 crm-app
            else
                docker compose logs --tail=20 crm-app
            fi
            ;;
        *)
            if [ -f "logs/crm.log" ]; then
                tail -20 logs/crm.log
            else
                log_warning "未找到日志文件"
            fi
            ;;
    esac
    
    echo "----------------------------------------"
}

# 主函数
main() {
    echo ""
    echo "========================================"
    echo "  CRM 项目服务器回滚脚本"
    echo "========================================"
    echo ""
    
    # 检查项目目录
    check_project_dir
    
    # 检测部署方式
    detect_deployment_type
    
    # 警告提示
    log_warning "⚠️  回滚操作将："
    echo "  1. 恢复代码到上一个版本"
    echo "  2. 恢复数据库到上一个备份"
    echo "  3. 重启服务"
    echo ""
    
    # 确认回滚
    read -p "确认要回滚吗？(y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "回滚已取消"
        exit 0
    fi
    
    # 执行回滚步骤
    stop_service
    rollback_code
    rollback_database
    start_service
    
    # 验证服务
    if verify_service; then
        log_success "✅ 回滚成功完成！"
        show_logs
        
        echo ""
        log_info "请验证以下功能："
        echo "  - 登录功能"
        echo "  - 线索列表页"
        echo "  - 客户列表页"
        echo "  - 数据完整性"
        echo ""
    else
        log_error "❌ 服务验证失败，请检查日志"
        show_logs
        exit 1
    fi
}

# 运行主函数
main

