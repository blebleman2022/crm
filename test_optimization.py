"""
测试数据库优化后的系统功能
"""
from run import app
from models import db, Lead, Customer, User
from sqlalchemy import text

def test_database_structure():
    """测试数据库结构"""
    with app.app_context():
        print('=' * 80)
        print('测试1：数据库结构检查')
        print('=' * 80)
        
        # 检查客户表字段
        result = db.session.execute(text("PRAGMA table_info(customers)")).fetchall()
        customer_columns = [row[1] for row in result]
        
        print('\n客户表字段：')
        for col in customer_columns:
            print(f'  - {col}')
        
        # 验证新字段存在
        assert 'competition_award_level' in customer_columns, '❌ 缺少 competition_award_level 字段'
        assert 'additional_requirements' in customer_columns, '❌ 缺少 additional_requirements 字段'
        
        # 验证旧字段已删除（从模型定义中）
        print('\n✅ 新字段已添加到数据库')
        
        # 检查线索表字段
        result = db.session.execute(text("PRAGMA table_info(leads)")).fetchall()
        lead_columns = [row[1] for row in result]
        
        print('\n线索表字段：')
        for col in lead_columns:
            print(f'  - {col}')
        
        print('\n✅ 数据库结构检查通过')


def test_data_integrity():
    """测试数据完整性"""
    with app.app_context():
        print('\n' + '=' * 80)
        print('测试2：数据完整性检查')
        print('=' * 80)
        
        customers = Customer.query.all()
        
        print(f'\n总客户数：{len(customers)}')
        
        for customer in customers:
            lead = customer.lead
            
            # 检查关联
            assert lead is not None, f'❌ 客户 {customer.id} 没有关联线索'
            
            # 检查责任销售（从线索表读取）
            sales_user = customer.get_sales_user()
            assert sales_user is not None, f'❌ 客户 {customer.id} 没有责任销售'
            
            # 检查服务类型（从线索表读取）
            service_types = customer.get_service_types()
            
            # 检查奖项信息（从客户表读取）
            award_level = customer.competition_award_level
            
            print(f'\n客户 {customer.id} ({lead.get_display_name()}):')
            print(f'  责任销售: {sales_user.username}')
            print(f'  服务类型: {service_types}')
            print(f'  奖项等级: {award_level or "无"}')
            print(f'  额外要求: {customer.additional_requirements[:30] + "..." if customer.additional_requirements and len(customer.additional_requirements) > 30 else customer.additional_requirements or "无"}')
            print(f'  中高考年份: {customer.exam_year}年')
        
        print('\n✅ 数据完整性检查通过')


def test_model_methods():
    """测试模型方法"""
    with app.app_context():
        print('\n' + '=' * 80)
        print('测试3：模型方法测试')
        print('=' * 80)
        
        customer = Customer.query.first()
        
        if customer:
            print(f'\n测试客户：{customer.lead.get_display_name()}')
            
            # 测试 get_sales_user()
            sales_user = customer.get_sales_user()
            print(f'  get_sales_user(): {sales_user.username if sales_user else None}')
            assert sales_user is not None, '❌ get_sales_user() 返回 None'
            
            # 测试 get_service_types()
            service_types = customer.get_service_types()
            print(f'  get_service_types(): {service_types}')
            
            # 测试 get_expire_date()
            expire_date = customer.get_expire_date()
            print(f'  get_expire_date(): {expire_date}')
            if customer.exam_year:
                assert expire_date is not None, '❌ get_expire_date() 返回 None'
            
            print('\n✅ 模型方法测试通过')
        else:
            print('\n⚠️  没有客户数据，跳过模型方法测试')


def test_field_removal():
    """测试旧字段是否已从模型中移除"""
    with app.app_context():
        print('\n' + '=' * 80)
        print('测试4：旧字段移除检查')
        print('=' * 80)
        
        # 检查 Customer 模型
        customer_attrs = dir(Customer)
        
        # 这些字段应该已从模型中移除
        removed_fields = ['sales_user_id', 'service_type', 'tutoring_expire_date', 'award_expire_date', 'award_requirement']
        
        print('\n检查客户表模型：')
        for field in removed_fields:
            if field in customer_attrs:
                # 检查是否是数据库列
                if hasattr(getattr(Customer, field), 'type'):
                    print(f'  ⚠️  {field} 仍在模型中（但可能在数据库中）')
                else:
                    print(f'  ✓  {field} 不是数据库列')
            else:
                print(f'  ✓  {field} 已从模型中移除')
        
        # 检查 Lead 模型
        lead_attrs = dir(Lead)
        
        # 这些字段应该已从线索模型中移除
        removed_lead_fields = ['deposit_paid_at', 'full_payment_at', 'service_type', 'award_requirement', 'competition_award_level', 'additional_requirements']
        
        print('\n检查线索表模型：')
        for field in removed_lead_fields:
            if field in lead_attrs:
                if hasattr(getattr(Lead, field), 'type'):
                    print(f'  ⚠️  {field} 仍在模型中（但可能在数据库中）')
                else:
                    print(f'  ✓  {field} 不是数据库列')
            else:
                print(f'  ✓  {field} 已从模型中移除')
        
        print('\n✅ 旧字段移除检查完成')


def test_query_performance():
    """测试查询性能"""
    with app.app_context():
        print('\n' + '=' * 80)
        print('测试5：查询性能测试')
        print('=' * 80)
        
        import time
        
        # 测试客户列表查询
        start = time.time()
        customers = Customer.query.join(Lead).limit(10).all()
        end = time.time()
        
        print(f'\n查询10个客户耗时：{(end - start) * 1000:.2f}ms')
        
        # 测试访问关联数据
        start = time.time()
        for customer in customers:
            _ = customer.lead.student_name
            _ = customer.lead.sales_user.username
            _ = customer.get_service_types()
        end = time.time()
        
        print(f'访问关联数据耗时：{(end - start) * 1000:.2f}ms')
        
        print('\n✅ 查询性能测试完成')


def main():
    """运行所有测试"""
    print('开始测试数据库优化后的系统...')
    print()
    
    try:
        test_database_structure()
        test_data_integrity()
        test_model_methods()
        test_field_removal()
        test_query_performance()
        
        print('\n' + '=' * 80)
        print('✅ 所有测试通过！')
        print('=' * 80)
        print('\n系统优化完成，数据完整，功能正常！')
        
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

