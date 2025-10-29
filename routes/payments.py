#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
客户付款管理路由

功能说明：
1. 销售管理和班主任对账页面（只读视图）- /payments/reconciliation
2. 班主任付款管理页面（编辑视图）- /payments/manage

权限控制：
- reconciliation: 销售管理和班主任可访问
- manage: 仅班主任可访问，且只能管理自己负责的客户
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Customer, CustomerPayment, User, Lead
from functools import wraps
from datetime import datetime
from decimal import Decimal

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

# 权限装饰器
def sales_manager_or_teacher_supervisor_required(f):
    """要求销售管理或班主任角色"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not (current_user.is_sales_manager() or current_user.is_teacher_supervisor()):
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def teacher_supervisor_required(f):
    """要求班主任角色"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_teacher_supervisor():
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@payments_bp.route('/reconciliation')
@login_required
@sales_manager_or_teacher_supervisor_required
def reconciliation():
    """销售管理和班主任对账页面（只读视图）"""

    # 获取筛选参数
    teacher_user_id = request.args.get('teacher_user_id', type=int)
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    # 构建查询
    query = db.session.query(
        Customer, CustomerPayment, Lead, User
    ).join(
        Lead, Customer.lead_id == Lead.id
    ).outerjoin(
        CustomerPayment, Customer.id == CustomerPayment.customer_id
    ).outerjoin(
        User, Customer.teacher_user_id == User.id
    )

    # 如果是班主任，只显示自己负责的客户
    if current_user.is_teacher_supervisor():
        query = query.filter(Customer.teacher_user_id == current_user.id)
    # 如果是销售管理，可以按班主任筛选
    elif teacher_user_id:
        query = query.filter(Customer.teacher_user_id == teacher_user_id)

    # 执行查询
    results = query.all()

    # 组织数据
    payment_data = []
    for customer, payment, lead, teacher_user in results:
        # 获取服务类型
        service_types = lead.get_service_types_list() if lead else []
        has_tutoring = 'tutoring' in service_types
        has_competition = 'competition' in service_types
        
        # 计算已付款和剩余付款
        if payment:
            total_paid = payment.get_total_paid()
            remaining = payment.get_remaining()
        else:
            total_paid = 0
            remaining = float(customer.payment_amount) if customer.payment_amount else 0
        
        # 总金额从customer_payments.total_amount获取（公司应付给供应商的金额）
        total_amount = float(payment.total_amount) if payment and payment.total_amount else 0

        # 时间筛选：检查是否有任何一笔付款在时间范围内
        if start_date or end_date:
            payment_dates = []
            if payment:
                if payment.first_payment_date:
                    payment_dates.append(payment.first_payment_date.strftime('%Y-%m'))
                if payment.second_payment_date:
                    payment_dates.append(payment.second_payment_date.strftime('%Y-%m'))
                if payment.third_payment_date:
                    payment_dates.append(payment.third_payment_date.strftime('%Y-%m'))

            # 如果没有付款记录，跳过
            if not payment_dates:
                continue

            # 检查是否有付款在时间范围内
            in_range = False
            for payment_date in payment_dates:
                if start_date and end_date:
                    if start_date <= payment_date <= end_date:
                        in_range = True
                        break
                elif start_date:
                    if payment_date >= start_date:
                        in_range = True
                        break
                elif end_date:
                    if payment_date <= end_date:
                        in_range = True
                        break

            if not in_range:
                continue

        payment_data.append({
            'customer_id': customer.id,
            'student_name': lead.student_name if lead else '',
            'parent_wechat_name': lead.parent_wechat_display_name if lead else '',
            'has_tutoring': '是' if has_tutoring else '否',
            'has_competition': '是' if has_competition else '否',
            'award_level': customer.competition_award_level or '无',
            'total_amount': total_amount,
            'first_payment': float(payment.first_payment) if payment and payment.first_payment else 0,
            'first_payment_date': payment.first_payment_date.strftime('%Y-%m') if payment and payment.first_payment_date else '',
            'second_payment': float(payment.second_payment) if payment and payment.second_payment else 0,
            'second_payment_date': payment.second_payment_date.strftime('%Y-%m') if payment and payment.second_payment_date else '',
            'third_payment': float(payment.third_payment) if payment and payment.third_payment else 0,
            'third_payment_date': payment.third_payment_date.strftime('%Y-%m') if payment and payment.third_payment_date else '',
            'total_paid': total_paid,
            'remaining': remaining,
            'teacher_user_name': teacher_user.username if teacher_user else '未分配'
        })

    # 获取所有班主任（用于筛选）
    teacher_supervisors = User.query.filter_by(role='teacher_supervisor', status=True).all()

    return render_template('payments/reconciliation.html',
                         payment_data=payment_data,
                         teacher_supervisors=teacher_supervisors,
                         selected_teacher_id=teacher_user_id,
                         start_date=start_date,
                         end_date=end_date)


