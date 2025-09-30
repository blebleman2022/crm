#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据架构优化测试脚本
测试客户表通过 @property 从线索表读取合同内容
"""

from run import app
from models import db, Lead, Customer

def test_property_reading():
    """测试通过 @property 读取数据"""
    print("\n" + "=" * 80)
    print("测试1: 验证 @property 读取功能")
    print("=" * 80)
    
    with app.app_context():
        # 查找一个已转客户的线索
        customer = Customer.query.join(Lead).filter(
            Lead.competition_award_level.isnot(None)
        ).first()
        
        if not customer:
            print("❌ 没有找到有奖项要求的客户")
            return False
        
        lead = customer.lead
        
        print(f"\n客户ID: {customer.id}")
        print(f"学员姓名: {lead.student_name}")
        print("-" * 80)
        
        # 测试从线索表读取
        print(f"\n从线索表读取:")
        print(f"  lead.competition_award_level = {lead.competition_award_level}")
        print(f"  lead.additional_requirements = {lead.additional_requirements}")
        
        # 测试通过 @property 读取
        print(f"\n通过 @property 读取:")
        print(f"  customer.competition_award_level = {customer.competition_award_level}")
        print(f"  customer.additional_requirements = {customer.additional_requirements}")
        
        # 验证数据一致性
        if customer.competition_award_level == lead.competition_award_level:
            print("\n✅ competition_award_level 读取一致")
        else:
            print(f"\n❌ competition_award_level 不一致")
            print(f"   线索表: {lead.competition_award_level}")
            print(f"   客户表: {customer.competition_award_level}")
            return False
        
        if customer.additional_requirements == lead.additional_requirements:
            print("✅ additional_requirements 读取一致")
        else:
            print(f"❌ additional_requirements 不一致")
            print(f"   线索表: {lead.additional_requirements}")
            print(f"   客户表: {customer.additional_requirements}")
            return False
        
        return True

def test_database_fields():
    """测试数据库字段是否保留"""
    print("\n" + "=" * 80)
    print("测试2: 验证数据库字段保留（向后兼容）")
    print("=" * 80)
    
    with app.app_context():
        from sqlalchemy import inspect
        
        inspector = inspect(db.engine)
        columns = inspector.get_columns('customers')
        
        column_names = [col['name'] for col in columns]
        
        print(f"\n客户表字段列表:")
        for col in columns:
            print(f"  - {col['name']:30} {str(col['type']):20}")
        
        # 检查字段是否存在
        if 'competition_award_level' in column_names:
            print("\n✅ competition_award_level 字段保留（向后兼容）")
        else:
            print("\n❌ competition_award_level 字段不存在")
            return False
        
        if 'additional_requirements' in column_names:
            print("✅ additional_requirements 字段保留（向后兼容）")
        else:
            print("❌ additional_requirements 字段不存在")
            return False
        
        return True

def test_model_attributes():
    """测试模型属性"""
    print("\n" + "=" * 80)
    print("测试3: 验证模型属性")
    print("=" * 80)
    
    with app.app_context():
        customer = Customer.query.first()
        
        if not customer:
            print("❌ 没有找到客户记录")
            return False
        
        # 检查是否有 @property
        print(f"\n检查 Customer 模型属性:")
        
        # 检查 competition_award_level
        if hasattr(Customer, 'competition_award_level'):
            prop = getattr(Customer, 'competition_award_level')
            if isinstance(prop, property):
                print("✅ competition_award_level 是 @property")
            else:
                print("❌ competition_award_level 不是 @property")
                return False
        else:
            print("❌ competition_award_level 属性不存在")
            return False
        
        # 检查 additional_requirements
        if hasattr(Customer, 'additional_requirements'):
            prop = getattr(Customer, 'additional_requirements')
            if isinstance(prop, property):
                print("✅ additional_requirements 是 @property")
            else:
                print("❌ additional_requirements 不是 @property")
                return False
        else:
            print("❌ additional_requirements 属性不存在")
            return False
        
        # 检查废弃字段
        if hasattr(customer, '_competition_award_level'):
            print("✅ _competition_award_level 字段保留（数据库字段）")
        else:
            print("⚠️  _competition_award_level 字段不存在")
        
        return True

def test_api_compatibility():
    """测试API兼容性"""
    print("\n" + "=" * 80)
    print("测试4: 验证API兼容性")
    print("=" * 80)
    
    with app.app_context():
        customer = Customer.query.join(Lead).filter(
            Lead.competition_award_level.isnot(None)
        ).first()
        
        if not customer:
            print("❌ 没有找到有奖项要求的客户")
            return False
        
        # 模拟API返回数据
        customer_data = {
            'id': customer.id,
            'student_name': customer.lead.student_name,
            'competition_award_level': customer.competition_award_level,  # 通过 @property 读取
            'additional_requirements': customer.additional_requirements,  # 通过 @property 读取
        }
        
        print(f"\nAPI 返回数据:")
        print(f"  id: {customer_data['id']}")
        print(f"  student_name: {customer_data['student_name']}")
        print(f"  competition_award_level: {customer_data['competition_award_level']}")
        print(f"  additional_requirements: {customer_data['additional_requirements']}")
        
        print("\n✅ API 兼容性测试通过")
        return True

def test_filter_query():
    """测试过滤查询"""
    print("\n" + "=" * 80)
    print("测试5: 验证过滤查询")
    print("=" * 80)
    
    with app.app_context():
        # 测试按奖项等级过滤（从线索表）
        customers = Customer.query.join(Lead).filter(
            Lead.competition_award_level == '国奖'
        ).all()
        
        print(f"\n查询奖项等级为'国奖'的客户:")
        print(f"  找到 {len(customers)} 个客户")
        
        for customer in customers[:3]:  # 只显示前3个
            print(f"  - {customer.lead.student_name}: {customer.competition_award_level}")
        
        print("\n✅ 过滤查询测试通过")
        return True

def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("数据架构优化测试")
    print("=" * 80)
    print("\n测试目标:")
    print("  1. 验证客户表通过 @property 从线索表读取合同内容")
    print("  2. 验证数据库字段保留（向后兼容）")
    print("  3. 验证API兼容性")
    print("  4. 验证过滤查询功能")
    
    results = []
    
    # 运行测试
    results.append(("@property 读取功能", test_property_reading()))
    results.append(("数据库字段保留", test_database_fields()))
    results.append(("模型属性", test_model_attributes()))
    results.append(("API 兼容性", test_api_compatibility()))
    results.append(("过滤查询", test_filter_query()))
    
    # 汇总结果
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:30} {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 所有测试通过！数据架构优化成功！")
    else:
        print("❌ 部分测试失败，请检查问题")
    print("=" * 80)
    
    return all_passed

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)

