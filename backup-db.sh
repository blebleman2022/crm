#!/bin/bash

# ========================================
# 数据库自动备份脚本
# ========================================
# 功能：每天凌晨3点自动备份 CRM 数据库
# 备份路径：/bak/edu_crm_YYYYMMDD.db
# 保留策略：最多保留3天的备份
# ========================================

# 配置变量
SOURCE_DB="/crm/instance/edu_crm.db"
BACKUP_DIR="/bak"
DATE_SUFFIX=$(date +%Y%m%d)
BACKUP_FILE="${BACKUP_DIR}/edu_crm_${DATE_SUFFIX}.db"
LOG_FILE="${BACKUP_DIR}/backup.log"
KEEP_DAYS=3

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 开始备份
log "========== 开始数据库备份 =========="

# 检查源数据库文件是否存在
if [ ! -f "$SOURCE_DB" ]; then
    log "错误：源数据库文件不存在: $SOURCE_DB"
    exit 1
fi

# 创建备份目录（如果不存在）
if [ ! -d "$BACKUP_DIR" ]; then
    log "创建备份目录: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    if [ $? -ne 0 ]; then
        log "错误：无法创建备份目录"
        exit 1
    fi
fi

# 检查今天的备份是否已存在
if [ -f "$BACKUP_FILE" ]; then
    log "警告：今天的备份已存在，将覆盖: $BACKUP_FILE"
fi

# 执行备份（使用 cp 保留权限和时间戳）
log "正在备份: $SOURCE_DB -> $BACKUP_FILE"
cp -p "$SOURCE_DB" "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    # 获取备份文件大小
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "备份成功！文件大小: $BACKUP_SIZE"
else
    log "错误：备份失败"
    exit 1
fi

# 清理旧备份（保留最近3天）
log "开始清理旧备份（保留最近 ${KEEP_DAYS} 天）..."

# 查找并删除3天前的备份文件
DELETED_COUNT=0
find "$BACKUP_DIR" -name "edu_crm_*.db" -type f -mtime +$((KEEP_DAYS - 1)) | while read old_backup; do
    log "删除旧备份: $old_backup"
    rm -f "$old_backup"
    if [ $? -eq 0 ]; then
        DELETED_COUNT=$((DELETED_COUNT + 1))
    else
        log "警告：删除失败: $old_backup"
    fi
done

# 列出当前所有备份文件
log "当前备份文件列表:"
ls -lh "$BACKUP_DIR"/edu_crm_*.db 2>/dev/null | while read line; do
    log "  $line"
done

BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/edu_crm_*.db 2>/dev/null | wc -l)
log "当前共有 ${BACKUP_COUNT} 个备份文件"

log "========== 备份完成 =========="
log ""

exit 0

