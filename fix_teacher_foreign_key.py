#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复脚本: 解决班主任分配老师时的外键约束问题
创建时间: 2026-02-04
问题: 
1. SQLite 外键约束未启用
2. User 表中有 role='teacher' 的用户,但 Teachers 表中缺少对应记录

解决方案:
1. 在 Flask 应用中启用 SQLite 外键约束
2. 为所有 role='teacher' 的用户创建 Teachers 表记录

使用方法:
    python fix_teacher_foreign_key.py
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
    backup_path = os.path.join(BACKUP_DIR, f'edu_crm_before_fk_fix_{timestamp}.db')
    
    print(f"📦 正在备份数据库...")
    shutil.copy2(DB_PATH, backup_path)
    print(f"✅ 数据库已备份到: {backup_path}")
    return backup_path

def check_missing_teachers(cursor):
    """检查缺少 Teachers 记录的用户"""
    print("\n🔍 检查数据一致性...")
    
    # 查找所有 role='teacher' 的用户
    cursor.execute("SELECT id, username, phone FROM users WHERE role='teacher'")
    teacher_users = cursor.fetchall()
    
    # 查找 Teachers 表中的所有 user_id
    cursor.execute("SELECT user_id FROM teachers")
    teacher_records = {row[0] for row in cursor.fetchall()}
    
    # 找出缺失的记录
    missing = []
    for user_id, username, phone in teacher_users:
        if user_id not in teacher_records:
            missing.append((user_id, username, phone))
    
    if missing:
        print(f"\n⚠️  发现 {len(missing)} 个用户缺少 Teachers 表记录:")
        for user_id, username, phone in missing:
            print(f"   - User ID: {user_id}, 姓名: {username}, 手机: {phone}")
    else:
        print("✅ 所有 role='teacher' 的用户都有对应的 Teachers 记录")
    
    return missing

def create_missing_teacher_records(cursor, missing_users):
    """为缺失的用户创建 Teachers 表记录"""
    if not missing_users:
        return 0
    
    print(f"\n📝 正在为 {len(missing_users)} 个用户创建 Teachers 记录...")
    
    created_count = 0
    for user_id, username, phone in missing_users:
        try:
            cursor.execute('''
                INSERT INTO teachers (user_id, email, subject, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (user_id, f'{phone}@temp.com', '待完善', True))
            print(f"✅ 已为用户 {username} (ID: {user_id}) 创建 Teachers 记录")
            created_count += 1
        except Exception as e:
            print(f"❌ 创建失败 - 用户 {username} (ID: {user_id}): {str(e)}")
    
    return created_count

def enable_foreign_keys_in_app():
    """在 run.py 中添加启用外键约束的代码"""
    print("\n📝 正在修改 run.py 以启用外键约束...")
    
    run_py_path = 'run.py'
    
    # 读取文件
    with open(run_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经添加了外键约束代码
    if 'PRAGMA foreign_keys' in content or '@event.listens_for' in content:
        print("⏭️  run.py 中已包含外键约束配置,跳过修改")
        return False
    
    # 在 db.init_app(app) 之后添加外键约束监听器
    insert_code = '''
    # 启用 SQLite 外键约束
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """在每次连接时启用外键约束"""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
'''
    
    # 找到 db.init_app(app) 的位置
    target = 'db.init_app(app)'
    if target in content:
        # 在 db.init_app(app) 之后插入代码
        content = content.replace(target, target + insert_code)
        
        # 写回文件
        with open(run_py_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 已在 run.py 中添加外键约束配置")
        return True
    else:
        print("⚠️  未找到 db.init_app(app),请手动添加外键约束配置")
        return False

def verify_fix(cursor):
    """验证修复结果"""
    print("\n🔍 正在验证修复结果...")
    
    # 检查数据一致性
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='teacher'")
    user_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM teachers")
    teacher_count = cursor.fetchone()[0]
    
    print(f"✅ User 表中 role='teacher' 的用户数: {user_count}")
    print(f"✅ Teachers 表中的记录数: {teacher_count}")
    
    if user_count == teacher_count:
        print("✅ 数据一致性检查通过!")
        return True
    else:
        print(f"⚠️  数据不一致: User表有{user_count}个老师,Teachers表有{teacher_count}条记录")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 开始修复: 班主任分配老师外键约束问题")
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
        # 1. 检查缺失的 Teachers 记录
        missing_users = check_missing_teachers(cursor)
        
        # 2. 创建缺失的记录
        created_count = create_missing_teacher_records(cursor, missing_users)
        
        # 提交事务
        conn.commit()
        print(f"\n✅ 数据库修复完成,创建了 {created_count} 条 Teachers 记录")
        
        # 3. 验证修复
        if verify_fix(cursor):
            print("\n" + "=" * 60)
            print("🎉 数据库修复成功!")
            print("=" * 60)
        
        # 4. 修改 run.py 启用外键约束
        enable_foreign_keys_in_app()
        
        print("\n📋 后续步骤:")
        print("1. ✅ 数据库已修复")
        print("2. ⚠️  需要重启 Flask 应用以启用外键约束")
        print("3. ⚠️  重启后测试班主任分配老师功能")
        print(f"\n💾 备份文件: {backup_path}")
        
        return True
            
    except Exception as e:
        print(f"\n❌ 修复过程中发生错误: {str(e)}")
        conn.rollback()
        print(f"⚠️  数据库已回滚,可以从备份恢复: {backup_path}")
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)

