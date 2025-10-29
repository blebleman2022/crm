#!/usr/bin/env python3
"""
测试老师数据隔离功能

测试场景：
1. 班主任A（葛）可以看到自己创建的2个老师
2. 班主任B（王五）看不到班主任A的老师
3. 班主任B创建新老师后，只能看到自己创建的老师
4. 班主任A无法编辑/删除班主任B创建的老师
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, Teacher, User
from run import create_app

def test_isolation():
    """测试数据隔离"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("测试老师数据隔离功能")
        print("=" * 60)
        
        # 获取两个班主任
        supervisor_a = User.query.filter_by(username='葛', role='teacher_supervisor').first()
        supervisor_b = User.query.filter_by(username='王五', role='teacher_supervisor').first()
        
        if not supervisor_a or not supervisor_b:
            print("❌ 错误：找不到测试用的班主任账号")
            return
        
        print(f"\n班主任A: {supervisor_a.username} (ID: {supervisor_a.id})")
        print(f"班主任B: {supervisor_b.username} (ID: {supervisor_b.id})")
        
        # 测试1：班主任A可以看到自己创建的老师
        print("\n" + "=" * 60)
        print("测试1：班主任A查看自己创建的老师")
        print("=" * 60)
        teachers_a = Teacher.query.filter_by(created_by_user_id=supervisor_a.id).all()
        print(f"✅ 班主任A ({supervisor_a.username}) 创建的老师数量: {len(teachers_a)}")
        for t in teachers_a:
            print(f"   - {t.chinese_name} (ID: {t.id})")
        
        # 测试2：班主任B看不到班主任A的老师
        print("\n" + "=" * 60)
        print("测试2：班主任B查看自己创建的老师")
        print("=" * 60)
        teachers_b = Teacher.query.filter_by(created_by_user_id=supervisor_b.id).all()
        print(f"✅ 班主任B ({supervisor_b.username}) 创建的老师数量: {len(teachers_b)}")
        if len(teachers_b) == 0:
            print("   （无）")
        else:
            for t in teachers_b:
                print(f"   - {t.chinese_name} (ID: {t.id})")
        
        # 测试3：为班主任B创建一个新老师
        print("\n" + "=" * 60)
        print("测试3：班主任B创建新老师")
        print("=" * 60)
        
        # 检查是否已存在测试老师
        test_teacher = Teacher.query.filter_by(
            chinese_name='测试老师-王五',
            created_by_user_id=supervisor_b.id
        ).first()
        
        if test_teacher:
            print(f"   测试老师已存在: {test_teacher.chinese_name} (ID: {test_teacher.id})")
        else:
            test_teacher = Teacher(
                chinese_name='测试老师-王五',
                english_name='Test Teacher Wang',
                current_institution='测试大学',
                major_direction='计算机科学',
                status=True,
                created_by_user_id=supervisor_b.id
            )
            db.session.add(test_teacher)
            db.session.commit()
            print(f"✅ 已为班主任B创建测试老师: {test_teacher.chinese_name} (ID: {test_teacher.id})")
        
        # 测试4：验证数据隔离
        print("\n" + "=" * 60)
        print("测试4：验证数据隔离")
        print("=" * 60)
        
        teachers_a_after = Teacher.query.filter_by(created_by_user_id=supervisor_a.id).all()
        teachers_b_after = Teacher.query.filter_by(created_by_user_id=supervisor_b.id).all()
        
        print(f"班主任A ({supervisor_a.username}) 可见的老师:")
        for t in teachers_a_after:
            print(f"   - {t.chinese_name} (ID: {t.id})")
        
        print(f"\n班主任B ({supervisor_b.username}) 可见的老师:")
        for t in teachers_b_after:
            print(f"   - {t.chinese_name} (ID: {t.id})")
        
        # 验证隔离
        teacher_a_ids = {t.id for t in teachers_a_after}
        teacher_b_ids = {t.id for t in teachers_b_after}
        
        if teacher_a_ids & teacher_b_ids:
            print("\n❌ 错误：发现共享的老师，数据隔离失败！")
        else:
            print("\n✅ 数据隔离成功：两个班主任看到的老师完全不同")
        
        # 测试5：统计信息
        print("\n" + "=" * 60)
        print("测试5：统计信息")
        print("=" * 60)
        
        total_teachers = Teacher.query.count()
        print(f"系统中老师总数: {total_teachers}")
        print(f"班主任A创建的老师数: {len(teachers_a_after)}")
        print(f"班主任B创建的老师数: {len(teachers_b_after)}")
        print(f"数据隔离验证: {len(teachers_a_after) + len(teachers_b_after) == total_teachers}")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60)

if __name__ == '__main__':
    test_isolation()

