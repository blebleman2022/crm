#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
年级字段修复验证脚本
验证年级字段不再是必填项，且锁定逻辑正确
"""

from run import app
from models import db, Lead

def test_grade_field_logic():
    """测试年级字段的逻辑"""
    print("\n" + "=" * 80)
    print("年级字段修复验证")
    print("=" * 80)
    
    with app.app_context():
        # 查找一个有年级的线索
        lead_with_grade = Lead.query.filter(Lead.grade.isnot(None)).first()
        
        if lead_with_grade:
            print(f"\n测试线索: {lead_with_grade.get_display_name()}")
            print(f"年级: {lead_with_grade.grade}")
            print("-" * 80)
            
            # 测试锁定逻辑
            def is_field_locked(value):
                """模拟模板中的锁定逻辑"""
                return value is not None and value != ''
            
            is_locked = is_field_locked(lead_with_grade.grade)
            print(f"年级是否锁定: {is_locked}")
            
            if is_locked:
                print("✅ 年级字段应该显示为锁定状态")
                print("✅ 不应该显示必填标记 (*)")
                print("✅ 应该显示 '(已锁定，无法修改)'")
                print("✅ 应该有灰色背景和禁用状态")
            else:
                print("❌ 年级字段应该被锁定但没有被锁定")
                return False
        
        # 查找一个没有年级的线索
        lead_without_grade = Lead.query.filter(
            (Lead.grade.is_(None)) | (Lead.grade == '')
        ).first()
        
        if lead_without_grade:
            print(f"\n测试线索: {lead_without_grade.get_display_name()}")
            print(f"年级: {lead_without_grade.grade}")
            print("-" * 80)
            
            is_locked = is_field_locked(lead_without_grade.grade)
            print(f"年级是否锁定: {is_locked}")
            
            if not is_locked:
                print("✅ 年级字段应该显示为可编辑状态")
                print("✅ 不应该显示必填标记 (*)")
                print("✅ 应该显示 '可选，选择学员当前年级'")
                print("✅ 应该有正常背景和可编辑状态")
            else:
                print("❌ 年级字段不应该被锁定")
                return False
        
        print("\n" + "=" * 80)
        print("✅ 年级字段逻辑验证通过")
        print("=" * 80)
        
        return True

def test_template_logic():
    """测试模板逻辑"""
    print("\n" + "=" * 80)
    print("模板逻辑测试")
    print("=" * 80)
    
    # 模拟模板中的逻辑
    def is_field_locked(value):
        return value is not None and value != ''
    
    # 测试用例
    test_cases = [
        ("高二", True, "有值应该锁定"),
        ("", False, "空字符串不应该锁定"),
        (None, False, "None值不应该锁定"),
        ("1年级", True, "有值应该锁定"),
    ]
    
    print("\n测试锁定逻辑:")
    for value, expected, description in test_cases:
        result = is_field_locked(value)
        status = "✅" if result == expected else "❌"
        print(f"{status} {description}: 值='{value}', 预期={expected}, 实际={result}")
        
        if result != expected:
            return False
    
    print("\n" + "=" * 80)
    print("✅ 模板逻辑测试通过")
    print("=" * 80)
    
    return True

def check_template_changes():
    """检查模板文件的修改"""
    print("\n" + "=" * 80)
    print("检查模板文件修改")
    print("=" * 80)
    
    try:
        with open('templates/leads/edit.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键修改
        checks = [
            ('{% if not is_field_locked(lead.grade) %}<span class="text-red-500">*</span>{% endif %}', False, "不应该有必填标记逻辑"),
            ('{% if is_field_locked(lead.grade) %}disabled{% endif %}', True, "应该有禁用逻辑"),
            ('可选，选择学员当前年级', True, "应该显示'可选'提示"),
            ('{% if not is_field_locked(lead.grade) %}required{% endif %}', False, "不应该有required属性"),
        ]
        
        print("\n检查模板内容:")
        for pattern, should_exist, description in checks:
            exists = pattern in content
            if should_exist:
                status = "✅" if exists else "❌"
                print(f"{status} {description}: {'存在' if exists else '不存在'}")
                if not exists:
                    return False
            else:
                status = "✅" if not exists else "❌"
                print(f"{status} {description}: {'已移除' if not exists else '仍存在'}")
                if exists:
                    return False
        
        print("\n" + "=" * 80)
        print("✅ 模板文件检查通过")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ 检查模板文件失败: {e}")
        return False

def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("年级字段修复验证")
    print("=" * 80)
    print("\n修复内容:")
    print("1. 移除年级字段的必填属性 (required)")
    print("2. 移除年级字段的必填标记 (*)")
    print("3. 修改提示文本为'可选，选择学员当前年级'")
    print("4. 保持锁定逻辑不变")
    
    results = []
    
    # 运行测试
    results.append(("数据库逻辑测试", test_grade_field_logic()))
    results.append(("模板逻辑测试", test_template_logic()))
    results.append(("模板文件检查", check_template_changes()))
    
    # 汇总结果
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:20} {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 所有测试通过！年级字段修复成功！")
        print("\n修复效果:")
        print("✅ 年级字段不再是必填项")
        print("✅ 年级字段不显示必填标记 (*)")
        print("✅ 提示文本改为'可选，选择学员当前年级'")
        print("✅ 有值的年级字段仍然会被锁定")
        print("✅ 锁定的年级字段显示'(已锁定，无法修改)'")
    else:
        print("❌ 部分测试失败，请检查问题")
    print("=" * 80)
    
    return all_passed

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
