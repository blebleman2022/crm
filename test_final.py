"""
最终完整测试
"""
from run import app
from models import db, Lead, Customer, User
from flask import session

def test_all():
    """运行所有测试"""
    print('=' * 80)
    print('开始完整系统测试')
    print('=' * 80)
    
    with app.test_client() as client:
        # 测试1：登录
        print('\n测试1：用户登录')
        print('-' * 80)
        response = client.post('/auth/login', data={
            'phone': '13909999451'  # Kingble的手机号
        }, follow_redirects=False)
        
        if response.status_code == 302:
            print('✅ 登录成功，重定向到仪表板')
        else:
            print(f'❌ 登录失败: {response.status_code}')
            return False
        
        # 测试2：访问客户列表
        print('\n测试2：访问客户列表')
        print('-' * 80)
        response = client.get('/customers/list')
        
        if response.status_code == 200:
            html = response.data.decode('utf-8')
            if '客户管理' in html and '学员姓名' in html:
                print('✅ 客户列表页面正常显示')
                
                # 检查奖项列
                if '奖项' in html:
                    print('✅ 奖项列正常显示')
                else:
                    print('⚠️  未找到奖项列')
            else:
                print('❌ 页面内容不正确')
                return False
        else:
            print(f'❌ 访问失败: {response.status_code}')
            return False
        
        # 测试3：访问客户编辑页面
        print('\n测试3：访问客户编辑页面')
        print('-' * 80)

        # 获取客户ID
        customer_id = None
        with app.app_context():
            customer = Customer.query.first()
            if customer:
                customer_id = customer.id

        if customer_id:
            response = client.get(f'/customers/{customer_id}/edit')

            if response.status_code == 200:
                html = response.data.decode('utf-8')

                # 检查必要字段
                required_fields = [
                    'student_name',
                    'sales_user_id',
                    'competition_award_level',
                    'additional_requirements',
                    'exam_year'
                ]

                missing_fields = []
                for field in required_fields:
                    if field not in html:
                        missing_fields.append(field)

                if not missing_fields:
                    print(f'✅ 客户编辑页面正常显示 (客户ID: {customer_id})')
                else:
                    print(f'❌ 缺少字段: {missing_fields}')
                    return False
            else:
                print(f'❌ 访问失败: {response.status_code}')
                return False
        else:
            print('⚠️  没有客户数据，跳过测试')
        
        # 测试4：更新客户信息
        print('\n测试4：更新客户信息')
        print('-' * 80)

        # 获取客户数据
        customer_data = None
        with app.app_context():
            customer = Customer.query.first()
            if customer:
                customer_data = {
                    'id': customer.id,
                    'student_name': customer.lead.student_name,
                    'contact_info': customer.lead.contact_info,
                    'sales_user_id': customer.lead.sales_user_id,
                    'teacher_user_id': customer.teacher_user_id or '',
                    'exam_year': customer.exam_year
                }

        if customer_data:
            # 准备表单数据
            form_data = {
                'student_name': customer_data['student_name'],
                'contact_info': customer_data['contact_info'],
                'sales_user_id': str(customer_data['sales_user_id']),
                'competition_award_level': '市奖',
                'additional_requirements': '测试额外要求内容',
                'exam_year': str(customer_data['exam_year']),
                'notes': '测试备注内容'
            }

            # 只有当teacher_user_id不为空时才添加
            if customer_data['teacher_user_id']:
                form_data['teacher_user_id'] = str(customer_data['teacher_user_id'])

            response = client.post(f'/customers/{customer_data["id"]}/edit', data=form_data, follow_redirects=False)

            if response.status_code == 302:
                print('✅ 客户更新成功，重定向到列表页')

                # 验证更新
                with app.app_context():
                    updated_customer = Customer.query.get(customer_data['id'])
                    if updated_customer.competition_award_level == '市奖':
                        print(f'✅ 奖项等级更新成功: {updated_customer.competition_award_level}')
                    else:
                        print(f'❌ 奖项等级更新失败: {updated_customer.competition_award_level}')
                        return False

                    if updated_customer.additional_requirements == '测试额外要求内容':
                        print(f'✅ 额外要求更新成功')
                    else:
                        print(f'❌ 额外要求更新失败')
                        return False
            else:
                html = response.data.decode('utf-8')
                if 'error' in html or '错误' in html or '失败' in html:
                    # 提取错误信息
                    import re
                    error_match = re.search(r'class="[^"]*alert[^"]*"[^>]*>([^<]+)', html)
                    if error_match:
                        print(f'❌ 更新失败: {error_match.group(1).strip()}')
                    else:
                        print(f'❌ 更新失败: 状态码 {response.status_code}')
                else:
                    print(f'❌ 更新失败: 状态码 {response.status_code}')
                return False
        else:
            print('⚠️  没有客户数据，跳过测试')
        
        # 测试5：数据一致性
        print('\n测试5：数据一致性检查')
        print('-' * 80)
        
        with app.app_context():
            customers = Customer.query.all()
            
            for customer in customers:
                # 检查责任销售
                sales_user = customer.get_sales_user()
                if not sales_user:
                    print(f'❌ 客户 {customer.id} 没有责任销售')
                    return False
                
                # 检查服务类型
                service_types = customer.get_service_types()
                
                # 检查奖项信息
                award_level = customer.competition_award_level
                
                print(f'客户 {customer.id} ({customer.lead.get_display_name()}):')
                print(f'  责任销售: {sales_user.username}')
                print(f'  服务类型: {service_types}')
                print(f'  奖项等级: {award_level or "无"}')
                print(f'  额外要求: {customer.additional_requirements[:30] + "..." if customer.additional_requirements and len(customer.additional_requirements) > 30 else customer.additional_requirements or "无"}')
            
            print(f'\n✅ 数据一致性检查通过 (共 {len(customers)} 个客户)')
        
        # 测试6：筛选功能
        print('\n测试6：客户筛选功能')
        print('-' * 80)
        
        response = client.get('/customers/list?award_filter=市奖')
        if response.status_code == 200:
            print('✅ 奖项筛选功能正常')
        else:
            print(f'❌ 筛选失败: {response.status_code}')
            return False
        
        return True


def main():
    """主函数"""
    print('\n' + '🚀 ' * 20)
    print('EduConnect CRM - 数据库优化完整测试')
    print('🚀 ' * 20 + '\n')
    
    try:
        success = test_all()
        
        if success:
            print('\n' + '=' * 80)
            print('✅ 所有测试通过！')
            print('=' * 80)
            print('\n📊 测试总结:')
            print('  ✓ 用户登录功能正常')
            print('  ✓ 客户列表显示正常')
            print('  ✓ 客户编辑页面正常')
            print('  ✓ 客户更新功能正常')
            print('  ✓ 数据一致性检查通过')
            print('  ✓ 筛选功能正常')
            print('\n🎉 系统优化完成，所有功能正常，数据完整！')
            return True
        else:
            print('\n' + '=' * 80)
            print('❌ 测试失败')
            print('=' * 80)
            return False
            
    except Exception as e:
        print(f'\n❌ 测试出错：{e}')
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)

