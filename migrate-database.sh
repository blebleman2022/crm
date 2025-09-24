#!/bin/bash

# 数据库迁移脚本 - 将本地数据库迁移到云端
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
SERVER_IP="47.100.238.50"
SERVER_USER="root"
LOCAL_DB_PATH="./instance/edu_crm.db"
REMOTE_DB_DIR="/var/lib/crm/instance"
BACKUP_DIR="./database_backups"

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

# 检查本地数据库
check_local_database() {
    log_info "检查本地数据库..."
    
    if [ ! -f "$LOCAL_DB_PATH" ]; then
        log_error "本地数据库文件不存在: $LOCAL_DB_PATH"
        exit 1
    fi
    
    # 检查数据库大小
    local db_size=$(ls -lh "$LOCAL_DB_PATH" | awk '{print $5}')
    log_success "本地数据库文件存在，大小: $db_size"
    
    # 检查数据库内容
    log_info "检查数据库内容..."
    sqlite3 "$LOCAL_DB_PATH" "
    .mode column
    .headers on
    SELECT 'users' as table_name, COUNT(*) as count FROM users
    UNION ALL
    SELECT 'leads', COUNT(*) FROM leads
    UNION ALL
    SELECT 'customers', COUNT(*) FROM customers
    UNION ALL
    SELECT 'consultations', COUNT(*) FROM consultations;
    "
}

# 创建本地备份
create_local_backup() {
    log_info "创建本地备份..."
    
    mkdir -p "$BACKUP_DIR"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/edu_crm_backup_${timestamp}.db"
    
    cp "$LOCAL_DB_PATH" "$backup_file"
    log_success "本地备份创建完成: $backup_file"
    
    # 压缩备份
    gzip "$backup_file"
    log_success "备份已压缩: ${backup_file}.gz"
}

# 上传数据库到服务器
upload_database() {
    log_info "上传数据库到服务器..."
    
    # 检查服务器连接
    if ! ssh -o ConnectTimeout=10 "$SERVER_USER@$SERVER_IP" "echo '服务器连接正常'"; then
        log_error "无法连接到服务器 $SERVER_IP"
        exit 1
    fi
    
    # 在服务器上创建目录
    ssh "$SERVER_USER@$SERVER_IP" "
        mkdir -p $REMOTE_DB_DIR
        chmod 755 $REMOTE_DB_DIR
    "
    
    # 备份服务器上的现有数据库（如果存在）
    ssh "$SERVER_USER@$SERVER_IP" "
        if [ -f $REMOTE_DB_DIR/edu_crm.db ]; then
            echo '备份服务器现有数据库...'
            cp $REMOTE_DB_DIR/edu_crm.db $REMOTE_DB_DIR/edu_crm_server_backup_\$(date +%Y%m%d_%H%M%S).db
        fi
    "
    
    # 上传数据库文件
    log_info "正在上传数据库文件..."
    scp "$LOCAL_DB_PATH" "$SERVER_USER@$SERVER_IP:$REMOTE_DB_DIR/edu_crm.db"
    
    # 设置权限
    ssh "$SERVER_USER@$SERVER_IP" "
        chmod 666 $REMOTE_DB_DIR/edu_crm.db
        chown -R 1000:1000 $REMOTE_DB_DIR
    "
    
    log_success "数据库上传完成"
}

# 验证服务器数据库
verify_remote_database() {
    log_info "验证服务器数据库..."
    
    ssh "$SERVER_USER@$SERVER_IP" "
        echo '检查数据库文件...'
        ls -la $REMOTE_DB_DIR/
        
        echo ''
        echo '检查数据库内容...'
        sqlite3 $REMOTE_DB_DIR/edu_crm.db \"
        .mode column
        .headers on
        SELECT 'users' as table_name, COUNT(*) as count FROM users
        UNION ALL
        SELECT 'leads', COUNT(*) FROM leads
        UNION ALL
        SELECT 'customers', COUNT(*) FROM customers
        UNION ALL
        SELECT 'consultations', COUNT(*) FROM consultations;
        \"
    "
}

