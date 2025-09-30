#!/usr/bin/env python3
"""测试用户删除功能"""

from run import app
from models import User, LoginLog, db

with app.app_context():
    print("=" * 60)
    print("测试用户删除功能")
    print("=" * 60)
    
    # 1. 创建一个测试用户
    print("\n1. 创建测试用户...")
    test_user = User(
        username='测试用户_待删除',
        phone='13999999999',
        role='sales',
        status=True
    )
    db.session.add(test_user)
    db.session.commit()
    print(f"✅ 创建成功，用户ID: {test_user.id}")
    
    # 2. 添加一条登录日志
    print("\n2. 添加登录日志...")
    login_log = LoginLog(
        user_id=test_user.id,
        phone=test_user.phone,
        login_result='success'
    )
    db.session.add(login_log)
    db.session.commit()
    print(f"✅ 登录日志添加成功")
    
    # 3. 检查关联数据
    print("\n3. 检查关联数据...")
    leads_count = test_user.leads_as_sales.count()
    customers_count = test_user.customers_as_teacher.count()
    login_logs_count = LoginLog.query.filter_by(user_id=test_user.id).count()
    
    print(f"  关联线索数: {leads_count}")
    print(f"  关联客户数: {customers_count}")
    print(f"  登录日志数: {login_logs_count}")
    print(f"  可删除: {'是' if (leads_count == 0 and customers_count == 0) else '否'}")
    
    # 4. 模拟删除操作
    print("\n4. 执行删除操作...")
    
    if leads_count > 0 or customers_count > 0:
        print(f"❌ 用户有关联数据，无法删除")
    else:
        # 删除登录日志
        LoginLog.query.filter_by(user_id=test_user.id).delete()
        print(f"  ✅ 删除了 {login_logs_count} 条登录日志")
        
        # 删除用户
        username = test_user.username
        user_id = test_user.id
        db.session.delete(test_user)
        db.session.commit()
        print(f"  ✅ 删除用户成功: {username}")
        
        # 5. 验证删除结果
        print("\n5. 验证删除结果...")
        deleted_user = User.query.get(user_id)
        remaining_logs = LoginLog.query.filter_by(user_id=user_id).count()
        
        if deleted_user is None:
            print(f"  ✅ 用户已被删除")
        else:
            print(f"  ❌ 用户仍然存在")
        
        if remaining_logs == 0:
            print(f"  ✅ 登录日志已被删除")
        else:
            print(f"  ❌ 还有 {remaining_logs} 条登录日志")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)

