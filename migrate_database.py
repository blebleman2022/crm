#!/usr/bin/env python3
"""
数据库迁移脚本
用途：安全地将 edu_crm.db 迁移到最新版本
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
    backup_path = os.path.join(backup_dir, f"edu_crm_backup_{timestamp}.db")

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
    """添加或更新 teachers 和 teacher_images 表"""
    cursor = conn.cursor()

    # 检查是否已存在
    if check_table_exists(conn, 'teachers'):
        # 检查表结构是否正确
        columns = get_table_columns(conn, 'teachers')

        # 如果是旧结构（缺少 created_by_user_id 字段），需要重建
        if 'created_by_user_id' not in columns:
            print_warning("检测到旧版 teachers 表结构（缺少 created_by_user_id），需要重建...")

            # 备份旧数据（如果有）
            cursor.execute("SELECT COUNT(*) FROM teachers")
            old_count = cursor.fetchone()[0]

            if old_count > 0:
                print_warning(f"发现 {old_count} 条旧数据，将被清除（旧表结构不兼容）")

            # 删除旧表
            cursor.execute("DROP TABLE IF EXISTS teacher_images")
            cursor.execute("DROP TABLE IF EXISTS teachers")
            print_success("已删除旧版 teachers 表")
        else:
            print_warning("teachers 表已存在且结构正确，跳过创建")
            return False

    print_warning("创建新版 teachers 表...")

    # 创建新版 teachers 表（与 models.py 中的 Teacher 模型一致）
    cursor.execute("""
        CREATE TABLE teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chinese_name VARCHAR(50) NOT NULL,
            english_name VARCHAR(100),
            current_institution VARCHAR(200),
            major_direction VARCHAR(200),
            highest_degree VARCHAR(50),
            degree_description TEXT,
            research_achievements TEXT,
            innovation_coaching_achievements TEXT,
            social_roles TEXT,
            status BOOLEAN DEFAULT 1,
            created_by_user_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by_user_id) REFERENCES users (id)
        )
    """)

    # 创建 teacher_images 表（与 models.py 中的 TeacherImage 模型一致）
    cursor.execute("""
        CREATE TABLE teacher_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            image_path VARCHAR(500) NOT NULL,
            description VARCHAR(200),
            file_size INTEGER,
            file_name VARCHAR(200),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES teachers (id) ON DELETE CASCADE
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_teacher_images_teacher_id ON teacher_images(teacher_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_teachers_created_by ON teachers(created_by_user_id)")

    conn.commit()
    print_success("teachers 和 teacher_images 表创建成功")
    return True

def migrate_add_teacher_id_to_customers(conn):
    """为 customers 表添加 teacher_id 字段"""
    cursor = conn.cursor()

    # 检查字段是否已存在
    columns = get_table_columns(conn, 'customers')

    if 'teacher_id' in columns:
        print_warning("customers 表已有 teacher_id 字段，跳过添加")
        return False

    print_warning("为 customers 表添加 teacher_id 字段...")

    try:
        cursor.execute("""
            ALTER TABLE customers
            ADD COLUMN teacher_id INTEGER
        """)

        conn.commit()
        print_success("成功为 customers 表添加 teacher_id 字段")
        return True
    except Exception as e:
        print_error(f"添加字段失败: {str(e)}")
        return False

def migrate_update_user_roles(conn):
    """更新用户角色：teacher -> teacher_supervisor"""
    cursor = conn.cursor()

    # 检查是否有旧角色
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='teacher'")
    old_count = cursor.fetchone()[0]

    if old_count == 0:
        print_warning("没有需要更新的用户角色")
        return False

    print_warning(f"发现 {old_count} 个用户使用旧角色 'teacher'，更新为 'teacher_supervisor'...")

    try:
        cursor.execute("""
            UPDATE users
            SET role = 'teacher_supervisor',
                updated_at = CURRENT_TIMESTAMP
            WHERE role = 'teacher'
        """)

        affected_rows = cursor.rowcount
        conn.commit()
        print_success(f"成功更新 {affected_rows} 个用户的角色")
        return True
    except Exception as e:
        print_error(f"更新角色失败: {str(e)}")
        return False

def migrate_add_system_config_table(conn):
    """添加 system_config 表"""
    cursor = conn.cursor()

    # 检查表是否已存在
    if check_table_exists(conn, 'system_config'):
        print_warning("system_config 表已存在，跳过创建")
        return False

    print_warning("创建 system_config 表...")

    try:
        cursor.execute("""
            CREATE TABLE system_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key VARCHAR(50) NOT NULL UNIQUE,
                config_value VARCHAR(200),
                description VARCHAR(200),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_by INTEGER,
                FOREIGN KEY (updated_by) REFERENCES users (id)
            )
        """)

        # 创建索引
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_system_config_key ON system_config(config_key)")

        conn.commit()
        print_success("system_config 表创建成功")
        return True
    except Exception as e:
        print_error(f"创建 system_config 表失败: {str(e)}")
        return False

def migrate_add_customer_payments_table(conn):
    """添加 customer_payments 表"""
    cursor = conn.cursor()

    # 检查表是否已存在
    if check_table_exists(conn, 'customer_payments'):
        # 检查表结构是否正确（是否有id字段）
        columns = get_table_columns(conn, 'customer_payments')
        if 'id' not in columns:
            print_warning("customer_payments 表结构不正确，需要重建...")
            # 备份数据
            cursor.execute("SELECT * FROM customer_payments")
            old_data = cursor.fetchall()

            # 删除旧表
            cursor.execute("DROP TABLE customer_payments")
            print_success("已删除旧版 customer_payments 表")
        else:
            print_warning("customer_payments 表已存在且结构正确，跳过创建")
            return False

    print_warning("创建 customer_payments 表...")

    try:
        cursor.execute("""
            CREATE TABLE customer_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL UNIQUE,
                teacher_user_id INTEGER NOT NULL,
                total_amount NUMERIC(10, 2),
                first_payment NUMERIC(10, 2),
                first_payment_date DATE,
                second_payment NUMERIC(10, 2),
                second_payment_date DATE,
                third_payment NUMERIC(10, 2),
                third_payment_date DATE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE,
                FOREIGN KEY (teacher_user_id) REFERENCES users (id)
            )
        """)

        # 创建索引
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_customer_payments_customer_id ON customer_payments(customer_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_payments_dates ON customer_payments(first_payment_date, second_payment_date, third_payment_date)")

        conn.commit()
        print_success("customer_payments 表创建成功")
        return True
    except Exception as e:
        print_error(f"创建 customer_payments 表失败: {str(e)}")
        return False

def migrate_add_thesis_name_to_customers(conn):
    """为 customers 表添加 thesis_name 字段"""
    cursor = conn.cursor()

    # 检查字段是否已存在
    columns = get_table_columns(conn, 'customers')

    if 'thesis_name' in columns:
        print_warning("customers 表已有 thesis_name 字段，跳过添加")
        return False

    print_warning("为 customers 表添加 thesis_name 字段...")

    try:
        cursor.execute("""
            ALTER TABLE customers
            ADD COLUMN thesis_name VARCHAR(200)
        """)

        conn.commit()
        print_success("成功为 customers 表添加 thesis_name 字段")
        return True
    except Exception as e:
        print_error(f"添加字段失败: {str(e)}")
        return False

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

def migrate_add_customer_image_tables(conn):
    """添加客户图片表"""
    cursor = conn.cursor()

    try:
        # 检查course_record_images表是否存在
        if check_table_exists(conn, 'course_record_images'):
            print_warning("course_record_images表已存在，跳过")
            table1_created = False
        else:
            # 创建课程记录图片表
            cursor.execute("""
                CREATE TABLE course_record_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    image_path VARCHAR(500) NOT NULL,
                    description VARCHAR(200),
                    file_size INTEGER,
                    file_name VARCHAR(200),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            """)
            print_success("成功创建course_record_images表")
            table1_created = True

        # 检查award_certificate_images表是否存在
        if check_table_exists(conn, 'award_certificate_images'):
            print_warning("award_certificate_images表已存在，跳过")
            table2_created = False
        else:
            # 创建获奖证书图片表
            cursor.execute("""
                CREATE TABLE award_certificate_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    image_path VARCHAR(500) NOT NULL,
                    description VARCHAR(200),
                    file_size INTEGER,
                    file_name VARCHAR(200),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            """)
            print_success("成功创建award_certificate_images表")
            table2_created = True

        conn.commit()
        return table1_created or table2_created

    except Exception as e:
        print_error(f"添加客户图片表失败: {e}")
        conn.rollback()
        return False

def get_table_stats(conn):
    """获取表统计信息"""
    cursor = conn.cursor()

    tables = [
        'users', 'leads', 'customers', 'payments',
        'teachers', 'tutoring_deliveries', 'competition_deliveries',
        'communication_records', 'login_logs', 'competition_names',
        'system_config', 'customer_payments', 'course_record_images', 'award_certificate_images'
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
    db_path = "instance/edu_crm.db"

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

    # 迁移1: 添加/更新 teachers 表
    if migrate_add_teachers_table(conn):
        migrations_applied.append("添加/更新 teachers 和 teacher_images 表")

    # 迁移2: 为 customers 表添加 teacher_id 字段
    if migrate_add_teacher_id_to_customers(conn):
        migrations_applied.append("为 customers 表添加 teacher_id 字段")

    # 迁移3: 更新用户角色
    if migrate_update_user_roles(conn):
        migrations_applied.append("更新用户角色 teacher -> teacher_supervisor")

    # 迁移4: 添加 system_config 表
    if migrate_add_system_config_table(conn):
        migrations_applied.append("添加 system_config 表")

    # 迁移5: 添加 customer_payments 表
    if migrate_add_customer_payments_table(conn):
        migrations_applied.append("添加 customer_payments 表")

    # 迁移6: 为 customers 表添加 thesis_name 字段
    if migrate_add_thesis_name_to_customers(conn):
        migrations_applied.append("为 customers 表添加 thesis_name 字段")

    # 迁移7: 添加客户图片表
    if migrate_add_customer_image_tables(conn):
        migrations_applied.append("添加 course_record_images 和 award_certificate_images 表")

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

