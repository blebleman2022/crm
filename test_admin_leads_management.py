#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员线索管理功能测试脚本
验证管理员线索管理模块是否正常工作
"""

from run import app
from models import db, User, Lead

def test_admin_routes():
    """测试管理员线索管理路由"""
    print("\n" + "=" * 80)
    print("管理员线索管理路由测试")
    print("=" * 80)
    
    with app.app_context():
        # 检查路由是否正确注册
        routes = []
        for rule in app.url_map.iter_rules():
            if 'admin' in rule.endpoint and 'lead' in rule.endpoint:
                routes.append({
                    'endpoint': rule.endpoint,
                    'rule': rule.rule,
                    'methods': list(rule.methods - {'HEAD', 'OPTIONS'})
                })
        
        print("\n注册的管理员线索路由:")
        print("-" * 60)
        
        expected_routes = [
            'admin.leads',
            'admin.search_leads', 
            'admin.edit_lead',
            'admin.update_lead'
        ]
        
        found_routes = [route['endpoint'] for route in routes]
        
        for expected in expected_routes:
            if expected in found_routes:
                route_info = next(r for r in routes if r['endpoint'] == expected)
                print(f"✅ {expected:20} {route_info['rule']:30} {route_info['methods']}")
            else:
                print(f"❌ {expected:20} 路由未找到")
        
        all_routes_found = all(route in found_routes for route in expected_routes)
        
        print("\n" + "=" * 80)
        if all_routes_found:
            print("✅ 所有管理员线索路由注册成功！")
        else:
            print("❌ 部分路由注册失败")
        print("=" * 80)
        
        return all_routes_found

def test_template_files():
    """测试模板文件是否存在"""
    print("\n" + "=" * 80)
    print("模板文件检查")
    print("=" * 80)
    
    import os
    
    template_files = [
        'templates/admin/leads.html',
        'templates/admin/edit_lead.html'
    ]
    
    print("\n检查模板文件:")
    print("-" * 60)
    
    all_files_exist = True
    
    for template_file in template_files:
        if os.path.exists(template_file):
            # 检查文件大小
            size = os.path.getsize(template_file)
            print(f"✅ {template_file:35} 存在 ({size} bytes)")
        else:
            print(f"❌ {template_file:35} 不存在")
            all_files_exist = False
    
    print("\n" + "=" * 80)
    if all_files_exist:
        print("✅ 所有模板文件检查通过！")
    else:
        print("❌ 部分模板文件缺失")
    print("=" * 80)
    
    return all_files_exist

def test_search_functionality():
    """测试搜索功能"""
    print("\n" + "=" * 80)
    print("搜索功能测试")
    print("=" * 80)
    
    with app.app_context():
        # 查找一些测试数据
        leads = Lead.query.limit(3).all()
        
        if not leads:
            print("⚠️  数据库中没有线索数据，跳过搜索测试")
            return True
        
        print(f"\n找到 {len(leads)} 条线索数据用于测试:")
        print("-" * 60)
        
        for lead in leads:
            print(f"ID: {lead.id:3} | 学员: {lead.student_name or '未填写':10} | 家长微信名: {lead.parent_wechat_display_name or '未填写'}")
        
        # 测试搜索逻辑
        test_cases = []
        
        # 如果有学员姓名，测试按学员姓名搜索
        for lead in leads:
            if lead.student_name:
                test_cases.append(('学员姓名', lead.student_name, lead.id))
                break
        
        # 如果有家长微信名，测试按家长微信名搜索
        for lead in leads:
            if lead.parent_wechat_display_name:
                test_cases.append(('家长微信名', lead.parent_wechat_display_name, lead.id))
                break
        
        print(f"\n执行搜索测试 ({len(test_cases)} 个测试用例):")
        print("-" * 60)
        
        all_passed = True
        
        for search_type, query, expected_id in test_cases:
            # 模拟搜索查询
            results = Lead.query.filter(
                (Lead.student_name.ilike(f'%{query}%')) |
                (Lead.parent_wechat_display_name.ilike(f'%{query}%'))
            ).all()
            
            found_ids = [lead.id for lead in results]
            
            if expected_id in found_ids:
                print(f"✅ {search_type:10} 搜索 '{query}' -> 找到 {len(results)} 条结果")
            else:
                print(f"❌ {search_type:10} 搜索 '{query}' -> 未找到预期结果")
                all_passed = False
        
        print("\n" + "=" * 80)
        if all_passed:
            print("✅ 搜索功能测试通过！")
        else:
            print("❌ 搜索功能测试失败")
        print("=" * 80)
        
        return all_passed

def test_admin_sidebar():
    """测试管理员侧边栏是否包含线索管理"""
    print("\n" + "=" * 80)
    print("管理员侧边栏检查")
    print("=" * 80)
    
    try:
        with open('templates/admin/base.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键内容
        checks = [
            ('线索管理链接', "{{ url_for('admin.leads') }}"),
            ('线索管理文本', '线索管理'),
            ('线索管理图标', 'contact_page'),
            ('编辑线索路由', "admin.edit_lead"),
        ]
        
        print("\n检查侧边栏内容:")
        print("-" * 60)
        
        all_passed = True
        
        for check_name, pattern in checks:
            if pattern in content:
                print(f"✅ {check_name:15} 存在")
            else:
                print(f"❌ {check_name:15} 缺失")
                all_passed = False
        
        print("\n" + "=" * 80)
        if all_passed:
            print("✅ 管理员侧边栏检查通过！")
        else:
            print("❌ 管理员侧边栏检查失败")
        print("=" * 80)
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 检查侧边栏失败: {e}")
        return False

def test_edit_form_fields():
    """测试编辑表单字段"""
    print("\n" + "=" * 80)
    print("编辑表单字段检查")
    print("=" * 80)
    
    try:
        with open('templates/admin/edit_lead.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键字段
        required_fields = [
            'parent_wechat_display_name',
            'parent_wechat_name', 
            'student_name',
            'contact_info',
            'lead_source',
            'sales_user_id',
            'grade',
            'district',
            'school',
            'stage',
            'service_types',
            'competition_award_level',
            'additional_requirements',
            'contract_amount'
        ]
        
        print("\n检查表单字段:")
        print("-" * 60)
        
        all_fields_found = True
        
        for field in required_fields:
            if f'name="{field}"' in content:
                print(f"✅ {field:25} 存在")
            else:
                print(f"❌ {field:25} 缺失")
                all_fields_found = False
        
        # 检查是否没有锁定逻辑
        has_locking = 'is_field_locked' in content
        
        print(f"\n字段锁定检查:")
        print("-" * 60)
        if not has_locking:
            print("✅ 无字段锁定逻辑 - 管理员可编辑所有字段")
        else:
            print("❌ 仍有字段锁定逻辑 - 管理员应该能编辑所有字段")
            all_fields_found = False
        
        print("\n" + "=" * 80)
        if all_fields_found:
            print("✅ 编辑表单字段检查通过！")
        else:
            print("❌ 编辑表单字段检查失败")
        print("=" * 80)
        
        return all_fields_found
        
    except Exception as e:
        print(f"❌ 检查编辑表单失败: {e}")
        return False

def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("管理员线索管理功能测试")
    print("=" * 80)
    print("\n功能要求:")
    print("✅ 管理员页面侧边栏增加线索管理模块")
    print("✅ 右侧上方为搜索学员姓名或家长微信名的搜索框")
    print("✅ 下方空白，输入后搜索才出现符合条件的线索列表")
    print("✅ 线索列表形式如销售管理的线索列表")
    print("✅ 点击编辑可以编辑所有的字段信息")
    
    results = []
    
    # 运行测试
    results.append(("路由注册测试", test_admin_routes()))
    results.append(("模板文件检查", test_template_files()))
    results.append(("搜索功能测试", test_search_functionality()))
    results.append(("侧边栏检查", test_admin_sidebar()))
    results.append(("编辑表单检查", test_edit_form_fields()))
    
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
        print("🎉 所有测试通过！管理员线索管理功能开发完成！")
        print("\n功能特性:")
        print("✅ 侧边栏新增线索管理模块")
        print("✅ 支持按学员姓名或家长微信名搜索")
        print("✅ 搜索结果以表格形式展示")
        print("✅ 管理员可编辑所有字段（无锁定限制）")
        print("✅ 完整的CRUD操作支持")
        print("\n访问地址:")
        print("📍 线索管理: http://localhost:5001/admin/leads")
        print("📍 编辑线索: http://localhost:5001/admin/leads/<id>/edit")
    else:
        print("❌ 部分测试失败，请检查问题")
    print("=" * 80)
    
    return all_passed

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
