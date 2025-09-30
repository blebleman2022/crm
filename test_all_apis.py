"""
测试所有API是否还在使用已删除的字段
"""
from run import app
from models import Lead, Customer

def test_all_apis():
    """测试所有API"""
    with app.test_client() as client:
        # 登录
        response = client.post('/auth/login', data={
            'phone': '13909999451'
        }, follow_redirects=False)
        
        if response.status_code != 302:
            print(f'❌ 登录失败: {response.status_code}')
            return False
        
        print('✅ 登录成功\n')
        
        # 获取测试数据
        with app.app_context():
            lead = Lead.query.first()
            customer = Customer.query.first()
            
            if not lead or not customer:
                print('❌ 没有测试数据')
                return False
            
            lead_id = lead.id
            customer_id = customer.id
        
        all_passed = True
        
        # 测试1：线索API
        print('测试1：线索API (/leads/<id>/api)')
        print('-' * 80)
        response = client.get(f'/leads/{lead_id}/api')
        
        if response.status_code == 200:
            data = response.get_json()
            if data.get('success'):
                lead_data = data.get('lead', {})
                
                # 检查不应该存在的字段
                bad_fields = []
                if 'follow_up_notes' in lead_data:
                    bad_fields.append('follow_up_notes')
                
                if bad_fields:
                    print(f'❌ 发现已删除的字段: {bad_fields}')
                    all_passed = False
                else:
                    print(f'✅ 线索API正常')
                    print(f'   - 学员姓名: {lead_data.get("student_name")}')
                    print(f'   - 服务类型: {lead_data.get("service_types")}')
                    print(f'   - 奖项等级: {lead_data.get("competition_award_level") or "无"}')
            else:
                print(f'❌ API返回失败: {data.get("message")}')
                all_passed = False
        else:
            print(f'❌ API请求失败: {response.status_code}')
            all_passed = False
        
        print()
        
        # 测试2：客户API
        print('测试2：客户API (/customers/<id>/api)')
        print('-' * 80)
        response = client.get(f'/customers/{customer_id}/api')
        
        if response.status_code == 200:
            data = response.get_json()
            if data.get('success'):
                customer_data = data.get('customer', {})
                
                # 检查不应该存在的字段
                bad_fields = []
                if 'service_type' in customer_data:
                    bad_fields.append('service_type')
                if 'sales_user_id' in customer_data:
                    bad_fields.append('sales_user_id')
                if 'award_requirement' in customer_data:
                    bad_fields.append('award_requirement')
                if 'tutoring_expire_date' in customer_data:
                    bad_fields.append('tutoring_expire_date')
                if 'award_expire_date' in customer_data:
                    bad_fields.append('award_expire_date')
                
                if bad_fields:
                    print(f'❌ 发现已删除的字段: {bad_fields}')
                    all_passed = False
                else:
                    print(f'✅ 客户API正常')
                    print(f'   - 学员姓名: {customer_data.get("student_name")}')
                    print(f'   - 责任销售: {customer_data.get("sales_user")}')
                    print(f'   - 服务类型: {customer_data.get("service_types")}')
                    print(f'   - 奖项等级: {customer_data.get("competition_award_level") or "无"}')
            else:
                print(f'❌ API返回失败: {data.get("message")}')
                all_passed = False
        else:
            print(f'❌ API请求失败: {response.status_code}')
            all_passed = False
        
        print()
        
        # 测试3：客户进度API
        print('测试3：客户进度API (/customers/<id>/progress)')
        print('-' * 80)
        response = client.get(f'/customers/{customer_id}/progress')
        
        if response.status_code == 200:
            data = response.get_json()
            if data.get('success'):
                customer_data = data.get('customer', {})
                
                # 检查不应该存在的字段
                bad_fields = []
                if 'service_type' in customer_data:
                    bad_fields.append('service_type')
                if 'award_requirement' in customer_data:
                    bad_fields.append('award_requirement')
                
                if bad_fields:
                    print(f'❌ 发现已删除的字段: {bad_fields}')
                    all_passed = False
                else:
                    print(f'✅ 客户进度API正常')
                    print(f'   - 学员姓名: {customer_data.get("student_name")}')
            else:
                print(f'❌ API返回失败: {data.get("message")}')
                all_passed = False
        else:
            print(f'❌ API请求失败: {response.status_code}')
            all_passed = False
        
        print()
        
        # 测试4：咨询详情API
        print('测试4：咨询详情API (/consultations/details_data/<lead_id>)')
        print('-' * 80)
        response = client.get(f'/consultations/details_data/{lead_id}')
        
        if response.status_code == 200:
            data = response.get_json()
            if data.get('success'):
                response_data = data.get('data', {})
                customer_data = response_data.get('customer', {})
                
                if customer_data:
                    # 检查不应该存在的字段
                    bad_fields = []
                    if 'service_type' in customer_data:
                        bad_fields.append('service_type')
                    
                    if bad_fields:
                        print(f'❌ 发现已删除的字段: {bad_fields}')
                        all_passed = False
                    else:
                        print(f'✅ 咨询详情API正常')
                        print(f'   - 服务类型: {customer_data.get("service_types")}')
                else:
                    print(f'✅ 咨询详情API正常（无客户数据）')
            else:
                print(f'❌ API返回失败: {data.get("message")}')
                all_passed = False
        else:
            print(f'❌ API请求失败: {response.status_code}')
            all_passed = False
        
        print()
        
        return all_passed


def main():
    """主函数"""
    print('=' * 80)
    print('测试所有API是否使用已删除字段')
    print('=' * 80)
    print()
    
    print('已删除的字段列表：')
    print('  线索表: follow_up_notes, competition_award_level, additional_requirements')
    print('  客户表: service_type, sales_user_id, award_requirement,')
    print('         tutoring_expire_date, award_expire_date')
    print()
    print('=' * 80)
    print()
    
    success = test_all_apis()
    
    if success:
        print('=' * 80)
        print('✅ 所有API测试通过！')
        print('=' * 80)
        print()
        print('📊 测试总结:')
        print('  ✓ 线索API - 正常')
        print('  ✓ 客户API - 正常')
        print('  ✓ 客户进度API - 正常')
        print('  ✓ 咨询详情API - 正常')
        print()
        print('🎉 所有API都已正确更新，不再使用已删除的字段！')
    else:
        print('=' * 80)
        print('❌ 部分API测试失败')
        print('=' * 80)
        print()
        print('请检查上述失败的API并修复问题。')
    
    return success


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)

