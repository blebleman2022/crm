#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复测试数据质量问题
为标记为"全款支付"的测试学员添加相应的付款记录
"""

from run import create_app
from models import db, Lead, Payment, User
from datetime import datetime, timedelta
from decimal import Decimal

app = create_app('development')

with app.app_context():
    print('=== 开始修复测试数据 ===\n')
    
    # 查找所有标记为"全款支付"但没有付款记录的测试学员
    leads = Lead.query.filter(
        Lead.student_name.like('测试学员%'),
        Lead.stage == '全款支付'
    ).all()
    
    print(f'找到 {len(leads)} 个需要修复的测试学员\n')
    
    for lead in leads:
        print(f'处理: {lead.student_name}')
        
        # 检查是否已有付款记录
        existing_payments = Payment.query.filter_by(lead_id=lead.id).count()
        if existing_payments > 0:
            print(f'  ⚠️  已有 {existing_payments} 条付款记录，跳过')
            continue
        
        # 获取合同金额
        contract_amount = lead.contract_amount or Decimal('50000.00')
        
        # 创建三笔付款记录（首笔、次笔、全款）
        # 首笔支付：30%
        first_payment_amount = contract_amount * Decimal('0.3')
        first_payment = Payment(
            lead_id=lead.id,
            amount=first_payment_amount,
            payment_date=lead.created_at.date() if lead.created_at else datetime.now().date(),
            payment_type='首笔支付',
            notes='测试数据 - 首笔支付'
        )
        db.session.add(first_payment)
        print(f'  ✅ 添加首笔支付: ¥{first_payment_amount}')
        
        # 次笔支付：30%
        second_payment_amount = contract_amount * Decimal('0.3')
        second_payment_date = (lead.created_at + timedelta(days=30)).date() if lead.created_at else (datetime.now() + timedelta(days=30)).date()
        second_payment = Payment(
            lead_id=lead.id,
            amount=second_payment_amount,
            payment_date=second_payment_date,
            payment_type='次笔支付',
            notes='测试数据 - 次笔支付'
        )
        db.session.add(second_payment)
        print(f'  ✅ 添加次笔支付: ¥{second_payment_amount}')
        
        # 全款支付：剩余40%
        final_payment_amount = contract_amount - first_payment_amount - second_payment_amount
        final_payment_date = (lead.created_at + timedelta(days=60)).date() if lead.created_at else (datetime.now() + timedelta(days=60)).date()
        final_payment = Payment(
            lead_id=lead.id,
            amount=final_payment_amount,
            payment_date=final_payment_date,
            payment_type='全款支付',
            notes='测试数据 - 全款支付'
        )
        db.session.add(final_payment)
        print(f'  ✅ 添加全款支付: ¥{final_payment_amount}')
        
        total = first_payment_amount + second_payment_amount + final_payment_amount
        print(f'  📊 总计: ¥{total} (合同金额: ¥{contract_amount})')
        print()
    
    # 提交更改
    try:
        db.session.commit()
        print('✅ 所有更改已保存到数据库')
    except Exception as e:
        db.session.rollback()
        print(f'❌ 保存失败: {str(e)}')
        raise
    
    print('\n=== 修复完成，验证数据 ===\n')
    
    # 验证修复结果
    for lead in leads:
        payments = Payment.query.filter_by(lead_id=lead.id).all()
        paid_amount = sum(p.amount for p in payments)
        status = "✅ 一致" if paid_amount >= lead.contract_amount else "❌ 不一致"
        print(f'{lead.student_name}:')
        print(f'  付款记录: {len(payments)}条')
        print(f'  已付款: ¥{paid_amount}')
        print(f'  合同金额: ¥{lead.contract_amount}')
        print(f'  状态: {status}')
        print()

