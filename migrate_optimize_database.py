"""
数据库彻底优化迁移脚本 - 方案B
1. 将线索表的 competition_award_level 和 additional_requirements 迁移到客户表
2. 备份所有数据
3. 验证数据完整性
"""
from run import app
from models import db, Lead, Customer
from sqlalchemy import text
import json
from datetime import datetime


def backup_data():
    """备份当前数据"""
    with app.app_context():
        print('=' * 80)
        print('步骤1：备份当前数据')
        print('=' * 80)
        
        # 备份线索数据
        leads = Lead.query.all()
        leads_backup = []
        for lead in leads:
            leads_backup.append({
                'id': lead.id,
                'student_name': lead.student_name,
                'competition_award_level': lead.competition_award_level,
                'additional_requirements': lead.additional_requirements,
                'service_types': lead.service_types
            })
        
        # 备份客户数据
        customers = Customer.query.all()
        customers_backup = []
        for customer in customers:
            customers_backup.append({
                'id': customer.id,
                'lead_id': customer.lead_id,
                'sales_user_id': customer.sales_user_id,
                'award_requirement': customer.award_requirement,
                'service_type': customer.service_type
            })
        
        print(f'✅ 备份了 {len(leads_backup)} 条线索记录')
        print(f'✅ 备份了 {len(customers_backup)} 条客户记录')
        
        # 保存备份到文件
        backup_file = f'backup_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump({
                'leads': leads_backup,
                'customers': customers_backup,
                'timestamp': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        
        print(f'✅ 备份文件已保存: {backup_file}')
        return leads_backup, customers_backup


def add_customer_fields():
    """在客户表添加新字段"""
    with app.app_context():
        print('\n' + '=' * 80)
        print('步骤2：在客户表添加新字段')
        print('=' * 80)
        
        try:
            # 添加 competition_award_level 字段
            db.session.execute(text(
                "ALTER TABLE customers ADD COLUMN competition_award_level VARCHAR(20)"
            ))
            print('✅ 添加 customers.competition_award_level 字段')
        except Exception as e:
            if 'duplicate column' in str(e).lower():
                print('✓  customers.competition_award_level 字段已存在')
            else:
                print(f'❌ 添加失败: {e}')
                return False
        
        try:
            # 添加 additional_requirements 字段
            db.session.execute(text(
                "ALTER TABLE customers ADD COLUMN additional_requirements TEXT"
            ))
            print('✅ 添加 customers.additional_requirements 字段')
        except Exception as e:
            if 'duplicate column' in str(e).lower():
                print('✓  customers.additional_requirements 字段已存在')
            else:
                print(f'❌ 添加失败: {e}')
                return False
        
        db.session.commit()
        return True


def migrate_data():
    """迁移数据"""
    with app.app_context():
        print('\n' + '=' * 80)
        print('步骤3：迁移数据到客户表')
        print('=' * 80)
        
        try:
            # 迁移 competition_award_level
            result = db.session.execute(text("""
                UPDATE customers 
                SET competition_award_level = (
                    SELECT competition_award_level 
                    FROM leads 
                    WHERE leads.id = customers.lead_id
                )
            """))
            print(f'✅ 迁移 competition_award_level 数据')
            
            # 迁移 additional_requirements
            result = db.session.execute(text("""
                UPDATE customers 
                SET additional_requirements = (
                    SELECT additional_requirements 
                    FROM leads 
                    WHERE leads.id = customers.lead_id
                )
            """))
            print(f'✅ 迁移 additional_requirements 数据')
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f'❌ 数据迁移失败: {e}')
            return False


def verify_migration():
    """验证迁移结果"""
    with app.app_context():
        print('\n' + '=' * 80)
        print('步骤4：验证迁移结果')
        print('=' * 80)
        
        customers = Customer.query.all()
        success_count = 0
        error_count = 0
        
        for customer in customers:
            lead = customer.lead
            
            # 验证 competition_award_level
            lead_award = lead.competition_award_level
            customer_award = db.session.execute(text(
                f"SELECT competition_award_level FROM customers WHERE id = {customer.id}"
            )).fetchone()[0]
            
            # 验证 additional_requirements
            lead_req = lead.additional_requirements
            customer_req = db.session.execute(text(
                f"SELECT additional_requirements FROM customers WHERE id = {customer.id}"
            )).fetchone()[0]
            
            if lead_award == customer_award and lead_req == customer_req:
                success_count += 1
            else:
                error_count += 1
                print(f'❌ 客户 {customer.id} 数据不一致')
                print(f'   线索奖项: {lead_award} vs 客户奖项: {customer_award}')
                print(f'   线索要求: {lead_req} vs 客户要求: {customer_req}')
        
        print(f'\n验证结果：')
        print(f'  ✅ 成功: {success_count} 条')
        print(f'  ❌ 失败: {error_count} 条')
        
        return error_count == 0


def show_summary():
    """显示数据摘要"""
    with app.app_context():
        print('\n' + '=' * 80)
        print('步骤5：数据摘要')
        print('=' * 80)
        
        # 显示客户数据示例
        customers = Customer.query.limit(5).all()
        
        print('\n前5个客户的数据：')
        for customer in customers:
            lead = customer.lead
            customer_award = db.session.execute(text(
                f"SELECT competition_award_level FROM customers WHERE id = {customer.id}"
            )).fetchone()[0]
            customer_req = db.session.execute(text(
                f"SELECT additional_requirements FROM customers WHERE id = {customer.id}"
            )).fetchone()[0]
            
            print(f'\n客户 {customer.id} ({lead.get_display_name()}):')
            print(f'  责任销售: {lead.sales_user.username}')
            print(f'  服务类型: {lead.get_service_types_list()}')
            print(f'  奖项等级: {customer_award or "无"}')
            print(f'  额外要求: {customer_req[:50] + "..." if customer_req and len(customer_req) > 50 else customer_req or "无"}')
            print(f'  中高考年份: {customer.exam_year}年')


def main():
    """主函数"""
    print('开始数据库彻底优化迁移...')
    print('方案B：彻底优化方案')
    print()
    
    # 步骤1：备份数据
    leads_backup, customers_backup = backup_data()
    
    # 步骤2：添加新字段
    if not add_customer_fields():
        print('\n❌ 添加字段失败，迁移终止')
        return False
    
    # 步骤3：迁移数据
    if not migrate_data():
        print('\n❌ 数据迁移失败，迁移终止')
        return False
    
    # 步骤4：验证迁移
    if not verify_migration():
        print('\n❌ 数据验证失败，请检查数据')
        return False
    
    # 步骤5：显示摘要
    show_summary()
    
    print('\n' + '=' * 80)
    print('✅ 数据迁移完成！')
    print('=' * 80)
    print('\n下一步：')
    print('1. 更新模型定义（models.py）')
    print('2. 更新业务代码（routes/*.py）')
    print('3. 更新模板文件（templates/**/*.html）')
    print('4. 运行完整测试')
    
    return True


if __name__ == '__main__':
    success = main()
    if not success:
        print('\n⚠️  迁移过程中出现错误，请检查日志')