# 重启应用容器
restart_application() {
    log_info "重启应用容器..."
    
    ssh "$SERVER_USER@$SERVER_IP" "
        # 停止现有容器
        docker stop crm-app 2>/dev/null || true
        docker stop crm-app-fixed 2>/dev/null || true
        docker stop o5b578f64f6 2>/dev/null || true
        
        # 删除现有容器
        docker rm crm-app 2>/dev/null || true
        docker rm crm-app-fixed 2>/dev/null || true
        docker rm o5b578f64f6 2>/dev/null || true
        
        # 启动新容器
        docker run -d \\
            --name crm-app \\
            --restart unless-stopped \\
            -p 80:80 \\
            -e FLASK_ENV=production \\
            -e DATABASE_URL=sqlite:///instance/edu_crm.db \\
            -e SECRET_KEY=crm-production-secret-\$(date +%s) \\
            -v $REMOTE_DB_DIR:/app/instance \\
            -v /var/lib/crm/logs:/app/logs \\
            crm-app:latest
        
        echo '等待容器启动...'
        sleep 15
        
        echo '检查容器状态...'
        docker ps | grep crm-app
        
        echo '检查应用日志...'
        docker logs crm-app | tail -10
    "
}

# 测试应用访问
test_application() {
    log_info "测试应用访问..."
    
    # 等待应用完全启动
    sleep 30
    
    # 测试健康检查
    if curl -f "http://$SERVER_IP/health" > /dev/null 2>&1; then
        log_success "✅ 健康检查通过"
    else
        log_warning "健康检查失败，尝试登录页面..."
        
        if curl -f "http://$SERVER_IP/auth/login" > /dev/null 2>&1; then
            log_success "✅ 登录页面可访问"
        else
            log_error "❌ 应用无法访问"
            return 1
        fi
    fi
    
    # 获取健康检查详细信息
    log_info "获取应用状态..."
    curl -s "http://$SERVER_IP/health" | python3 -m json.tool 2>/dev/null || echo "无法获取JSON响应"
}

# 显示迁移结果
show_migration_result() {
    log_success "🎉 数据库迁移完成！"
    echo "================================"
    log_info "📊 迁移信息:"
    echo "  本地数据库: $LOCAL_DB_PATH"
    echo "  服务器数据库: $SERVER_USER@$SERVER_IP:$REMOTE_DB_DIR/edu_crm.db"
    echo "  应用地址: http://$SERVER_IP"
    echo ""
    log_info "🔧 管理命令:"
    echo "  查看日志: ssh $SERVER_USER@$SERVER_IP 'docker logs -f crm-app'"
    echo "  重启应用: ssh $SERVER_USER@$SERVER_IP 'docker restart crm-app'"
    echo "  进入容器: ssh $SERVER_USER@$SERVER_IP 'docker exec -it crm-app bash'"
    echo ""
    log_info "💾 备份位置:"
    echo "  本地备份: $BACKUP_DIR/"
    echo "  服务器备份: $SERVER_USER@$SERVER_IP:$REMOTE_DB_DIR/edu_crm_server_backup_*"
}

# 主函数
main() {
    echo "🚀 开始数据库迁移..."
    echo "================================"
    echo "从: $LOCAL_DB_PATH"
    echo "到: $SERVER_USER@$SERVER_IP:$REMOTE_DB_DIR"
    echo "================================"
    
    # 确认操作
    read -p "确认开始迁移？这将覆盖服务器上的现有数据库 (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "迁移已取消"
        exit 0
    fi
    
    check_local_database
    create_local_backup
    upload_database
    verify_remote_database
    restart_application
    test_application
    show_migration_result
    
    echo "================================"
    log_success "迁移完成！"
}

# 执行主函数
main "$@"
