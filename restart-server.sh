#!/bin/bash

# ========================================
# CRM 服务器重启脚本（直接部署版本）
# ========================================
# 适用于非 Docker 部署方式
# 支持：systemd / supervisor / 手动进程 / gunicorn
# ========================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置变量
PROJECT_DIR="/crm"  # 修改为你的实际项目路径
VENV_PATH="${PROJECT_DIR}/venv"
LOG_DIR="${PROJECT_DIR}/logs"
DB_PATH="${PROJECT_DIR}/instance/edu_crm.db"

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

# 检测部署方式
detect_deployment_type() {
    log_info "检测部署方式..."
    
    # 检查 systemd
    if systemctl list-units --type=service 2>/dev/null | grep -q crm; then
        echo "systemd"
        return
    fi
    
    # 检查 supervisor
    if command -v supervisorctl &> /dev/null; then
        if supervisorctl status 2>/dev/null | grep -q crm; then
            echo "supervisor"
            return
        fi
    fi
    
    # 检查 gunicorn
    if ps aux | grep -v grep | grep -q "gunicorn.*run:app"; then
        echo "gunicorn"
        return
    fi
    
    # 检查直接运行的 Python 进程
    if ps aux | grep -v grep | grep -q "python.*run.py"; then
        echo "python"
        return
    fi
    
    echo "unknown"
}

# 备份数据库
backup_database() {
    log_info "备份数据库..."
    
    if [ -f "$DB_PATH" ]; then
        BACKUP_FILE="${PROJECT_DIR}/instance/edu_crm_backup_$(date +%Y%m%d_%H%M%S).db"
        cp "$DB_PATH" "$BACKUP_FILE"
        if [ $? -eq 0 ]; then
            log_success "数据库已备份到: $BACKUP_FILE"
        else
            log_error "数据库备份失败"
            return 1
        fi
    else
        log_warning "未找到数据库文件: $DB_PATH"
    fi
}

# 拉取最新代码
pull_latest_code() {
    log_info "拉取最新代码..."
    
    cd "$PROJECT_DIR" || exit 1
    
    # 检查是否有未提交的更改
    if ! git diff-index --quiet HEAD --; then
        log_warning "检测到本地有未提交的更改"
        read -p "是否要暂存本地更改并继续？(y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git stash
            log_info "本地更改已暂存"
        else
            log_error "取消更新"
            return 1
        fi
    fi
    
    git pull origin master
    if [ $? -eq 0 ]; then
        log_success "代码更新成功"
    else
        log_error "代码更新失败"
        return 1
    fi
}

# 更新依赖
update_dependencies() {
    log_info "检查并更新依赖..."
    
    if [ -d "$VENV_PATH" ]; then
        source "$VENV_PATH/bin/activate"
        pip install -r "$PROJECT_DIR/requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple --quiet
        if [ $? -eq 0 ]; then
            log_success "依赖更新成功"
        else
            log_warning "依赖更新失败，但继续执行"
        fi
    else
        log_warning "未找到虚拟环境: $VENV_PATH"
    fi
}

# 重启服务 - systemd
restart_systemd() {
    log_info "使用 systemd 重启服务..."
    
    sudo systemctl restart crm
    if [ $? -eq 0 ]; then
        log_success "服务重启成功"
        sleep 2
        sudo systemctl status crm --no-pager
    else
        log_error "服务重启失败"
        return 1
    fi
}

# 重启服务 - supervisor
restart_supervisor() {
    log_info "使用 supervisor 重启服务..."
    
    sudo supervisorctl restart crm
    if [ $? -eq 0 ]; then
        log_success "服务重启成功"
        sleep 2
        sudo supervisorctl status crm
    else
        log_error "服务重启失败"
        return 1
    fi
}

