"""
测试线索详情API
"""
from run import app
from models import Lead, Customer

def test_lead_api():
    """测试线索详情API"""
    with app.test_client() as client:
        # 登录
        response = client.post('/auth/login', data={
            'phone': '13909999451'
        }, follow_redirects=False)
        
        if response.status_code != 302:
            print(f'❌ 登录失败: {response.status_code}')
            return False
        
        print('✅ 登录成功')
        
        # 获取第一个线索
        with app.app_context():
            lead = Lead.query.first()
            if not lead:
                print('❌ 没有线索数据')
                return False
            
            lead_id = lead.id
            student_name = lead.student_name or lead.parent_wechat_display_name
            
            # 检查是否已转为客户
            customer = Customer.query.filter_by(lead_id=lead_id).first()
            
            print(f'\n测试线索: ID={lead_id}')
            print(f'学员姓名: {student_name}')
            print(f'是否已转客户: {"是" if customer else "否"}')
            
            if customer:
                print(f'客户ID: {customer.id}')
                print(f'奖项等级: {customer.competition_award_level or "无"}')
                print(f'额外要求: {customer.additional_requirements[:50] + "..." if customer.additional_requirements and len(customer.additional_requirements) > 50 else customer.additional_requirements or "无"}')
        
        # 测试API
        print(f'\n测试API: /leads/{lead_id}/api')
        response = client.get(f'/leads/{lead_id}/api')
        
        print(f'状态码: {response.status_code}')
        
        if response.status_code == 200:
            data = response.get_json()
            print(f'\n响应数据:')
            print(f'  success: {data.get("success")}')
            
            if data.get('success'):
                lead_data = data.get('lead', {})
                
                print(f'  学员姓名: {lead_data.get("student_name")}')
                print(f'  年级: {lead_data.get("grade")}')
                print(f'  服务类型: {lead_data.get("service_types")}')
                print(f'  奖项等级: {lead_data.get("competition_award_level") or "无"}')
                print(f'  额外要求: {lead_data.get("additional_requirements") or "无"}')
                
                print('\n✅ API测试通过')
                return True
            else:
                print(f'  message: {data.get("message")}')
                print('\n❌ API返回失败')
                return False
        else:
            print(f'\n❌ API请求失败: {response.status_code}')
            if response.data:
                try:
                    error_data = response.get_json()
                    print(f'错误信息: {error_data}')
                except:
                    print(f'响应内容: {response.data[:200]}')
            return False


if __name__ == '__main__':
    print('=' * 80)
    print('测试线索详情API')
    print('=' * 80)
    
    success = test_lead_api()
    
    if success:
        print('\n' + '=' * 80)
        print('✅ 所有测试通过')
        print('=' * 80)
    else:
        print('\n' + '=' * 80)
        print('❌ 测试失败')
        print('=' * 80)

