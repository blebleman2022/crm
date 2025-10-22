"""
验证角色迁移结果
"""

from run import app
from models import db, User, Customer

with app.app_context():
    print("=" * 60)
    print("验证角色迁移结果")
    print("=" * 60)
    
    # 1. 检查所有用户的角色
    print("\n📊 所有用户角色统计：")
    users = User.query.all()
    role_count = {}
    for user in users:
        role_count[user.role] = role_count.get(user.role, 0) + 1
        print(f"   - ID: {user.id}, 用户名: {user.username}, 手机: {user.phone}, 角色: {user.role}")
    
    print("\n📊 角色统计：")
    for role, count in role_count.items():
        print(f"   - {role}: {count}个用户")
    
    # 2. 检查是否还有旧的teacher角色
    old_teachers = User.query.filter_by(role='teacher').all()
    if old_teachers:
        print(f"\n⚠️  警告：还有 {len(old_teachers)} 个用户使用旧的teacher角色")
        for user in old_teachers:
            print(f"   - ID: {user.id}, 用户名: {user.username}")
    else:
        print("\n✅ 没有用户使用旧的teacher角色")
    
    # 3. 检查新的teacher_supervisor角色
    supervisors = User.query.filter_by(role='teacher_supervisor').all()
    print(f"\n📊 teacher_supervisor角色用户数: {len(supervisors)}")
    for user in supervisors:
        print(f"   - ID: {user.id}, 用户名: {user.username}, 手机: {user.phone}")
        # 检查该班主任负责的客户数
        customer_count = Customer.query.filter_by(teacher_user_id=user.id).count()
        print(f"     负责客户数: {customer_count}")
    
    # 4. 检查Customer表的teacher_user_id字段
    print("\n📊 客户的班主任分配情况：")
    customers_with_teacher = Customer.query.filter(Customer.teacher_user_id.isnot(None)).all()
    print(f"   已分配班主任的客户数: {len(customers_with_teacher)}")
    for customer in customers_with_teacher:
        teacher = User.query.get(customer.teacher_user_id)
        if teacher:
            print(f"   - 客户ID: {customer.id}, 班主任: {teacher.username} (角色: {teacher.role})")
        else:
            print(f"   - 客户ID: {customer.id}, 班主任ID: {customer.teacher_user_id} (用户不存在)")
    
    # 5. 验证is_teacher_supervisor()方法
    print("\n📊 验证is_teacher_supervisor()方法：")
    for user in supervisors:
        if user.is_teacher_supervisor():
            print(f"   ✅ {user.username} 的is_teacher_supervisor()返回True")
        else:
            print(f"   ❌ {user.username} 的is_teacher_supervisor()返回False")
    
    print("\n" + "=" * 60)
    print("✅ 验证完成！")
    print("=" * 60)

