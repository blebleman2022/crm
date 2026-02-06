#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除重复学员中“支付金额较低”的那条记录。

默认逻辑：
1) 以 leads.student_name 精确匹配
2) 计算每个 lead 的已付款总额 (payments 表求和)
3) 删除付款总额较低的 lead 及其关联数据

用法:
    python3 remove_duplicate_student_by_payment.py --name "张三"
    python3 remove_duplicate_student_by_payment.py --name "张三" --yes
"""

import argparse
import os
import shutil
import sqlite3
from datetime import datetime


def resolve_db_path():
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
    backup_dir = os.path.abspath(os.path.join(os.path.dirname(db_path), "..", "backups"))
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"edu_crm_before_remove_dup_{ts}.db")
    shutil.copy2(db_path, backup_path)
    return backup_path


def get_fk_refs(cursor, target_table):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]
    refs = []
    for table in tables:
        if table == target_table:
            continue
        cursor.execute(f"PRAGMA foreign_key_list({table});")
        for fk in cursor.fetchall():
            # fk: (id, seq, table, from, to, on_update, on_delete, match)
            if fk[2] == target_table:
                refs.append((table, fk[3]))
    return refs


def fetch_candidates(cursor, student_name):
    cursor.execute(
        """
        SELECT
            l.id AS lead_id,
            l.student_name,
            c.id AS customer_id,
            c.payment_amount,
            COALESCE((SELECT SUM(p.amount) FROM payments p WHERE p.lead_id = l.id), 0) AS paid_sum
        FROM leads l
        LEFT JOIN customers c ON c.lead_id = l.id
        WHERE l.student_name = ?
        ORDER BY l.id;
        """,
        (student_name,),
    )
    return cursor.fetchall()


def delete_by_fk(cursor, refs, target_id):
    total = 0
    for table, column in refs:
        cursor.execute(f"DELETE FROM {table} WHERE {column} = ?;", (target_id,))
        total += cursor.rowcount
    return total


def main():
    parser = argparse.ArgumentParser(description="删除重复学员中支付金额较低的记录")
    parser.add_argument("--name", required=True, help="学员姓名（精确匹配）")
    parser.add_argument("--yes", action="store_true", help="跳过确认，直接删除")
    args = parser.parse_args()

    db_path, uri = resolve_db_path()
    if not db_path:
        print(f"❌ 非 SQLite 数据库或无法解析路径: {uri}")
        return 1
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        candidates = fetch_candidates(cursor, args.name)
        if len(candidates) != 2:
            print(f"❌ 找到 {len(candidates)} 条记录，期望 2 条。请确认姓名或手动处理。")
            for row in candidates:
                print(f"   lead_id={row[0]}, customer_id={row[2]}, paid_sum={row[4]}")
            return 1

        first, second = candidates
        # 以 payments 汇总为主要比较依据
        if first[4] == second[4]:
            print("⚠️ 两条记录支付金额相同，脚本不会自动删除。请人工确认。")
            print(f"   A: lead_id={first[0]}, customer_id={first[2]}, paid_sum={first[4]}")
            print(f"   B: lead_id={second[0]}, customer_id={second[2]}, paid_sum={second[4]}")
            return 1

        delete_target = first if first[4] < second[4] else second
        keep_target = second if delete_target is first else first

        print("🧾 待删除记录:")
        print(f"   lead_id={delete_target[0]}, customer_id={delete_target[2]}, paid_sum={delete_target[4]}")
        print("✅ 保留记录:")
        print(f"   lead_id={keep_target[0]}, customer_id={keep_target[2]}, paid_sum={keep_target[4]}")

        if not args.yes:
            confirm = input("输入 DELETE 确认删除: ").strip()
            if confirm != "DELETE":
                print("❌ 已取消")
                return 1

        backup_path = backup_database(db_path)
        print(f"💾 已备份数据库: {backup_path}")

        conn.execute("PRAGMA foreign_keys=ON;")

        # 删除依赖表记录（按外键引用自动发现）
        lead_refs = get_fk_refs(cursor, "leads")
        customer_refs = get_fk_refs(cursor, "customers")

        deleted_rows = 0

        # 先删 customer 相关
        if delete_target[2]:
            deleted_rows += delete_by_fk(cursor, customer_refs, delete_target[2])
            cursor.execute("DELETE FROM customers WHERE id = ?;", (delete_target[2],))
            deleted_rows += cursor.rowcount

        # 再删 lead 相关
        deleted_rows += delete_by_fk(cursor, lead_refs, delete_target[0])
        cursor.execute("DELETE FROM leads WHERE id = ?;", (delete_target[0],))
        deleted_rows += cursor.rowcount

        conn.commit()
        print(f"✅ 删除完成，共删除 {deleted_rows} 条关联记录。")
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"❌ 删除失败: {exc}")
        return 1
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
