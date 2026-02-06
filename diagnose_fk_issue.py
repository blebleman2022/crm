#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断脚本: 检查外键约束问题
创建时间: 2026-02-06
"""

import sqlite3
import os

DB_PATH = 'instance/edu_crm.db'

def main():
    print("=" * 60)
    print("🔍 外键约束问题诊断")
    print("=" * 60)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. 检查外键约束是否启用
        print("\n1️⃣ 检查外键约束状态:")
        cursor.execute("PRAGMA foreign_keys;")
        fk_status = cursor.fetchone()[0]
        if fk_status == 1:
            print("   ✅ 外键约束已启用")
        else:
            print("   ❌ 外键约束未启用 (这是问题所在!)")
            print("   💡 需要在应用启动时执行: PRAGMA foreign_keys=ON")
        
        # 2. 检查 customers 表的外键定义
        print("\n2️⃣ 检查 customers 表外键定义:")
        cursor.execute("PRAGMA foreign_key_list(customers);")
        fk_list = cursor.fetchall()
        for fk in fk_list:
            if 'teacher' in str(fk):
                print(f"   外键: {fk}")
        
        # 3. 检查所有 role='teacher' 的用户
        print("\n3️⃣ 检查 Users 表中的老师:")
        cursor.execute("SELECT id, username, role, status FROM users WHERE role='teacher' ORDER BY id;")
        teacher_users = cursor.fetchall()
        print(f"   共有 {len(teacher_users)} 个老师用户:")
        for user_id, username, role, status in teacher_users:
            status_text = "启用" if status else "禁用"
            print(f"   - ID: {user_id:2d}, 姓名: {username:10s}, 状态: {status_text}")
        
        # 4. 检查 Teachers 表记录
        print("\n4️⃣ 检查 Teachers 表记录:")
        cursor.execute("SELECT user_id FROM teachers ORDER BY user_id;")
        teacher_records = cursor.fetchall()
        teacher_ids = {row[0] for row in teacher_records}
        print(f"   共有 {len(teacher_records)} 条 Teachers 记录:")
        print(f"   user_id: {sorted(teacher_ids)}")
        
        # 5. 检查数据一致性
        print("\n5️⃣ 检查数据一致性:")
        user_ids = {row[0] for row in teacher_users}
        missing_in_teachers = user_ids - teacher_ids
        extra_in_teachers = teacher_ids - user_ids
        
        if missing_in_teachers:
            print(f"   ❌ 以下用户在 Users 表中但不在 Teachers 表中:")
            for uid in sorted(missing_in_teachers):
                cursor.execute("SELECT username FROM users WHERE id=?", (uid,))
                username = cursor.fetchone()[0]
                print(f"      - ID: {uid}, 姓名: {username}")
        else:
            print("   ✅ 所有老师用户都有对应的 Teachers 记录")
        
        if extra_in_teachers:
            print(f"   ⚠️  以下 Teachers 记录没有对应的用户:")
            for uid in sorted(extra_in_teachers):
                print(f"      - user_id: {uid}")
        
        # 6. 测试特定老师 (ID=19)
        print("\n6️⃣ 测试老师 ID=19:")
        cursor.execute("SELECT id, username FROM users WHERE id=19;")
        user = cursor.fetchone()
        if user:
            print(f"   ✅ Users 表: ID={user[0]}, 姓名={user[1]}")
        else:
            print("   ❌ Users 表中没有 ID=19 的记录")
        
        cursor.execute("SELECT user_id FROM teachers WHERE user_id=19;")
        teacher = cursor.fetchone()
        if teacher:
            print(f"   ✅ Teachers 表: user_id={teacher[0]}")
        else:
            print("   ❌ Teachers 表中没有 user_id=19 的记录")
        
        # 7. 检查 customers 表中的 teacher_id
        print("\n7️⃣ 检查 customers 表中的 teacher_id 值:")
        cursor.execute("SELECT DISTINCT teacher_id FROM customers WHERE teacher_id IS NOT NULL ORDER BY teacher_id;")
        customer_teacher_ids = cursor.fetchall()
        print(f"   当前已分配的 teacher_id: {[row[0] for row in customer_teacher_ids]}")
        
        # 检查是否有无效的 teacher_id
        invalid_ids = []
        for (tid,) in customer_teacher_ids:
            if tid not in teacher_ids:
                invalid_ids.append(tid)
        
        if invalid_ids:
            print(f"   ❌ 发现无效的 teacher_id (不在 Teachers 表中): {invalid_ids}")
            print("   💡 这些记录会导致外键约束错误!")
        else:
            print("   ✅ 所有 teacher_id 都有效")
        
        # 8. 模拟更新操作
        print("\n8️⃣ 模拟更新操作 (不实际执行):")
        print("   SQL: UPDATE customers SET teacher_id=19 WHERE customers.id = 9")
        
        # 启用外键约束后测试
        cursor.execute("PRAGMA foreign_keys=ON;")
        try:
            # 检查是否可以执行
            cursor.execute("SELECT id FROM customers WHERE id=9;")
            customer = cursor.fetchone()
            if customer:
                print("   ✅ 客户 ID=9 存在")
                # 不实际执行,只是测试
                print("   ℹ️  如果外键约束启用,此操作应该成功")
            else:
                print("   ⚠️  客户 ID=9 不存在")
        except Exception as e:
            print(f"   ❌ 模拟失败: {str(e)}")
        
        print("\n" + "=" * 60)
        print("📊 诊断总结:")
        print("=" * 60)
        
        if fk_status == 0:
            print("⚠️  主要问题: 外键约束未启用")
            print("   解决方案: 确保 run.py 中的外键配置生效,并重启应用")
        
        if missing_in_teachers:
            print(f"⚠️  数据问题: {len(missing_in_teachers)} 个用户缺少 Teachers 记录")
            print("   解决方案: 运行 fix_teacher_foreign_key.py")
        
        if invalid_ids:
            print(f"⚠️  数据问题: customers 表中有 {len(invalid_ids)} 个无效的 teacher_id")
            print("   解决方案: 需要清理或修复这些记录")
        
        if fk_status == 1 and not missing_in_teachers and not invalid_ids:
            print("✅ 所有检查通过! 外键约束应该正常工作")
        
    except Exception as e:
        print(f"\n❌ 诊断过程出错: {str(e)}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    main()

