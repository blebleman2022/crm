#!/usr/bin/env python3
"""
数据库迁移脚本
用途：安全地将 edu_crm_1022.db 迁移到最新版本
支持：添加新表、修改表结构、数据迁移
"""

import sqlite3
import os
import shutil
from datetime import datetime

# 颜色输出
class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.NC}")

def print_warning(msg):
    print(f"{Colors.YELLOW}! {msg}{Colors.NC}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.NC}")

def backup_database(db_path):
    """备份数据库"""
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"edu_crm_1022_backup_{timestamp}.db")
    
    shutil.copy2(db_path, backup_path)
    print_success(f"数据库已备份到: {backup_path}")
    return backup_path

def check_table_exists(conn, table_name):
    """检查表是否存在"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone()[0] > 0

def get_table_columns(conn, table_name):
    """获取表的列信息"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1]: row[2] for row in cursor.fetchall()}

def migrate_add_teachers_table(conn):
    """添加 teachers 和 teacher_images 表"""
    cursor = conn.cursor()
    
    # 检查是否已存在
    if check_table_exists(conn, 'teachers'):
        print_warning("teachers 表已存在，跳过创建")
        return False
    
    print_warning("创建 teachers 表...")
    
    # 创建 teachers 表
    cursor.execute("""
        CREATE TABLE teachers (
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
        )
    """)
    
    # 创建 teacher_images 表
    cursor.execute("""
        CREATE TABLE teacher_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            image_path VARCHAR(500) NOT NULL,
            image_type VARCHAR(50),
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES teachers (id) ON DELETE CASCADE
        )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX idx_teachers_phone ON teachers(phone)")
    cursor.execute("CREATE INDEX idx_teachers_status ON teachers(status)")
    cursor.execute("CREATE INDEX idx_teacher_images_teacher_id ON teacher_images(teacher_id)")
    
    conn.commit()
    print_success("teachers 和 teacher_images 表创建成功")
    return True

def verify_database_integrity(conn):
    """验证数据库完整性"""
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check")
    result = cursor.fetchone()[0]
    
    if result == "ok":
        print_success("数据库完整性检查通过")
        return True
    else:
        print_error(f"数据库完整性检查失败: {result}")
        return False

def get_table_stats(conn):
    """获取表统计信息"""
    cursor = conn.cursor()
    
    tables = [
        'users', 'leads', 'customers', 'payments', 
        'teachers', 'tutoring_deliveries', 'competition_deliveries',
        'communication_records', 'login_logs', 'competition_names'
    ]
    
    stats = {}
    for table in tables:
        if check_table_exists(conn, table):
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            stats[table] = count
    
    return stats

def main():
    """主函数"""
    print(f"{Colors.GREEN}{'='*50}{Colors.NC}")
    print(f"{Colors.GREEN}EduConnect CRM 数据库迁移工具{Colors.NC}")
    print(f"{Colors.GREEN}{'='*50}{Colors.NC}\n")
    
    # 数据库路径
    db_path = "instance/edu_crm_1022.db"
    
    # 检查数据库文件是否存在
    if not os.path.exists(db_path):
        print_error(f"数据库文件不存在: {db_path}")
        return 1
    
    # 1. 备份数据库
    print(f"\n{Colors.YELLOW}步骤 1/5: 备份数据库...{Colors.NC}")
    backup_path = backup_database(db_path)
    
    # 2. 连接数据库
    print(f"\n{Colors.YELLOW}步骤 2/5: 连接数据库...{Colors.NC}")
    conn = sqlite3.connect(db_path)
    print_success(f"已连接到: {db_path}")
    
    # 3. 执行迁移
    print(f"\n{Colors.YELLOW}步骤 3/5: 执行数据库迁移...{Colors.NC}")
    
    migrations_applied = []
    
    # 迁移1: 添加 teachers 表
    if migrate_add_teachers_table(conn):
        migrations_applied.append("添加 teachers 和 teacher_images 表")
    
    if migrations_applied:
        print_success(f"应用了 {len(migrations_applied)} 个迁移")
        for migration in migrations_applied:
            print(f"  - {migration}")
    else:
        print_warning("没有需要应用的迁移")
    
    # 4. 验证数据库
    print(f"\n{Colors.YELLOW}步骤 4/5: 验证数据库完整性...{Colors.NC}")
    if not verify_database_integrity(conn):
        print_error("数据库验证失败，正在恢复备份...")
        conn.close()
        shutil.copy2(backup_path, db_path)
        print_success(f"已从备份恢复: {backup_path}")
        return 1
    
    # 5. 显示统计信息
    print(f"\n{Colors.YELLOW}步骤 5/5: 数据库统计信息...{Colors.NC}")
    stats = get_table_stats(conn)
    
    print("\n表名                     记录数")
    print("-" * 40)
    for table, count in stats.items():
        print(f"{table:<25} {count:>10}")
    
    conn.close()
    
    # 完成
    print(f"\n{Colors.GREEN}{'='*50}{Colors.NC}")
    print(f"{Colors.GREEN}迁移完成！{Colors.NC}")
    print(f"{Colors.GREEN}{'='*50}{Colors.NC}\n")
    print(f"数据库文件: {Colors.GREEN}{db_path}{Colors.NC}")
    print(f"备份文件: {Colors.GREEN}{backup_path}{Colors.NC}")
    print(f"\n{Colors.YELLOW}提示：如果需要回滚，请运行：{Colors.NC}")
    print(f"  cp {backup_path} {db_path}\n")
    
    return 0

if __name__ == "__main__":
    exit(main())

