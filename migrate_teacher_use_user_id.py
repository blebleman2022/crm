#!/usr/bin/env python3
"""
数据迁移脚本: 删除 Teacher.id, 使用 user_id 作为主键

目的: 解决 User.id 和 Teacher.id 混淆使用的问题
方案: 让 Teacher 表使用 user_id 作为主键,删除独立的 id 字段

影响范围:
1. teachers 表结构
2. customers.teacher_id 外键
3. teacher_images.teacher_id 外键
4. delivery_documents.uploaded_by_id (当 uploaded_by_type='teacher' 时)
"""

import sqlite3
import os
from datetime import datetime

def backup_database():
    """备份数据库"""
    db_path = 'instance/edu_crm.db'
    backup_path = f'instance/edu_crm_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    
    if os.path.exists(db_path):
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ 数据库已备份到: {backup_path}")
        return backup_path
    else:
        print(f"❌ 数据库文件不存在: {db_path}")
        return None

def migrate():
    """执行迁移"""
    db_path = 'instance/edu_crm.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    # 先备份
    backup_path = backup_database()
    if not backup_path:
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("\n开始迁移...")
        
        # ========== 步骤1: 更新 customers.teacher_id ==========
        print("\n[1/5] 更新 customers.teacher_id (Teacher.id → User.id)...")
        
        cursor.execute("""
            UPDATE customers 
            SET teacher_id = (
                SELECT user_id FROM teachers WHERE teachers.id = customers.teacher_id
            )
            WHERE teacher_id IS NOT NULL
        """)
        affected = cursor.rowcount
        print(f"   ✅ 更新了 {affected} 条客户记录")
        
        # ========== 步骤2: 更新 teacher_images.teacher_id ==========
        print("\n[2/5] 更新 teacher_images.teacher_id (Teacher.id → User.id)...")
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='teacher_images'")
        if cursor.fetchone():
            cursor.execute("""
                UPDATE teacher_images 
                SET teacher_id = (
                    SELECT user_id FROM teachers WHERE teachers.id = teacher_images.teacher_id
                )
            """)
            affected = cursor.rowcount
            print(f"   ✅ 更新了 {affected} 条老师图片记录")
        else:
            print("   ⚠️  teacher_images 表不存在,跳过")
        
        # ========== 步骤3: 更新 delivery_documents.uploaded_by_id ==========
        print("\n[3/5] 更新 delivery_documents.uploaded_by_id (当 uploaded_by_type='teacher' 时)...")
        
        cursor.execute("""
            UPDATE delivery_documents 
            SET uploaded_by_id = (
                SELECT user_id FROM teachers WHERE teachers.id = delivery_documents.uploaded_by_id
            )
            WHERE uploaded_by_type = 'teacher' AND uploaded_by_id IS NOT NULL
        """)
        affected = cursor.rowcount
        print(f"   ✅ 更新了 {affected} 条文档记录")
        
        # ========== 步骤4: 重建 teachers 表 ==========
        print("\n[4/5] 重建 teachers 表 (user_id 作为主键)...")
        
        # 4.1 重命名旧表
        cursor.execute("ALTER TABLE teachers RENAME TO teachers_old")
        print("   ✅ 旧表已重命名为 teachers_old")
        
        # 4.2 创建新表
        cursor.execute("""
            CREATE TABLE teachers (
                user_id INTEGER PRIMARY KEY,
                current_institution VARCHAR(200),
                major_direction VARCHAR(200),
                highest_degree VARCHAR(50),
                degree_description TEXT,
                research_achievements TEXT,
                innovation_coaching_achievements TEXT,
                social_roles TEXT,
                email VARCHAR(100),
                subject VARCHAR(50),
                status BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        print("   ✅ 新表已创建 (user_id 作为主键)")
        
        # 4.3 迁移数据
        cursor.execute("""
            INSERT INTO teachers 
            (user_id, current_institution,
             major_direction, highest_degree, degree_description,
             research_achievements, innovation_coaching_achievements,
             social_roles, email, subject, status, created_at, updated_at)
            SELECT user_id, current_institution,
                   major_direction, highest_degree, degree_description,
                   research_achievements, innovation_coaching_achievements,
                   social_roles, email, subject, status, created_at, updated_at
            FROM teachers_old
        """)
        affected = cursor.rowcount
        print(f"   ✅ 迁移了 {affected} 条老师记录")
        
        # 4.4 删除旧表
        cursor.execute("DROP TABLE teachers_old")
        print("   ✅ 旧表已删除")
        
        # ========== 步骤5: 验证数据 ==========
        print("\n[5/5] 验证数据完整性...")
        
        # 验证 teachers 表
        cursor.execute("SELECT COUNT(*) FROM teachers")
        teacher_count = cursor.fetchone()[0]
        print(f"   ✅ teachers 表: {teacher_count} 条记录")
        
        # 验证 customers 表
        cursor.execute("SELECT COUNT(*) FROM customers WHERE teacher_id IS NOT NULL")
        customer_count = cursor.fetchone()[0]
        print(f"   ✅ customers 表: {customer_count} 条记录有辅导老师")
        
        # 验证外键完整性
        cursor.execute("""
            SELECT COUNT(*) FROM customers 
            WHERE teacher_id IS NOT NULL 
            AND teacher_id NOT IN (SELECT user_id FROM teachers)
        """)
        orphan_count = cursor.fetchone()[0]
        if orphan_count > 0:
            print(f"   ⚠️  警告: 发现 {orphan_count} 条客户记录的 teacher_id 无效")
        else:
            print(f"   ✅ 外键完整性检查通过")
        
        # 提交事务
        conn.commit()
        print("\n" + "="*60)
        print("✅ 迁移成功完成!")
        print("="*60)
        print(f"\n备份文件: {backup_path}")
        print("\n下一步: 请修改代码中所有使用 teacher.id 的地方")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ 迁移失败: {e}")
        print(f"\n数据库已回滚,备份文件: {backup_path}")
        return False
        
    finally:
        conn.close()

if __name__ == '__main__':
    import sys

    print("="*60)
    print("Teacher 表迁移脚本")
    print("删除 Teacher.id, 使用 user_id 作为主键")
    print("="*60)

    # 检查是否有 --auto-confirm 参数
    auto_confirm = '--auto-confirm' in sys.argv

    if auto_confirm:
        print("\n⚠️  自动确认模式,开始迁移...")
        confirm = 'yes'
    else:
        confirm = input("\n⚠️  此操作将修改数据库结构,是否继续? (yes/no): ")

    if confirm.lower() == 'yes':
        success = migrate()
        if success:
            print("\n✅ 迁移完成!")
        else:
            print("\n❌ 迁移失败!")
    else:
        print("\n已取消迁移")
