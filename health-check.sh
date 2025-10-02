#!/bin/bash

# ============================================
# CRM系统健康检查脚本
# ============================================
# 
# 功能：
# 1. 检查服务状态
# 2. 检查HTTP响应
# 3. 检查数据库连接
# 4. 自动重启故障服务
#
# 使用方法：
#   bash health-check.sh
#
# 定时任务（每5分钟检查一次）：
#   */5 * * * * /root/crm/health-check.sh >> /var/log/crm/health-check.log 2>&1
#
# ============================================

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 检查systemd服务状态
check_service() {
    if systemctl is-active --quiet crm; then
        log "✓ CRM服务运行正常"
        return 0
    else
        log "✗ CRM服务未运行"
        return 1
    fi
}

# 检查HTTP响应
check_http() {
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health 2>/dev/null)
    
    if [ "$HTTP_CODE" = "200" ]; then
        log "✓ HTTP健康检查通过 (状态码: $HTTP_CODE)"
        return 0
    else
        log "✗ HTTP健康检查失败 (状态码: $HTTP_CODE)"
        return 1
    fi
}

# 检查端口监听
check_port() {
    if netstat -tuln 2>/dev/null | grep -q ":5000"; then
        log "✓ 端口5000正在监听"
        return 0
    else
        log "✗ 端口5000未监听"
        return 1
    fi
}

# 检查数据库文件
check_database() {
    DB_FILE="/root/crm/instance/edu_crm.db"
    
    if [ -f "$DB_FILE" ]; then
        DB_SIZE=$(du -h "$DB_FILE" | cut -f1)
        log "✓ 数据库文件存在 (大小: $DB_SIZE)"
        return 0
    else
        log "✗ 数据库文件不存在"
        return 1
    fi
}

# 检查磁盘空间
check_disk() {
    DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$DISK_USAGE" -lt 90 ]; then
        log "✓ 磁盘空间充足 (使用率: ${DISK_USAGE}%)"
        return 0
    else
        log "⚠ 磁盘空间不足 (使用率: ${DISK_USAGE}%)"
        return 1
    fi
}

# 检查内存使用
check_memory() {
    MEM_USAGE=$(free | awk 'NR==2 {printf "%.0f", $3/$2 * 100}')
    
    if [ "$MEM_USAGE" -lt 90 ]; then
        log "✓ 内存使用正常 (使用率: ${MEM_USAGE}%)"
        return 0
    else
        log "⚠ 内存使用过高 (使用率: ${MEM_USAGE}%)"
        return 1
    fi
}

# 重启服务
restart_service() {
    log "⚠ 尝试重启CRM服务..."
    systemctl restart crm
    sleep 5
    
    if systemctl is-active --quiet crm; then
        log "✓ CRM服务重启成功"
        
        # 发送通知（可选）
        # send_notification "CRM服务已自动重启"
        
        return 0
    else
        log "✗ CRM服务重启失败"
        
        # 发送告警（可选）
        # send_alert "CRM服务重启失败，需要人工介入"
        
        return 1
    fi
}

# 发送通知（示例，需要配置邮件或其他通知方式）
send_notification() {
    MESSAGE="$1"
    # echo "$MESSAGE" | mail -s "CRM系统通知" admin@example.com
    log "通知: $MESSAGE"
}

# 发送告警（示例，需要配置邮件或其他通知方式）
send_alert() {
    MESSAGE="$1"
    # echo "$MESSAGE" | mail -s "CRM系统告警" admin@example.com
    log "告警: $MESSAGE"
}

# 主检查流程
main() {
    log "========================================="
    log "开始健康检查"
    log "========================================="
    
    FAILED=0
    
    # 检查服务状态
    if ! check_service; then
        FAILED=$((FAILED + 1))
        restart_service
    fi
    
    # 检查HTTP响应
    if ! check_http; then
        FAILED=$((FAILED + 1))
        
        # 如果HTTP检查失败，尝试重启
        if [ $FAILED -eq 1 ]; then
            restart_service
        fi
    fi
    
    # 检查端口监听
    check_port || FAILED=$((FAILED + 1))
    
    # 检查数据库
    check_database || FAILED=$((FAILED + 1))
    
    # 检查磁盘空间
    check_disk
    
    # 检查内存使用
    check_memory
    
    # 总结
    log "========================================="
    if [ $FAILED -eq 0 ]; then
        log "✓ 所有检查通过"
    else
        log "⚠ 发现 $FAILED 个问题"
    fi
    log "========================================="
    log ""
    
    return $FAILED
}

# 执行主流程
main
exit $?

