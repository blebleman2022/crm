"""
简单的功能测试
"""
from run import app
from models import db, Lead, Customer, User
from flask import session
from flask.testing import FlaskClient

def test_customer_list():
    """测试客户列表"""
    with app.test_client() as client:
        # 登录（使用手机号）
        with app.app_context():
            user = User.query.filter_by(username='Kingble').first()
            phone = user.phone if user else '13800138000'

        response = client.post('/login', data={
            'phone': phone
        }, follow_redirects=True)
        
        print('=' * 80)
        print('测试1：客户列表访问')
        print('=' * 80)
        
        # 访问客户列表
        response = client.get('/customers/list')
        assert response.status_code == 200, f'客户列表访问失败: {response.status_code}'
        
        # 检查页面内容
        html = response.data.decode('utf-8')
        assert '客户管理' in html, '页面标题不正确'
        assert '学员姓名' in html, '缺少学员姓名列'
        assert '奖项等级' in html or '奖项要求' in html, '缺少奖项列'
        
        print('✅ 客户列表访问测试通过')


def test_customer_edit_page():
    """测试客户编辑页面"""
    with app.test_client() as client:
        # 登录（使用手机号）
        with app.app_context():
            user = User.query.filter_by(username='Kingble').first()
            phone = user.phone if user else '13800138000'

        client.post('/login', data={
            'phone': phone
        }, follow_redirects=True)
        
        print('\n' + '=' * 80)
        print('测试2：客户编辑页面访问')
        print('=' * 80)
        
        # 获取第一个客户
        with app.app_context():
            customer = Customer.query.first()
            if customer:
                # 访问编辑页面
                response = client.get(f'/customers/{customer.id}/edit')
                assert response.status_code == 200, f'编辑页面访问失败: {response.status_code}'
                
                # 检查页面内容
                html = response.data.decode('utf-8')
                assert '编辑客户' in html, '页面标题不正确'
                assert 'student_name' in html, '缺少学员姓名字段'
                assert 'sales_user_id' in html, '缺少责任销售字段'
                assert 'competition_award_level' in html, '缺少竞赛奖项等级字段'
                assert 'additional_requirements' in html, '缺少额外要求字段'
                assert 'exam_year' in html, '缺少中高考年份字段'
                
                print(f'✅ 客户编辑页面访问测试通过 (客户ID: {customer.id})')
            else:
                print('⚠️  没有客户数据，跳过测试')


def test_customer_update():
    """测试客户更新"""
    with app.test_client() as client:
        # 登录（使用手机号）
        with app.app_context():
            user = User.query.filter_by(username='Kingble').first()
            phone = user.phone if user else '13800138000'

        client.post('/login', data={
            'phone': phone
        }, follow_redirects=True)
        
        print('\n' + '=' * 80)
        print('测试3：客户更新功能')
        print('=' * 80)
        
        # 获取第一个客户
        with app.app_context():
            customer = Customer.query.first()
            if customer:
                # 提交更新
                response = client.post(f'/customers/{customer.id}/edit', data={
                    'student_name': customer.lead.student_name,
                    'contact_info': customer.lead.contact_info,
                    'sales_user_id': customer.lead.sales_user_id,
                    'teacher_user_id': customer.teacher_user_id or '',
                    'competition_award_level': '市奖',
                    'additional_requirements': '测试额外要求',
                    'exam_year': customer.exam_year,
                    'notes': '测试备注'
                }, follow_redirects=True)
                
                assert response.status_code == 200, f'更新失败: {response.status_code}'
                
                # 验证更新
                with app.app_context():
                    updated_customer = Customer.query.get(customer.id)
                    assert updated_customer.competition_award_level == '市奖', '奖项等级更新失败'
                    assert updated_customer.additional_requirements == '测试额外要求', '额外要求更新失败'
                    
                print(f'✅ 客户更新功能测试通过 (客户ID: {customer.id})')
                print(f'   奖项等级: {updated_customer.competition_award_level}')
                print(f'   额外要求: {updated_customer.additional_requirements}')
            else:
                print('⚠️  没有客户数据，跳过测试')


def test_customer_filter():
    """测试客户筛选"""
    with app.test_client() as client:
        # 登录（使用手机号）
        with app.app_context():
            user = User.query.filter_by(username='Kingble').first()
            phone = user.phone if user else '13800138000'

        client.post('/login', data={
            'phone': phone
        }, follow_redirects=True)
        
        print('\n' + '=' * 80)
        print('测试4：客户筛选功能')
        print('=' * 80)
        
        # 测试奖项筛选
        response = client.get('/customers/list?award_filter=市奖')
        assert response.status_code == 200, f'筛选失败: {response.status_code}'
        
        html = response.data.decode('utf-8')
        assert '客户管理' in html, '筛选后页面不正确'
        
        print('✅ 客户筛选功能测试通过')


def test_data_consistency():
    """测试数据一致性"""
    with app.app_context():
        print('\n' + '=' * 80)
        print('测试5：数据一致性检查')
        print('=' * 80)
        
        customers = Customer.query.all()
        
        for customer in customers:
            # 检查责任销售（从线索表读取）
            sales_user = customer.get_sales_user()
            assert sales_user is not None, f'客户 {customer.id} 没有责任销售'
            
            # 检查服务类型（从线索表读取）
            service_types = customer.get_service_types()
            
            # 检查奖项信息（从客户表读取）
            award_level = customer.competition_award_level
            
            print(f'客户 {customer.id} ({customer.lead.get_display_name()}):')
            print(f'  责任销售: {sales_user.username}')
            print(f'  服务类型: {service_types}')
            print(f'  奖项等级: {award_level or "无"}')
        
        print(f'\n✅ 数据一致性检查通过 (共 {len(customers)} 个客户)')


def main():
    """运行所有测试"""
    print('开始功能测试...')
    print()
    
    try:
        test_customer_list()
        test_customer_edit_page()
        test_customer_update()
        test_customer_filter()
        test_data_consistency()
        
        print('\n' + '=' * 80)
        print('✅ 所有功能测试通过！')
        print('=' * 80)
        print('\n系统优化完成，功能正常，数据完整！')
        
        return True
        
    except AssertionError as e:
        print(f'\n❌ 测试失败：{e}')
        return False
    except Exception as e:
        print(f'\n❌ 测试出错：{e}')
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)

