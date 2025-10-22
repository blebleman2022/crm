"""
将旧的teacher角色迁移为teacher_supervisor角色
- 所有User表中role='teacher'的用户改为role='teacher_supervisor'
- 更新相关注释和约束
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, User
from sqlalchemy import text

def migrate():
    print("=" * 60)
    print("开始迁移teacher角色到teacher_supervisor...")
    print("=" * 60)
    
    # 1. 检查当前有多少teacher角色用户
    teacher_users = User.query.filter_by(role='teacher').all()
    teacher_count = len(teacher_users)
    print(f"\n📊 发现 {teacher_count} 个teacher角色用户：")
    for user in teacher_users:
        print(f"   - ID: {user.id}, 用户名: {user.username}, 手机: {user.phone}")
    
    if teacher_count > 0:
        # 2. 更新所有teacher角色为teacher_supervisor
        print(f"\n🔄 正在将 {teacher_count} 个用户从teacher角色更新为teacher_supervisor角色...")
        result = db.session.execute(
            text("UPDATE users SET role = 'teacher_supervisor' WHERE role = 'teacher'")
        )
        db.session.commit()
        print(f"✅ 已成功更新 {result.rowcount} 个用户")
    else:
        print("\n⚠️  没有找到需要迁移的teacher角色用户")
    
    # 3. 更新User表的role字段注释
    print("\n🔄 正在更新users表role字段注释...")
    try:
        db.session.execute(text("""
            ALTER TABLE users 
            MODIFY COLUMN role VARCHAR(20) NOT NULL 
            COMMENT '角色：admin/sales_manager/salesperson/teacher_supervisor/teacher'
        """))
        db.session.commit()
        print("✅ 已更新users表role字段注释")
    except Exception as e:
        print(f"⚠️  更新字段注释失败（可忽略）: {e}")
        db.session.rollback()
    
    # 4. 更新Customer表的teacher_user_id字段注释
    print("\n🔄 正在更新customers表teacher_user_id字段注释...")
    try:
        db.session.execute(text("""
            ALTER TABLE customers 
            MODIFY COLUMN teacher_user_id INT 
            COMMENT '责任班主任ID（User表，role=teacher_supervisor）'
        """))
        db.session.commit()
        print("✅ 已更新customers表teacher_user_id字段注释")
    except Exception as e:
        print(f"⚠️  更新字段注释失败（可忽略）: {e}")
        db.session.rollback()
    
    # 5. 验证迁移结果
    print("\n" + "=" * 60)
    print("迁移结果验证：")
    print("=" * 60)
    
    supervisor_users = User.query.filter_by(role='teacher_supervisor').all()
    supervisor_count = len(supervisor_users)
    remaining_teacher_count = User.query.filter_by(role='teacher').count()
    
    print(f"\n📊 teacher_supervisor角色用户数: {supervisor_count}")
    for user in supervisor_users:
        print(f"   - ID: {user.id}, 用户名: {user.username}, 手机: {user.phone}")
    
    print(f"\n📊 teacher角色用户数: {remaining_teacher_count}")
    
    if remaining_teacher_count == 0 and supervisor_count == teacher_count:
        print("\n" + "=" * 60)
        print("✅ 迁移成功！所有teacher角色用户已更新为teacher_supervisor")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("⚠️  迁移可能存在问题，请检查")
        print("=" * 60)
    
    return True

if __name__ == '__main__':
    from run import app
    with app.app_context():
        migrate()

