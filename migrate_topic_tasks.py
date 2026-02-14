#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本: 课题任务管理功能
创建时间: 2026-02-04
功能: 
1. 创建 topic_tasks 表(课题任务)
2. 创建 topic_submissions 表(课题提交)
3. 为 leads 表添加头脑风暴相关字段

使用方法:
    python migrate_topic_tasks.py

注意: 
- 执行前会自动备份数据库
- 如果表已存在会跳过创建
"""

import sqlite3
import os
import shutil
from datetime import datetime

# 数据库路径
DB_PATH = 'instance/edu_crm.db'
BACKUP_DIR = 'backups'

def backup_database():
    """备份数据库"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'edu_crm_before_topic_tasks_{timestamp}.db')
    
    print(f"📦 正在备份数据库...")
    shutil.copy2(DB_PATH, backup_path)
    print(f"✅ 数据库已备份到: {backup_path}")
    return backup_path

def table_exists(cursor, table_name):
    """检查表是否存在"""
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone() is not None

def column_exists(cursor, table_name, column_name):
    """检查列是否存在"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def create_topic_tasks_table(cursor):
    """创建 topic_tasks 表"""
    if table_exists(cursor, 'topic_tasks'):
        print("⏭️  topic_tasks 表已存在,跳过创建")
        return False
    
    print("📝 正在创建 topic_tasks 表...")
    cursor.execute('''
        CREATE TABLE topic_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            teacher_user_id INTEGER NOT NULL,
            due_at DATETIME NOT NULL,
            status VARCHAR(20) DEFAULT '待提交',
            created_by INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(lead_id) REFERENCES leads(id),
            FOREIGN KEY(teacher_user_id) REFERENCES users(id),
            FOREIGN KEY(created_by) REFERENCES users(id)
        )
    ''')
    print("✅ topic_tasks 表创建成功")
    return True

def create_topic_submissions_table(cursor):
    """创建 topic_submissions 表"""
    if table_exists(cursor, 'topic_submissions'):
        print("⏭️  topic_submissions 表已存在,跳过创建")
        return False
    
    print("📝 正在创建 topic_submissions 表...")
    cursor.execute('''
        CREATE TABLE topic_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(task_id) REFERENCES topic_tasks(id)
        )
    ''')
    print("✅ topic_submissions 表创建成功")
    return True

def add_brainstorm_fields(cursor):
    """为 leads 表添加头脑风暴相关字段"""
    fields_to_add = [
        ('deposit_paid_at', 'DATETIME', '定金支付时间(兼容字段)'),
        ('full_payment_at', 'DATETIME', '尾款支付时间(兼容字段)'),
        ('brainstorm_conclusion', 'TEXT', '头脑风暴结论'),
        ('brainstorm_topics', 'TEXT', '课题选项内容'),
        ('brainstorm_conclusion_at', 'DATETIME', '头脑风暴结论保存时间'),
        ('brainstorm_topics_at', 'DATETIME', '课题选项保存时间')
    ]
    
    added_count = 0
    for field_name, field_type, comment in fields_to_add:
        if column_exists(cursor, 'leads', field_name):
            print(f"⏭️  leads.{field_name} 字段已存在,跳过添加")
        else:
            print(f"📝 正在添加 leads.{field_name} 字段...")
            cursor.execute(f'ALTER TABLE leads ADD COLUMN {field_name} {field_type}')
            print(f"✅ leads.{field_name} 字段添加成功 - {comment}")
            added_count += 1
    
    return added_count

def verify_migration(cursor):
    """验证迁移结果"""
    print("\n🔍 正在验证迁移结果...")
    
    # 检查表
    tables = ['topic_tasks', 'topic_submissions']
    for table in tables:
        if table_exists(cursor, table):
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✅ {table} 表存在, 当前记录数: {count}")
        else:
            print(f"❌ {table} 表不存在!")
            return False
    
    # 检查字段
    fields = ['brainstorm_conclusion', 'brainstorm_topics', 'brainstorm_conclusion_at',
              'brainstorm_topics_at', 'deposit_paid_at', 'full_payment_at']
    for field in fields:
        if column_exists(cursor, 'leads', field):
            print(f"✅ leads.{field} 字段存在")
        else:
            print(f"❌ leads.{field} 字段不存在!")
            return False

    return True

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 开始执行数据库迁移: 课题任务管理功能")
    print("=" * 60)

    # 检查数据库文件是否存在
    if not os.path.exists(DB_PATH):
        print(f"❌ 错误: 数据库文件不存在: {DB_PATH}")
        return False

    # 备份数据库
    backup_path = backup_database()

    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 执行迁移
        print("\n" + "=" * 60)
        print("📋 开始执行迁移步骤")
        print("=" * 60)

        # 1. 创建 topic_tasks 表
        create_topic_tasks_table(cursor)

        # 2. 创建 topic_submissions 表
        create_topic_submissions_table(cursor)

        # 3. 添加头脑风暴字段
        added_fields = add_brainstorm_fields(cursor)

        # 提交事务
        conn.commit()
        print("\n✅ 所有变更已提交到数据库")

        # 验证迁移
        if verify_migration(cursor):
            print("\n" + "=" * 60)
            print("🎉 数据库迁移成功完成!")
            print("=" * 60)
            print(f"\n📊 迁移统计:")
            print(f"  - 创建表: topic_tasks, topic_submissions")
            print(f"  - 新增字段: {added_fields} 个")
            print(f"  - 备份文件: {backup_path}")
            print("\n✅ 可以安全地重启应用服务")
            return True
        else:
            print("\n❌ 迁移验证失败,请检查错误信息")
            return False

    except Exception as e:
        print(f"\n❌ 迁移过程中发生错误: {str(e)}")
        conn.rollback()
        print(f"⚠️  数据库已回滚,可以从备份恢复: {backup_path}")
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)

