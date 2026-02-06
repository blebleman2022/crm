#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复脚本: 修正 customers.teacher_id 与 teacher_images.teacher_id 的外键引用
目标: 统一指向 teachers.user_id (而不是 teachers.id)

使用方法:
    python3 fix_teacher_fk_schema.py
"""

import os
import re
import shutil
import sqlite3
from datetime import datetime


def resolve_db_path():
    """从配置中解析 SQLite 数据库路径"""
    try:
        from config import Config
        uri = Config.SQLALCHEMY_DATABASE_URI
    except Exception:
        uri = os.environ.get("SQLALCHEMY_DATABASE_URI", "")

    if not uri.startswith("sqlite:///"):
        return None, uri

    path = uri.replace("sqlite:///", "", 1)
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    return path, uri


def backup_database(db_path):
    """备份数据库"""
    backup_dir = os.path.join(os.path.dirname(db_path), "..", "backups")
    backup_dir = os.path.abspath(backup_dir)
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"edu_crm_before_fk_schema_fix_{timestamp}.db")
    shutil.copy2(db_path, backup_path)
    return backup_path


def table_exists(cursor, table_name):
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;",
        (table_name,),
    )
    return cursor.fetchone() is not None


def get_fk_target(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA foreign_key_list({table_name});")
    for row in cursor.fetchall():
        # row: (id, seq, table, from, to, on_update, on_delete, match)
        if row[3] == column_name:
            return row[2], row[4]
    return None


def rebuild_table(cursor, table_name, replace_rules):
    """重建表并替换外键引用"""
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?;",
        (table_name,),
    )
    row = cursor.fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"无法读取 {table_name} 的建表语句")

    create_sql = row[0]
    new_sql = create_sql
    total_replaced = 0
    for pattern, replacement in replace_rules:
        new_sql, count = re.subn(pattern, replacement, new_sql, flags=re.IGNORECASE)
        total_replaced += count

    if total_replaced == 0:
        return False

    temp_table = f"{table_name}_new"
    new_sql = re.sub(
        rf'CREATE TABLE\s+["`]?{re.escape(table_name)}["`]?',
        f"CREATE TABLE {temp_table}",
        new_sql,
        count=1,
        flags=re.IGNORECASE,
    )

    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = [row[1] for row in cursor.fetchall()]
    column_list = ", ".join([f'"{col}"' for col in columns])

    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL;",
        (table_name,),
    )
    index_sql_list = [row[0] for row in cursor.fetchall()]

    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?;",
        (table_name,),
    )
    trigger_sql_list = [row[0] for row in cursor.fetchall() if row[0]]

    cursor.executescript(
        "PRAGMA foreign_keys=OFF;\n"
        "BEGIN;\n"
        f"{new_sql};\n"
        f"INSERT INTO {temp_table} ({column_list}) SELECT {column_list} FROM {table_name};\n"
        f"DROP TABLE {table_name};\n"
        f"ALTER TABLE {temp_table} RENAME TO {table_name};\n"
        + "\n".join([sql + ";" for sql in index_sql_list])
        + "\n"
        + "\n".join([sql + ";" for sql in trigger_sql_list])
        + "\nCOMMIT;\nPRAGMA foreign_keys=ON;\n"
    )
    return True


def main():
    print("=" * 60)
    print("🔧 外键结构修复: teachers.user_id")
    print("=" * 60)

    db_path, uri = resolve_db_path()
    if not db_path:
        print(f"❌ 非 SQLite 数据库或无法解析路径: {uri}")
        return 1

    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return 1

    print(f"📌 数据库路径: {db_path}")
    backup_path = backup_database(db_path)
    print(f"✅ 备份完成: {backup_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        replace_rules = [
            (r"REFERENCES\s+teachers\s*\(\s*id\s*\)", "REFERENCES teachers(user_id)")
        ]

        changed_any = False

        if table_exists(cursor, "customers"):
            fk_target = get_fk_target(cursor, "customers", "teacher_id")
            if fk_target == ("teachers", "user_id"):
                print("✅ customers.teacher_id 外键已正确指向 teachers.user_id")
            else:
                print(f"⚠️  customers.teacher_id 当前指向: {fk_target}")
                if rebuild_table(cursor, "customers", replace_rules):
                    print("✅ 已修复 customers 外键指向 teachers.user_id")
                    changed_any = True
                else:
                    print("⚠️  未检测到可替换的外键定义 (customers)")

        if table_exists(cursor, "teacher_images"):
            fk_target = get_fk_target(cursor, "teacher_images", "teacher_id")
            if fk_target == ("teachers", "user_id"):
                print("✅ teacher_images.teacher_id 外键已正确指向 teachers.user_id")
            else:
                print(f"⚠️  teacher_images.teacher_id 当前指向: {fk_target}")
                if rebuild_table(cursor, "teacher_images", replace_rules):
                    print("✅ 已修复 teacher_images 外键指向 teachers.user_id")
                    changed_any = True
                else:
                    print("⚠️  未检测到可替换的外键定义 (teacher_images)")

        if not changed_any:
            print("ℹ️  未发现需要修复的外键结构")

        return 0
    except Exception as exc:
        conn.rollback()
        print(f"❌ 修复失败: {exc}")
        print(f"💾 请使用备份恢复: {backup_path}")
        return 1
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