# 重启服务 - gunicorn
restart_gunicorn() {
    log_info "重启 Gunicorn 服务..."
    
    # 停止旧进程
    log_info "停止旧进程..."
    pkill -f "gunicorn.*run:app"
    sleep 2
    
    # 确认进程已停止
    if ps aux | grep -v grep | grep -q "gunicorn.*run:app"; then
        log_warning "进程未完全停止，强制终止..."
        pkill -9 -f "gunicorn.*run:app"
        sleep 1
    fi
    
    # 启动新进程
    log_info "启动新进程..."
    cd "$PROJECT_DIR" || exit 1
    source "$VENV_PATH/bin/activate"
    
    mkdir -p "$LOG_DIR"
    nohup gunicorn -c gunicorn.conf.py run:app > "$LOG_DIR/gunicorn.log" 2>&1 &
    
    sleep 3
    
    # 验证启动
    if ps aux | grep -v grep | grep -q "gunicorn.*run:app"; then
        log_success "Gunicorn 启动成功"
        ps aux | grep gunicorn | grep -v grep
    else
        log_error "Gunicorn 启动失败"
        log_info "查看日志: tail -f $LOG_DIR/gunicorn.log"
        return 1
    fi
}

# 重启服务 - python
restart_python() {
    log_info "重启 Python 进程..."
    
    # 停止旧进程
    log_info "停止旧进程..."
    pkill -f "python.*run.py"
    sleep 2
    
    # 确认进程已停止
    if ps aux | grep -v grep | grep -q "python.*run.py"; then
        log_warning "进程未完全停止，强制终止..."
        pkill -9 -f "python.*run.py"
        sleep 1
    fi
    
    # 启动新进程
    log_info "启动新进程..."
    cd "$PROJECT_DIR" || exit 1
    source "$VENV_PATH/bin/activate"
    
    mkdir -p "$LOG_DIR"
    nohup python run.py > "$LOG_DIR/crm.log" 2>&1 &
    
    sleep 3
    
    # 验证启动
    if ps aux | grep -v grep | grep -q "python.*run.py"; then
        log_success "Python 进程启动成功"
        ps aux | grep python | grep run.py | grep -v grep
    else
        log_error "Python 进程启动失败"
        log_info "查看日志: tail -f $LOG_DIR/crm.log"
        return 1
    fi
}

# 验证服务
verify_service() {
    log_info "验证服务状态..."
    
    # 等待服务启动
    sleep 3
    
    # 检查端口
    if netstat -tlnp 2>/dev/null | grep -q ":5000"; then
        log_success "端口 5000 正在监听"
    else
        log_warning "端口 5000 未监听"
    fi
    
    # 测试 HTTP 响应
    log_info "测试 HTTP 响应..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/auth/login 2>/dev/null)
    
    if [ "$HTTP_CODE" = "200" ]; then
        log_success "服务响应正常 (HTTP $HTTP_CODE)"
    else
        log_warning "服务响应异常 (HTTP $HTTP_CODE)"
    fi
}

# 主函数
main() {
    echo ""
    echo "========================================"
    echo "  CRM 服务器重启脚本"
    echo "========================================"
    echo ""
    
    # 检查是否在项目目录
    if [ ! -f "$PROJECT_DIR/run.py" ]; then
        log_error "项目目录不存在或配置错误: $PROJECT_DIR"
        log_info "请修改脚本中的 PROJECT_DIR 变量"
        exit 1
    fi
    
    # 检测部署方式
    DEPLOY_TYPE=$(detect_deployment_type)
    log_info "检测到部署方式: $DEPLOY_TYPE"
    
    if [ "$DEPLOY_TYPE" = "unknown" ]; then
        log_error "无法检测到部署方式"
        log_info "请手动指定部署方式或检查服务是否正在运行"
        exit 1
    fi
    
    # 确认重启
    read -p "确认要重启 CRM 服务吗？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "取消重启"
        exit 0
    fi
    
    # 执行重启流程
    backup_database || exit 1
    pull_latest_code || exit 1
    update_dependencies
    
    # 根据部署方式重启
    case "$DEPLOY_TYPE" in
        systemd)
            restart_systemd || exit 1
            ;;
        supervisor)
            restart_supervisor || exit 1
            ;;
        gunicorn)
            restart_gunicorn || exit 1
            ;;
        python)
            restart_python || exit 1
            ;;
        *)
            log_error "未知的部署方式: $DEPLOY_TYPE"
            exit 1
            ;;
    esac
    
    # 验证服务
    verify_service
    
    echo ""
    echo "========================================"
    echo "  重启完成！"
    echo "========================================"
    echo ""
    log_info "查看日志: tail -f $LOG_DIR/*.log"
    log_info "访问地址: http://your-server-ip:5000"
    echo ""
}

# 运行主函数
main

