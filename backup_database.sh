#!/bin/bash

# CRM 数据库自动备份脚本
# 用途：每天凌晨3点自动备份数据库文件
# 作者：CRM Team
# 最后更新：2025-10-04

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置项
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
DB_FILE="$PROJECT_DIR/instance/edu_crm.db"
BACKUP_DIR="$PROJECT_DIR/bak"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/edu_crm_$TIMESTAMP.db"
LOG_FILE="$BACKUP_DIR/backup.log"

# 保留最近N天的备份（默认30天）
KEEP_DAYS=30

# 创建备份目录（如果不存在）- 必须在日志函数之前创建
if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p "$BACKUP_DIR"
fi

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $1${NC}" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1${NC}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] ℹ️  $1${NC}" | tee -a "$LOG_FILE"
}

# 开始备份
log "=========================================="
log "开始数据库备份任务"
log "=========================================="

# 检查数据库文件是否存在
if [ ! -f "$DB_FILE" ]; then
    log_error "数据库文件不存在：$DB_FILE"
    exit 1
fi

# 确认备份目录已创建
log_info "备份目录：$BACKUP_DIR"

# 获取数据库文件大小
DB_SIZE=$(du -h "$DB_FILE" | cut -f1)
log_info "数据库文件大小：$DB_SIZE"

# 执行备份
log_info "正在备份数据库..."
cp "$DB_FILE" "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log_success "备份成功！"
    log_info "备份文件：$BACKUP_FILE"
    log_info "备份大小：$BACKUP_SIZE"
else
    log_error "备份失败！"
    exit 1
fi

# 验证备份文件完整性
if [ -f "$BACKUP_FILE" ]; then
    # 使用 SQLite 检查数据库完整性
    if command -v sqlite3 &> /dev/null; then
        log_info "正在验证备份文件完整性..."
        INTEGRITY_CHECK=$(sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" 2>&1)
        
        if [ "$INTEGRITY_CHECK" = "ok" ]; then
            log_success "备份文件完整性验证通过"
        else
            log_error "备份文件完整性验证失败：$INTEGRITY_CHECK"
            # 删除损坏的备份文件
            rm -f "$BACKUP_FILE"
            exit 1
        fi
    else
        log_info "未安装 sqlite3，跳过完整性验证"
    fi
else
    log_error "备份文件不存在：$BACKUP_FILE"
    exit 1
fi

# 清理旧备份（保留最近N天）
log_info "正在清理 $KEEP_DAYS 天前的旧备份..."
DELETED_COUNT=0

# 查找并删除超过N天的备份文件
find "$BACKUP_DIR" -name "edu_crm_*.db" -type f -mtime +$KEEP_DAYS | while read old_backup; do
    log_info "删除旧备份：$(basename "$old_backup")"
    rm -f "$old_backup"
    DELETED_COUNT=$((DELETED_COUNT + 1))
done

if [ $DELETED_COUNT -gt 0 ]; then
    log_info "已删除 $DELETED_COUNT 个旧备份文件"
else
    log_info "没有需要清理的旧备份"
fi

# 统计备份文件数量和总大小
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "edu_crm_*.db" -type f | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

log_info "当前备份文件数量：$BACKUP_COUNT"
log_info "备份目录总大小：$TOTAL_SIZE"

# 备份完成
log "=========================================="
log_success "数据库备份任务完成"
log "=========================================="

# 如果是手动运行，显示最近的备份列表
if [ -t 1 ]; then
    echo ""
    echo -e "${BLUE}最近的5个备份文件：${NC}"
    find "$BACKUP_DIR" -name "edu_crm_*.db" -type f -printf "%T@ %p\n" | sort -rn | head -5 | while read timestamp filepath; do
        filename=$(basename "$filepath")
        filesize=$(du -h "$filepath" | cut -f1)
        filedate=$(date -r "$filepath" '+%Y-%m-%d %H:%M:%S')
        echo "  - $filename ($filesize) - $filedate"
    done
    echo ""
fi

exit 0

