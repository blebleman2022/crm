#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为家长微信 yiyi (季禹昆) 创建付款记录
"""

from models import db, Customer, CustomerPayment, Lead
from run import app

def add_payment_record():
    """为客户 ID 65 创建付款记录"""
    
    with app.app_context():
        # 查询客户信息
        customer = Customer.query.get(65)
        
        if not customer:
            print("❌ 未找到客户 ID 65")
            return
        
        # 查询线索信息
        lead = Lead.query.get(customer.lead_id)
        
        print("=" * 60)
        print("📋 客户信息")
        print("=" * 60)
        print(f"客户 ID: {customer.id}")
        print(f"学员姓名: {lead.student_name if lead else '未知'}")
        print(f"家长微信: {lead.parent_wechat_display_name if lead else '未知'}")
        print(f"负责班主任 ID: {customer.teacher_user_id}")
        print("")
        
        # 检查是否已有付款记录
        existing_payment = CustomerPayment.query.filter_by(customer_id=65).first()
        
        if existing_payment:
            print("⚠️  该客户已有付款记录:")
            print(f"   总金额: {existing_payment.total_amount}")
            print(f"   已付金额: {existing_payment.total_paid}")
            print("")
            
            confirm = input("是否要更新现有记录? (y/n): ")
            if confirm.lower() != 'y':
                print("❌ 操作已取消")
                return
            
            payment = existing_payment
        else:
            print("✅ 该客户没有付款记录,将创建新记录")
            print("")
            
            # 创建新的付款记录
            payment = CustomerPayment(
                customer_id=65,
                teacher_user_id=customer.teacher_user_id
            )
            db.session.add(payment)
        
        # 设置付款信息 (可以根据实际情况修改)
        print("请输入付款信息 (直接回车跳过):")
        print("")
        
        total_amount = input("总金额 (元): ").strip()
        if total_amount:
            payment.total_amount = float(total_amount)
        
        # 提交到数据库
        try:
            db.session.commit()
            print("")
            print("=" * 60)
            print("✅ 付款记录创建/更新成功!")
            print("=" * 60)
            print(f"客户 ID: {payment.customer_id}")
            print(f"总金额: {payment.total_amount}")
            print("")
            print("现在该客户应该可以在付款对账页面看到了!")
            print("")
        except Exception as e:
            db.session.rollback()
            print("")
            print("=" * 60)
            print("❌ 操作失败!")
            print("=" * 60)
            print(f"错误信息: {str(e)}")
            print("")

if __name__ == '__main__':
    add_payment_record()

