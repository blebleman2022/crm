"""
测试沟通记录API
"""
from run import app
from models import Customer
from communication_utils import CommunicationManager

def test_api():
    """测试沟通记录API"""
    with app.test_client() as client:
        # 登录
        response = client.post('/auth/login', data={
            'phone': '13909999451'
        }, follow_redirects=False)
        
        if response.status_code != 302:
            print(f'❌ 登录失败: {response.status_code}')
            return False
        
        print('✅ 登录成功')
        
        # 获取第一个客户
        with app.app_context():
            customer = Customer.query.first()
            if not customer:
                print('❌ 没有客户数据')
                return False
            
            lead_id = customer.lead_id
            customer_id = customer.id
            print(f'\n测试客户: ID={customer_id}, 线索ID={lead_id}')
            print(f'学员姓名: {customer.lead.student_name}')
        
        # 测试API
        print(f'\n测试API: /consultations/details_data/{lead_id}?customer_only=true')
        response = client.get(f'/consultations/details_data/{lead_id}?customer_only=true')
        
        print(f'状态码: {response.status_code}')
        
        if response.status_code == 200:
            data = response.get_json()
            print(f'\n响应数据:')
            print(f'  success: {data.get("success")}')
            
            if data.get('success'):
                comm_data = data.get('data', {})
                records = comm_data.get('communication_records', [])
                stats = comm_data.get('stats', {})
                
                print(f'  沟通记录数: {len(records)}')
                print(f'  统计信息:')
                print(f'    总记录数: {stats.get("total_count", 0)}')
                print(f'    线索阶段: {stats.get("lead_stage_count", 0)}')
                print(f'    客户阶段: {stats.get("customer_stage_count", 0)}')
                
                if records:
                    print(f'\n  前3条记录:')
                    for i, record in enumerate(records[:3], 1):
                        print(f'    {i}. [{record.get("stage")}] {record.get("content")[:50]}...')
                
                print('\n✅ API测试通过')
                return True
            else:
                print(f'  message: {data.get("message")}')
                print('\n❌ API返回失败')
                return False
        else:
            print(f'\n❌ API请求失败: {response.status_code}')
            print(f'响应内容: {response.data[:200]}')
            return False


if __name__ == '__main__':
    print('=' * 80)
    print('测试沟通记录API')
    print('=' * 80)
    
    success = test_api()
    
    if success:
        print('\n' + '=' * 80)
        print('✅ 所有测试通过')
        print('=' * 80)
    else:
        print('\n' + '=' * 80)
        print('❌ 测试失败')
        print('=' * 80)

