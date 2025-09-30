#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
必填字段调整验证脚本
验证必填字段调整是否正确
"""

def check_template_required_fields():
    """检查模板中的必填字段设置"""
    print("\n" + "=" * 80)
    print("必填字段调整验证")
    print("=" * 80)
    
    try:
        with open('templates/leads/edit.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 应该有必填标记的字段
        required_fields = [
            ('家长微信名', 'parent_wechat_display_name'),
            ('家长微信号', 'parent_wechat_name'),
            ('线索来源', 'lead_source'),
            ('责任销售', 'sales_user_id'),
        ]
        
        # 不应该有必填标记的字段
        optional_fields = [
            ('学员姓名', 'student_name'),
            ('联系电话', 'contact_info'),
            ('年级', 'grade'),
            ('行政区', 'district'),
            ('学校', 'school'),
            ('服务类型', 'service_types'),
            ('竞赛奖项等级', 'competition_award_level'),
            ('额外要求', 'additional_requirements'),
        ]
        
        print("\n✅ 应该有必填标记的字段:")
        print("-" * 60)
        
        all_passed = True
        
        for field_name, field_id in required_fields:
            # 检查是否有条件必填逻辑
            if field_id in ['parent_wechat_display_name', 'parent_wechat_name']:
                # 这两个字段应该有条件必填逻辑
                pattern = '{% if not is_field_locked(lead.' + field_id + ') %}<span class="text-red-500">*</span>{% endif %}'
                has_conditional_required = pattern in content

                # 检查是否有条件required属性
                required_pattern = '{% if not is_field_locked(lead.' + field_id + ') %}required{% endif %}'
                has_conditional_required_attr = required_pattern in content
                
                status1 = "✅" if has_conditional_required else "❌"
                status2 = "✅" if has_conditional_required_attr else "❌"
                
                print(f"{status1} {field_name:12} - 条件必填标记: {'存在' if has_conditional_required else '缺失'}")
                print(f"{status2} {field_name:12} - 条件required属性: {'存在' if has_conditional_required_attr else '缺失'}")
                
                if not (has_conditional_required and has_conditional_required_attr):
                    all_passed = False
                    
            elif field_id in ['lead_source', 'sales_user_id']:
                # 这两个字段已经有条件必填逻辑
                pattern = '{% if not is_field_locked(lead.' + field_id + ') %}<span class="text-red-500">*</span>{% endif %}'
                has_conditional_required = pattern in content

                required_pattern = '{% if not is_field_locked(lead.' + field_id + ') %}required{% endif %}'
                has_conditional_required_attr = required_pattern in content
                
                status1 = "✅" if has_conditional_required else "❌"
                status2 = "✅" if has_conditional_required_attr else "❌"
                
                print(f"{status1} {field_name:12} - 条件必填标记: {'存在' if has_conditional_required else '缺失'}")
                print(f"{status2} {field_name:12} - 条件required属性: {'存在' if has_conditional_required_attr else '缺失'}")
                
                if not (has_conditional_required and has_conditional_required_attr):
                    all_passed = False
        
        print("\n❌ 不应该有必填标记的字段:")
        print("-" * 60)
        
        for field_name, field_id in optional_fields:
            # 检查是否有必填标记
            patterns_to_check = [
                f'<span class="text-red-500">*</span>',
                f'required',
            ]
            
            # 特殊处理：检查字段附近是否有必填标记
            field_section_start = content.find(f'name="{field_id}"')
            if field_section_start == -1:
                field_section_start = content.find(f'id="{field_id}"')
            
            if field_section_start != -1:
                # 检查字段前后200个字符
                section_start = max(0, field_section_start - 200)
                section_end = min(len(content), field_section_start + 200)
                field_section = content[section_start:section_end]
                
                has_required_mark = '<span class="text-red-500">*</span>' in field_section
                has_required_attr = 'required' in field_section and 'required{% endif %}' not in field_section
                
                status1 = "✅" if not has_required_mark else "❌"
                status2 = "✅" if not has_required_attr else "❌"
                
                print(f"{status1} {field_name:12} - 无必填标记: {'正确' if not has_required_mark else '仍有标记'}")
                print(f"{status2} {field_name:12} - 无required属性: {'正确' if not has_required_attr else '仍有属性'}")
                
                if has_required_mark or has_required_attr:
                    all_passed = False
            else:
                print(f"⚠️  {field_name:12} - 字段未找到")
        
        # 特殊检查：服务类型
        service_type_section = content[content.find('服务类型'):content.find('服务类型') + 100] if '服务类型' in content else ''
        has_service_required = '<span class="text-red-500">*</span>' in service_type_section
        
        status = "✅" if not has_service_required else "❌"
        print(f"{status} {'服务类型':12} - 无必填标记: {'正确' if not has_service_required else '仍有标记'}")
        
        if has_service_required:
            all_passed = False
        
        # 特殊检查：竞赛奖项等级
        competition_section = content[content.find('竞赛奖项等级'):content.find('竞赛奖项等级') + 100] if '竞赛奖项等级' in content else ''
        has_competition_required = '<span class="text-red-500">*</span>' in competition_section
        
        status = "✅" if not has_competition_required else "❌"
        print(f"{status} {'竞赛奖项等级':12} - 无必填标记: {'正确' if not has_competition_required else '仍有标记'}")
        
        if has_competition_required:
            all_passed = False
        
        print("\n" + "=" * 80)
        if all_passed:
            print("🎉 必填字段调整验证通过！")
            print("\n调整结果:")
            print("✅ 家长微信名 - 已设为必填")
            print("✅ 家长微信号 - 保持必填")
            print("✅ 线索来源 - 保持条件必填")
            print("✅ 责任销售 - 保持条件必填")
            print("✅ 其他字段 - 已设为可选")
        else:
            print("❌ 必填字段调整验证失败，请检查问题")
        print("=" * 80)
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 检查模板文件失败: {e}")
        return False

def check_help_text():
    """检查帮助文本是否正确"""
    print("\n" + "=" * 80)
    print("帮助文本检查")
    print("=" * 80)
    
    try:
        with open('templates/leads/edit.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查必填字段的帮助文本
        help_text_checks = [
            ('家长微信名', '必填，输入家长的微信显示名称'),
            ('家长微信号', '必填，输入家长的微信号'),
            ('年级', '可选，选择学员当前年级'),
        ]
        
        print("\n检查帮助文本:")
        print("-" * 60)
        
        all_passed = True
        
        for field_name, expected_text in help_text_checks:
            has_text = expected_text in content
            status = "✅" if has_text else "❌"
            print(f"{status} {field_name:12} - {expected_text}: {'存在' if has_text else '缺失'}")
            
            if not has_text:
                all_passed = False
        
        print("\n" + "=" * 80)
        if all_passed:
            print("✅ 帮助文本检查通过！")
        else:
            print("❌ 帮助文本检查失败")
        print("=" * 80)
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 检查帮助文本失败: {e}")
        return False

def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("必填字段调整验证")
    print("=" * 80)
    print("\n调整要求:")
    print("✅ 必填字段：家长微信号、家长微信名、线索来源、责任销售")
    print("✅ 其他字段：均为可选")
    print("✅ 必填字段显示红色 * 标记")
    
    results = []
    
    # 运行测试
    results.append(("必填字段设置检查", check_template_required_fields()))
    results.append(("帮助文本检查", check_help_text()))
    
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
        print("🎉 所有测试通过！必填字段调整成功！")
        print("\n最终设置:")
        print("✅ 必填字段（4个）：")
        print("   - 家长微信名（条件必填）")
        print("   - 家长微信号（条件必填）")
        print("   - 线索来源（条件必填）")
        print("   - 责任销售（条件必填）")
        print("✅ 可选字段：其他所有字段")
        print("✅ 锁定机制：有值后自动锁定，不再显示必填标记")
    else:
        print("❌ 部分测试失败，请检查问题")
    print("=" * 80)
    
    return all_passed

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
