#!/bin/bash

# CRM项目部署问题修复脚本
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

echo "🔧 CRM项目部署问题诊断和修复"
echo "================================"

# 1. 检查容器状态
check_container_status() {
    log_info "检查容器状态..."
    docker compose ps
    echo ""
}

# 2. 查看完整错误日志
show_full_logs() {
    log_info "查看完整错误日志..."
    docker compose logs crm-development | tail -50
    echo ""
}

# 3. 检查数据库文件
check_database_file() {
    log_info "检查数据库文件..."
    
    if [ -f "./instance/edu_crm.db" ]; then
        log_success "数据库文件存在"
        ls -la ./instance/edu_crm.db
        
        # 检查文件权限
        local perms=$(stat -c "%a" ./instance/edu_crm.db)
        if [ "$perms" != "666" ]; then
            log_warning "数据库文件权限不正确: $perms"
            log_info "修复权限..."
            chmod 666 ./instance/edu_crm.db
            log_success "权限已修复为666"
        else
            log_success "数据库文件权限正确: $perms"
        fi
        
        # 检查文件大小
        local size=$(stat -c "%s" ./instance/edu_crm.db)
        if [ "$size" -eq 0 ]; then
            log_error "数据库文件为空！"
            return 1
        else
            log_success "数据库文件大小: ${size} bytes"
        fi
    else
        log_error "数据库文件不存在: ./instance/edu_crm.db"
        return 1
    fi
    echo ""
}

# 4. 检查目录权限
check_directory_permissions() {
    log_info "检查目录权限..."
    
    # 检查instance目录
    if [ -d "./instance" ]; then
        local perms=$(stat -c "%a" ./instance)
        log_info "instance目录权限: $perms"
        if [ "$perms" != "755" ]; then
            chmod 755 ./instance
            log_success "已修复instance目录权限"
        fi
    else
        log_warning "instance目录不存在，创建中..."
        mkdir -p ./instance
        chmod 755 ./instance
    fi
    
    # 检查logs目录
    if [ -d "./logs" ]; then
        local perms=$(stat -c "%a" ./logs)
        log_info "logs目录权限: $perms"
        if [ "$perms" != "755" ]; then
            chmod 755 ./logs
            log_success "已修复logs目录权限"
        fi
    else
        log_warning "logs目录不存在，创建中..."
        mkdir -p ./logs
        chmod 755 ./logs
    fi
    echo ""
}

# 5. 进入容器诊断
diagnose_in_container() {
    log_info "进入容器进行详细诊断..."
    
    docker compose exec crm-development bash -c "
    echo '=== 容器内部诊断 ==='
    echo '当前用户:' \$(whoami)
    echo '当前目录:' \$(pwd)
    echo '用户ID:' \$(id)
    echo ''
    
    echo '=== 检查Python环境 ==='
    python --version
    echo ''
    
    echo '=== 检查文件权限 ==='
    ls -la /app/instance/ 2>/dev/null || echo '❌ instance目录问题'
    ls -la /app/logs/ 2>/dev/null || echo '❌ logs目录问题'
    echo ''
    
    echo '=== 测试数据库连接 ==='
    python -c \"
import os
import sqlite3
try:
    db_path = '/app/instance/edu_crm.db'
    if os.path.exists(db_path):
        print(f'✅ 数据库文件存在: {db_path}')
        print(f'文件大小: {os.path.getsize(db_path)} bytes')
        
        # 测试SQLite连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM sqlite_master WHERE type=\\\"table\\\";')
        tables = cursor.fetchall()
        print(f'✅ 数据库表数量: {len(tables)}')
        for table in tables:
            print(f'  - {table[0]}')
        conn.close()
        print('✅ SQLite连接测试成功')
    else:
        print(f'❌ 数据库文件不存在: {db_path}')
except Exception as e:
    print(f'❌ 数据库连接失败: {e}')
\"
    
    echo ''
    echo '=== 测试Flask应用导入 ==='
    python -c \"
try:
    from run import app
    print('✅ Flask应用导入成功')
    print(f'应用名称: {app.name}')
    print(f'应用配置: {app.config.get(\\\"ENV\\\", \\\"unknown\\\")}')
    print(f'数据库URI: {app.config.get(\\\"SQLALCHEMY_DATABASE_URI\\\")}')
except Exception as e:
    print(f'❌ Flask应用导入失败: {e}')
    import traceback
    traceback.print_exc()
\"
    "
    echo ""
}

# 6. 修复docker-compose.yml版本警告
fix_compose_version() {
    log_info "修复docker-compose.yml版本警告..."
    
    if grep -q "version:" docker-compose.yml; then
        log_info "移除过时的version字段..."
        sed -i '/^version:/d' docker-compose.yml
        log_success "已移除version字段"
    else
        log_success "docker-compose.yml无需修复"
    fi
    echo ""
}

# 7. 重新构建和启动
rebuild_and_restart() {
    log_info "重新构建和启动容器..."
    
    # 停止容器
    log_info "停止现有容器..."
    docker compose down
    
    # 清理旧镜像（可选）
    log_info "清理旧镜像..."
    docker image prune -f
    
    # 重新构建
    log_info "重新构建镜像..."
    docker compose build --no-cache
    
    # 启动容器
    log_info "启动容器..."
    docker compose up -d
    
    # 等待启动
    log_info "等待容器启动..."
    sleep 10
    
    # 检查状态
    log_info "检查容器状态..."
    docker compose ps
    echo ""
}

# 8. 测试应用访问
test_application() {
    log_info "测试应用访问..."
    
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:5000/auth/login > /dev/null 2>&1; then
            log_success "✅ 应用访问测试成功！"
            echo "访问地址: http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_SERVER_IP'):5000"
            return 0
        fi
        
        log_info "等待应用启动... ($attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
    
    log_warning "应用访问测试失败，请检查日志"
    return 1
}

# 主修复流程
main() {
    check_container_status
    show_full_logs
    check_database_file || {
        log_error "数据库文件问题，请确保instance/edu_crm.db文件存在且不为空"
        exit 1
    }
    check_directory_permissions
    fix_compose_version
    
    # 如果容器正在运行，进行容器内诊断
    if docker compose ps | grep "Up" > /dev/null; then
        diagnose_in_container
    fi
    
    # 询问是否重新构建
    echo ""
    read -p "是否重新构建和启动容器？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rebuild_and_restart
        test_application
    fi
    
    echo ""
    echo "================================"
    log_info "修复完成！"
    echo ""
    echo "如果问题仍然存在，请运行："
    echo "  docker compose logs -f crm-development"
    echo ""
    echo "或者查看详细日志："
    echo "  docker compose exec crm-development bash"
}

# 执行主函数
main "$@"