@payments_bp.route('/manage')
@login_required
@teacher_supervisor_required
def manage():
    """班主任付款管理页面（编辑视图）"""

    # 获取筛选参数
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    # 只查询当前班主任负责的客户
    query = db.session.query(
        Customer, CustomerPayment, Lead
    ).join(
        Lead, Customer.lead_id == Lead.id
    ).outerjoin(
        CustomerPayment, Customer.id == CustomerPayment.customer_id
    ).filter(
        Customer.teacher_user_id == current_user.id
    )

    results = query.all()

    # 组织数据
    payment_data = []
    for customer, payment, lead in results:
        # 获取服务类型
        service_types = lead.get_service_types_list() if lead else []
        has_tutoring = 'tutoring' in service_types
        has_competition = 'competition' in service_types
        
        # 如果没有付款记录，创建一个空的
        if not payment:
            payment = CustomerPayment(
                customer_id=customer.id,
                teacher_user_id=current_user.id,
                total_amount=None  # 总金额需要手动设置
            )

        # 总金额从customer_payments.total_amount获取（公司应付给供应商的金额）
        total_amount = float(payment.total_amount) if payment.total_amount else 0

        # 时间筛选：检查是否有任何一笔付款在时间范围内
        if start_date or end_date:
            payment_dates = []
            if payment.first_payment_date:
                payment_dates.append(payment.first_payment_date.strftime('%Y-%m'))
            if payment.second_payment_date:
                payment_dates.append(payment.second_payment_date.strftime('%Y-%m'))
            if payment.third_payment_date:
                payment_dates.append(payment.third_payment_date.strftime('%Y-%m'))

            # 如果没有付款记录，跳过
            if not payment_dates:
                continue

            # 检查是否有付款在时间范围内
            in_range = False
            for payment_date in payment_dates:
                if start_date and end_date:
                    if start_date <= payment_date <= end_date:
                        in_range = True
                        break
                elif start_date:
                    if payment_date >= start_date:
                        in_range = True
                        break
                elif end_date:
                    if payment_date <= end_date:
                        in_range = True
                        break

            if not in_range:
                continue

        payment_data.append({
            'customer_id': customer.id,
            'payment_id': payment.id if payment.id else None,
            'student_name': lead.student_name if lead else '',
            'parent_wechat_name': lead.parent_wechat_display_name if lead else '',
            'has_tutoring': '是' if has_tutoring else '否',
            'has_competition': '是' if has_competition else '否',
            'award_level': customer.competition_award_level or '无',
            'total_amount': total_amount,
            'first_payment': float(payment.first_payment) if payment.first_payment else 0,
            'first_payment_date': payment.first_payment_date.strftime('%Y-%m') if payment.first_payment_date else '',
            'second_payment': float(payment.second_payment) if payment.second_payment else 0,
            'second_payment_date': payment.second_payment_date.strftime('%Y-%m') if payment.second_payment_date else '',
            'third_payment': float(payment.third_payment) if payment.third_payment else 0,
            'third_payment_date': payment.third_payment_date.strftime('%Y-%m') if payment.third_payment_date else '',
            'total_paid': payment.get_total_paid() if hasattr(payment, 'get_total_paid') else 0,
            'remaining': payment.get_remaining() if hasattr(payment, 'get_remaining') else 0
        })

    return render_template('payments/manage.html',
                         payment_data=payment_data,
                         start_date=start_date,
                         end_date=end_date)


@payments_bp.route('/update/<int:customer_id>', methods=['POST'])
@login_required
@teacher_supervisor_required
def update_payment(customer_id):
    """更新客户付款信息"""
    
    # 验证权限：只能更新自己负责的客户
    customer = Customer.query.get_or_404(customer_id)
    if customer.teacher_user_id != current_user.id:
        return jsonify({'success': False, 'message': '您只能编辑自己负责的客户付款信息'}), 403
    
    # 获取或创建付款记录
    payment = CustomerPayment.query.filter_by(customer_id=customer_id).first()
    if not payment:
        payment = CustomerPayment(
            customer_id=customer_id,
            teacher_user_id=current_user.id
        )
        db.session.add(payment)
    
    try:
        # 更新字段
        data = request.get_json()
        
        # 总金额
        if 'total_amount' in data:
            payment.total_amount = Decimal(str(data['total_amount'])) if data['total_amount'] else None
        
        # 第一笔付款
        if 'first_payment' in data:
            payment.first_payment = Decimal(str(data['first_payment'])) if data['first_payment'] else None
        if 'first_payment_date' in data:
            if data['first_payment_date']:
                # 支持年-月格式，转换为该月的第一天
                payment.first_payment_date = datetime.strptime(data['first_payment_date'] + '-01', '%Y-%m-%d').date()
            else:
                payment.first_payment_date = None

        # 第二笔付款
        if 'second_payment' in data:
            payment.second_payment = Decimal(str(data['second_payment'])) if data['second_payment'] else None
        if 'second_payment_date' in data:
            if data['second_payment_date']:
                # 支持年-月格式，转换为该月的第一天
                payment.second_payment_date = datetime.strptime(data['second_payment_date'] + '-01', '%Y-%m-%d').date()
            else:
                payment.second_payment_date = None

        # 第三笔付款
        if 'third_payment' in data:
            payment.third_payment = Decimal(str(data['third_payment'])) if data['third_payment'] else None
        if 'third_payment_date' in data:
            if data['third_payment_date']:
                # 支持年-月格式，转换为该月的第一天
                payment.third_payment_date = datetime.strptime(data['third_payment_date'] + '-01', '%Y-%m-%d').date()
            else:
                payment.third_payment_date = None
        
        # 验证：已付款总额不能超过总金额
        total_paid = payment.get_total_paid()
        if payment.total_amount and total_paid > float(payment.total_amount):
            return jsonify({
                'success': False,
                'message': f'已付款总额（¥{total_paid:,.0f}）不能超过总金额（¥{float(payment.total_amount):,.0f}）'
            }), 400
        
        payment.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '付款信息更新成功',
            'data': {
                'total_paid': total_paid,
                'remaining': payment.get_remaining()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'}), 500

