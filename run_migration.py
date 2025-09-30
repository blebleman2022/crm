from run import app
from models import db, Lead, Customer
from sqlalchemy import text

with app.app_context():
    print('开始数据库彻底优化迁移...')
    print('=' * 80)
    
    # 步骤1：备份数据
    print('\n步骤1：备份当前数据')
    print('-' * 80)
    
    leads = Lead.query.all()
    customers = Customer.query.all()
    
    print(f'当前有 {len(leads)} 条线索记录')
    print(f'当前有 {len(customers)} 条客户记录')
    
    # 步骤2：添加新字段
    print('\n步骤2：在客户表添加新字段')
    print('-' * 80)
    
    try:
        db.session.execute(text("ALTER TABLE customers ADD COLUMN competition_award_level VARCHAR(20)"))
        print('添加 customers.competition_award_level 字段')
    except Exception as e:
        if 'duplicate column' in str(e).lower():
            print('customers.competition_award_level 字段已存在')
        else:
            print(f'错误: {e}')
    
    try:
        db.session.execute(text("ALTER TABLE customers ADD COLUMN additional_requirements TEXT"))
        print('添加 customers.additional_requirements 字段')
    except Exception as e:
        if 'duplicate column' in str(e).lower():
            print('customers.additional_requirements 字段已存在')
        else:
            print(f'错误: {e}')
    
    db.session.commit()
    
    # 步骤3：迁移数据
    print('\n步骤3：迁移数据到客户表')
    print('-' * 80)
    
    db.session.execute(text("""
        UPDATE customers 
        SET competition_award_level = (
            SELECT competition_award_level 
            FROM leads 
            WHERE leads.id = customers.lead_id
        )
    """))
    print('迁移 competition_award_level 数据')
    
    db.session.execute(text("""
        UPDATE customers 
        SET additional_requirements = (
            SELECT additional_requirements 
            FROM leads 
            WHERE leads.id = customers.lead_id
        )
    """))
    print('迁移 additional_requirements 数据')
    
    db.session.commit()
    
    # 步骤4：验证
    print('\n步骤4：验证迁移结果')
    print('-' * 80)
    
    for customer in customers:
        result = db.session.execute(text(f"SELECT competition_award_level, additional_requirements FROM customers WHERE id = {customer.id}")).fetchone()
        req_text = result[1][:30] + '...' if result[1] and len(result[1]) > 30 else (result[1] or '无')
        print(f'客户 {customer.id} ({customer.lead.get_display_name()}): 奖项={result[0] or "无"}, 要求={req_text}')
    
    print('\n数据迁移完成！')

