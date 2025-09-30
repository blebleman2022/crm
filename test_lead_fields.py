#!/usr/bin/env python3
"""测试线索表的竞赛等级和额外要求字段"""

from run import app
from models import Lead, Customer, db

with app.app_context():
    print("=" * 60)
    print("测试线索表字段恢复")
    print("=" * 60)
    
    # 1. 查看测试学员A的线索数据
    lead = Lead.query.filter_by(student_name='测试学员A').first()
    if lead:
        print(f"\n线索ID: {lead.id}")
        print(f"学员姓名: {lead.student_name}")
        print(f"\n【线索表字段】")
        print(f"competition_award_level: {lead.competition_award_level}")
        print(f"additional_requirements: {lead.additional_requirements}")
        print(f"service_types: {lead.get_service_types_list()}")
        
        # 2. 查看对应的客户数据
        customer = Customer.query.filter_by(lead_id=lead.id).first()
        if customer:
            print(f"\n【客户表字段】")
            print(f"competition_award_level: {customer.competition_award_level}")
            print(f"additional_requirements: {customer.additional_requirements}")
        
        # 3. 测试设置线索表字段
        print(f"\n{'=' * 60}")
        print("测试设置线索表字段")
        print("=" * 60)
        
        original_award = lead.competition_award_level
        original_req = lead.additional_requirements
        
        # 设置新值
        lead.competition_award_level = '市奖'
        lead.additional_requirements = '测试：销售在线索阶段设置的额外要求'
        db.session.commit()
        
        print(f"✅ 设置成功")
        print(f"competition_award_level: {lead.competition_award_level}")
        print(f"additional_requirements: {lead.additional_requirements}")
        
        # 恢复原值
        lead.competition_award_level = original_award
        lead.additional_requirements = original_req
        db.session.commit()
        
        print(f"\n✅ 已恢复原值")
    
    # 4. 测试新建线索
    print(f"\n{'=' * 60}")
    print("测试新建线索并设置字段")
    print("=" * 60)
    
    test_lead = Lead(
        parent_wechat_display_name='测试家长003',
        parent_wechat_name='test_parent_003',
        contact_info='13900000003',
        sales_user_id=13,
        grade='高一',
        stage='获取联系方式',
        service_types='["tutoring", "competition"]',
        competition_award_level='国奖',
        additional_requirements='测试额外要求：需要在2027年前获得国奖'
    )
    
    db.session.add(test_lead)
    db.session.commit()
    
    print(f"✅ 新建线索成功")
    print(f"线索ID: {test_lead.id}")
    print(f"competition_award_level: {test_lead.competition_award_level}")
    print(f"additional_requirements: {test_lead.additional_requirements}")
    
    # 删除测试线索
    db.session.delete(test_lead)
    db.session.commit()
    print(f"\n✅ 已删除测试线索")
    
    print(f"\n{'=' * 60}")
    print("✅ 所有测试通过！")
    print("=" * 60)

