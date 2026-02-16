#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
客户付款管理路由

功能说明：
1. 销售管理和班主任主管对账页面（只读视图）- /payments/reconciliation
2. 班主任主管付款管理页面（编辑视图）- /payments/manage

权限控制：
- reconciliation: 销售管理和班主任主管可访问
- manage: 仅班主任主管可访问，且可管理自己及旗下普通班主任负责的客户
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Customer, CustomerPayment, User, Lead, SystemConfig
from functools import wraps
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')
PUBLIC_SCOPE = Lead.SCOPE_PUBLIC
PRIVATE_SCOPE = Lead.SCOPE_PRIVATE


def is_private_owner_user(user):
    """是否为私域负责人账号（销售管理）"""
    return bool(getattr(user, 'is_private_owner', False) and user.is_sales_manager())


def resolve_reconciliation_scope(requested_scope):
    """解析对账scope"""
    requested_scope = (requested_scope or '').strip().lower()
    if current_user.is_teacher_supervisor():
        return requested_scope if requested_scope in [PUBLIC_SCOPE, PRIVATE_SCOPE] else PUBLIC_SCOPE
    if current_user.is_sales_manager():
        return PRIVATE_SCOPE if is_private_owner_user(current_user) else PUBLIC_SCOPE
    return PUBLIC_SCOPE


def resolve_manage_scope(requested_scope):
    """解析付款管理scope（仅班主任）"""
    requested_scope = (requested_scope or '').strip().lower()
    if current_user.is_private_only_teacher_supervisor():
        return PRIVATE_SCOPE
    return requested_scope if requested_scope in [PUBLIC_SCOPE, PRIVATE_SCOPE] else PUBLIC_SCOPE


def get_visible_teacher_supervisor_ids():
    """当前班主任可见的数据归属班主任ID集合（主管=自己+旗下普通班主任）"""
    if not current_user.is_teacher_supervisor():
        return []

    cached_ids = getattr(current_user, '_visible_teacher_supervisor_ids_cache', None)
    if cached_ids is not None:
        return cached_ids

    visible_ids = current_user.get_visible_teacher_supervisor_ids()
    if current_user.id not in visible_ids:
        visible_ids.append(current_user.id)

    current_user._visible_teacher_supervisor_ids_cache = visible_ids
    return visible_ids

# 权限装饰器
def sales_manager_or_teacher_supervisor_required(f):
    """要求销售管理或班主任主管角色"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not (current_user.is_sales_manager() or current_user.is_teacher_supervisor_manager()):
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def teacher_supervisor_required(f):
    """要求班主任主管角色"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_teacher_supervisor_manager():
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def sales_manager_required(f):
    """要求销售管理角色"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_sales_manager():
            return jsonify({'success': False, 'message': '您没有权限执行此操作'}), 403
        return f(*args, **kwargs)
    return decorated_function


@payments_bp.route('/reconciliation')
@login_required
@sales_manager_or_teacher_supervisor_required
def reconciliation():
    """销售管理和班主任主管对账页面（只读视图）"""

    # 获取筛选参数
    selected_supervisor_id = request.args.get('supervisor_user_id', type=int)
    search = request.args.get('search', '', type=str)
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    active_tab = request.args.get('tab', 'summary')
    scope_filter = resolve_reconciliation_scope(request.args.get('scope', '', type=str))
    can_switch_scope = False
    show_scope_switch = False
    selected_private_owner_id = None
    private_owner_options = []
    show_teacher_switch = False
    teacher_switch_options = []
    scope_expr = func.coalesce(CustomerPayment.scope_snapshot, Customer.customer_scope, PUBLIC_SCOPE)

    if current_user.is_teacher_supervisor():
        visible_teacher_ids = get_visible_teacher_supervisor_ids()
        assigned_scope_rows = db.session.query(
            scope_expr.label('effective_scope'),
            Customer.private_owner_id.label('private_owner_id')
        ).outerjoin(
            CustomerPayment, Customer.id == CustomerPayment.customer_id
        ).filter(
            Customer.supervisor_user_id.in_(visible_teacher_ids)
        ).all()

        has_public_customers = any(row.effective_scope == PUBLIC_SCOPE for row in assigned_scope_rows)
        has_private_customers = any(row.effective_scope == PRIVATE_SCOPE for row in assigned_scope_rows)
        private_owner_ids = sorted({
            row.private_owner_id for row in assigned_scope_rows
            if row.effective_scope == PRIVATE_SCOPE and row.private_owner_id
        })

        # 仅“同时服务公域+私域”的班主任显示切换按钮，并按私域销售人维度切换
        if has_public_customers and private_owner_ids:
            show_scope_switch = True
            requested_scope = (request.args.get('scope', '', type=str) or '').strip().lower()
            requested_private_owner_id = request.args.get('private_owner_id', type=int)
            if requested_scope == PRIVATE_SCOPE and requested_private_owner_id in private_owner_ids:
                scope_filter = PRIVATE_SCOPE
                selected_private_owner_id = requested_private_owner_id
            else:
                scope_filter = PUBLIC_SCOPE
                selected_private_owner_id = None
            private_owner_options = User.query.filter(
                User.id.in_(private_owner_ids)
            ).order_by(User.username.asc()).all()
        elif has_private_customers and not has_public_customers:
            scope_filter = PRIVATE_SCOPE
        else:
            scope_filter = PUBLIC_SCOPE

    # 销售端班主任切换：按当前可见数据范围生成按钮，仅多于1位班主任时显示
    if current_user.is_sales_manager():
        teacher_scope_query = db.session.query(
            Customer.supervisor_user_id.label('supervisor_user_id')
        ).outerjoin(
            CustomerPayment, Customer.id == CustomerPayment.customer_id
        ).filter(
            scope_expr == scope_filter
        )

        if is_private_owner_user(current_user):
            teacher_scope_query = teacher_scope_query.filter(Customer.private_owner_id == current_user.id)

        teacher_ids = sorted({
            row.supervisor_user_id for row in teacher_scope_query.all()
            if row.supervisor_user_id
        })

        if teacher_ids:
            teacher_switch_options = User.query.filter(
                User.id.in_(teacher_ids),
                User.role == 'teacher_supervisor'
            ).order_by(User.username.asc()).all()

        valid_teacher_ids = {teacher.id for teacher in teacher_switch_options}
        if selected_supervisor_id and selected_supervisor_id not in valid_teacher_ids:
            selected_supervisor_id = None

        show_teacher_switch = len(teacher_switch_options) > 1

    def parse_month(value):
        return datetime.strptime(value, '%Y-%m')

    def month_start(dt_value):
        return datetime(dt_value.year, dt_value.month, 1)

    def add_month(dt_value, months=1):
        month = dt_value.month - 1 + months
        year = dt_value.year + month // 12
        month = month % 12 + 1
        return datetime(year, month, 1)

    def build_month_columns(start_value, end_value, earliest_payment):
        now = datetime.now()
        max_future = add_month(month_start(now), 1)

        if not start_value and not end_value:
            start_dt = earliest_payment or month_start(now)
            end_dt = max_future
        else:
            start_dt = parse_month(start_value) if start_value else parse_month(end_value)
            end_dt = parse_month(end_value) if end_value else start_dt

        if start_dt > max_future:
            start_dt = max_future
        if end_dt > max_future:
            end_dt = max_future

        if start_dt > end_dt:
            end_dt = start_dt

        columns = []
        current = month_start(start_dt)
        end_marker = (end_dt.year, end_dt.month)
        while (current.year, current.month) <= end_marker:
            columns.append({
                'key': current.strftime('%Y-%m'),
                'label': f'{current.year}年{current.month}月'
            })
            current = add_month(current, 1)
        return columns

    earliest_payment_month = None

    # 构建查询
    query = db.session.query(
        Customer, CustomerPayment, Lead, User
    ).join(
        Lead, Customer.lead_id == Lead.id
    ).outerjoin(
        CustomerPayment, Customer.id == CustomerPayment.customer_id
    ).outerjoin(
        User, Customer.supervisor_user_id == User.id
    )

    # 对账按scope硬隔离（付款记录优先读快照，无记录则回退客户当前scope）
    query = query.filter(scope_expr == scope_filter)

    # 如果是班主任，只显示自己负责的客户
    if current_user.is_teacher_supervisor():
        query = query.filter(Customer.supervisor_user_id.in_(get_visible_teacher_supervisor_ids()))
        if selected_private_owner_id:
            query = query.filter(Customer.private_owner_id == selected_private_owner_id)
    # 如果是销售管理，可以按班主任筛选
    elif selected_supervisor_id:
        query = query.filter(Customer.supervisor_user_id == selected_supervisor_id)

    # 私域负责人仅看自己名下私域
    if is_private_owner_user(current_user):
        query = query.filter(Customer.private_owner_id == current_user.id)

    # 搜索过滤
    if search:
        query = query.filter(
            (Lead.student_name.contains(search)) |
            (Lead.parent_wechat_display_name.contains(search)) |
            (Lead.parent_wechat_name.contains(search))
        )

    # 执行查询
    results = query.all()

    for customer, payment, lead, teacher_user in results:
        if payment:
            for date_value in [payment.first_payment_date, payment.second_payment_date, payment.third_payment_date]:
                if date_value:
                    current_month = month_start(date_value)
                    if earliest_payment_month is None or current_month < earliest_payment_month:
                        earliest_payment_month = current_month

    month_columns = build_month_columns(start_date, end_date, earliest_payment_month)
    month_keys = [item['key'] for item in month_columns]
    month_totals = {key: 0 for key in month_keys}

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

        # 时间筛选：检查是否有任何一笔付款在时间范围内，并计算时间段内的付款总额
        period_paid = 0  # 筛选时间段内的付款总额
        if start_date or end_date:
            payment_dates = []
            if payment:
                # 检查第一笔付款
                if payment.first_payment_date:
                    date_str = payment.first_payment_date.strftime('%Y-%m')
                    payment_dates.append(date_str)
                    # 检查是否在时间范围内
                    if start_date and end_date:
                        if start_date <= date_str <= end_date:
                            period_paid += float(payment.first_payment) if payment.first_payment else 0
                    elif start_date:
                        if date_str >= start_date:
                            period_paid += float(payment.first_payment) if payment.first_payment else 0
                    elif end_date:
                        if date_str <= end_date:
                            period_paid += float(payment.first_payment) if payment.first_payment else 0

                # 检查第二笔付款
                if payment.second_payment_date:
                    date_str = payment.second_payment_date.strftime('%Y-%m')
                    payment_dates.append(date_str)
                    if start_date and end_date:
                        if start_date <= date_str <= end_date:
                            period_paid += float(payment.second_payment) if payment.second_payment else 0
                    elif start_date:
                        if date_str >= start_date:
                            period_paid += float(payment.second_payment) if payment.second_payment else 0
                    elif end_date:
                        if date_str <= end_date:
                            period_paid += float(payment.second_payment) if payment.second_payment else 0

                # 检查第三笔付款
                if payment.third_payment_date:
                    date_str = payment.third_payment_date.strftime('%Y-%m')
                    payment_dates.append(date_str)
                    if start_date and end_date:
                        if start_date <= date_str <= end_date:
                            period_paid += float(payment.third_payment) if payment.third_payment else 0
                    elif start_date:
                        if date_str >= start_date:
                            period_paid += float(payment.third_payment) if payment.third_payment else 0
                    elif end_date:
                        if date_str <= end_date:
                            period_paid += float(payment.third_payment) if payment.third_payment else 0

            # 如果有时间筛选但没有付款记录，跳过
            if not payment_dates:
                # 如果没有付款记录但有付款对象(payment存在),仍然显示
                # 这样可以显示已创建但还没有付款日期的记录
                if not payment:
                    continue

            # 检查是否有付款在时间范围内
            if payment_dates:  # 只有当有付款日期时才检查范围
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

        monthly_paid = {key: 0 for key in month_keys}
        if payment:
            if payment.first_payment_date:
                month_key = payment.first_payment_date.strftime('%Y-%m')
                if month_key in monthly_paid:
                    monthly_paid[month_key] += float(payment.first_payment) if payment.first_payment else 0
            if payment.second_payment_date:
                month_key = payment.second_payment_date.strftime('%Y-%m')
                if month_key in monthly_paid:
                    monthly_paid[month_key] += float(payment.second_payment) if payment.second_payment else 0
            if payment.third_payment_date:
                month_key = payment.third_payment_date.strftime('%Y-%m')
                if month_key in monthly_paid:
                    monthly_paid[month_key] += float(payment.third_payment) if payment.third_payment else 0

        for key, value in monthly_paid.items():
            month_totals[key] += value

        payment_data.append({
            'customer_id': customer.id,
            'customer_scope': customer.customer_scope or PUBLIC_SCOPE,
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
            'period_paid': period_paid,  # 筛选时间段内的付款总额
            'monthly_paid': monthly_paid,
            'teacher_user_name': teacher_user.username if teacher_user else '未分配'
        })

    totals = {
        'total_amount': sum(item['total_amount'] for item in payment_data),
        'first_payment': sum(item['first_payment'] for item in payment_data),
        'second_payment': sum(item['second_payment'] for item in payment_data),
        'third_payment': sum(item['third_payment'] for item in payment_data),
        'total_paid': sum(item['total_paid'] for item in payment_data),
        'remaining': sum(item['remaining'] for item in payment_data)
    }

    detail_totals = {
        'total_amount': sum(item['total_amount'] for item in payment_data),
        'total_paid': sum(item['total_paid'] for item in payment_data),
        'remaining': sum(item['remaining'] for item in payment_data)
    }

    return render_template('payments/reconciliation.html',
                         payment_data=payment_data,
                         totals=totals,
                         detail_totals=detail_totals,
                         month_columns=month_columns,
                         detail_month_totals=month_totals,
                         teacher_switch_options=teacher_switch_options,
                         show_teacher_switch=show_teacher_switch,
                         selected_supervisor_id=selected_supervisor_id,
                         show_scope_switch=show_scope_switch,
                         private_owner_options=private_owner_options,
                         selected_private_owner_id=selected_private_owner_id,
                         search=search,
                         start_date=start_date,
                         end_date=end_date,
                         scope_filter=scope_filter,
                         can_switch_scope=can_switch_scope,
                         active_tab=active_tab)


@payments_bp.route('/manage')
@login_required
@teacher_supervisor_required
def manage():
    """班主任主管付款管理页面（编辑视图）"""

    # 获取筛选参数
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    scope_filter = resolve_manage_scope(request.args.get('scope', '', type=str))
    can_switch_scope = False
    show_scope_switch = False
    selected_private_owner_id = None
    private_owner_options = []

    scope_expr = func.coalesce(CustomerPayment.scope_snapshot, Customer.customer_scope, PUBLIC_SCOPE)
    visible_teacher_ids = get_visible_teacher_supervisor_ids()
    show_teacher_column = current_user.is_teacher_supervisor_manager() and len(visible_teacher_ids) > 1
    assigned_scope_rows = db.session.query(
        scope_expr.label('effective_scope'),
        Customer.private_owner_id.label('private_owner_id')
    ).outerjoin(
        CustomerPayment, Customer.id == CustomerPayment.customer_id
    ).filter(
        Customer.supervisor_user_id.in_(visible_teacher_ids)
    ).all()

    has_public_customers = any(row.effective_scope == PUBLIC_SCOPE for row in assigned_scope_rows)
    has_private_customers = any(row.effective_scope == PRIVATE_SCOPE for row in assigned_scope_rows)
    private_owner_ids = sorted({
        row.private_owner_id for row in assigned_scope_rows
        if row.effective_scope == PRIVATE_SCOPE and row.private_owner_id
    })

    # 仅“同时服务公域+私域”的班主任显示切换按钮，并按私域销售人维度切换
    if has_public_customers and private_owner_ids:
        show_scope_switch = True
        can_switch_scope = True
        requested_scope = (request.args.get('scope', '', type=str) or '').strip().lower()
        requested_private_owner_id = request.args.get('private_owner_id', type=int)
        if requested_scope == PRIVATE_SCOPE and requested_private_owner_id in private_owner_ids:
            scope_filter = PRIVATE_SCOPE
            selected_private_owner_id = requested_private_owner_id
        else:
            scope_filter = PUBLIC_SCOPE
            selected_private_owner_id = None
        private_owner_options = User.query.filter(
            User.id.in_(private_owner_ids)
        ).order_by(User.username.asc()).all()
    elif has_private_customers and not has_public_customers:
        scope_filter = PRIVATE_SCOPE
    else:
        scope_filter = PUBLIC_SCOPE

    # 只查询当前班主任负责的客户
    query = db.session.query(
        Customer, CustomerPayment, Lead
    ).join(
        Lead, Customer.lead_id == Lead.id
    ).outerjoin(
        CustomerPayment, Customer.id == CustomerPayment.customer_id
    ).filter(
        Customer.supervisor_user_id.in_(visible_teacher_ids)
    )
    query = query.filter(scope_expr == scope_filter)
    if selected_private_owner_id:
        query = query.filter(Customer.private_owner_id == selected_private_owner_id)

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
                supervisor_user_id=customer.supervisor_user_id,
                total_amount=None  # 总金额需要手动设置
            )

        # 总金额从customer_payments.total_amount获取（公司应付给供应商的金额）
        total_amount = float(payment.total_amount) if payment.total_amount else 0

        # 时间筛选：检查是否有任何一笔付款在时间范围内，并计算时间段内的付款总额
        period_paid = 0  # 筛选时间段内的付款总额
        if start_date or end_date:
            payment_dates = []
            # 检查第一笔付款
            if payment.first_payment_date:
                date_str = payment.first_payment_date.strftime('%Y-%m')
                payment_dates.append(date_str)
                # 检查是否在时间范围内
                if start_date and end_date:
                    if start_date <= date_str <= end_date:
                        period_paid += float(payment.first_payment) if payment.first_payment else 0
                elif start_date:
                    if date_str >= start_date:
                        period_paid += float(payment.first_payment) if payment.first_payment else 0
                elif end_date:
                    if date_str <= end_date:
                        period_paid += float(payment.first_payment) if payment.first_payment else 0

            # 检查第二笔付款
            if payment.second_payment_date:
                date_str = payment.second_payment_date.strftime('%Y-%m')
                payment_dates.append(date_str)
                if start_date and end_date:
                    if start_date <= date_str <= end_date:
                        period_paid += float(payment.second_payment) if payment.second_payment else 0
                elif start_date:
                    if date_str >= start_date:
                        period_paid += float(payment.second_payment) if payment.second_payment else 0
                elif end_date:
                    if date_str <= end_date:
                        period_paid += float(payment.second_payment) if payment.second_payment else 0

            # 检查第三笔付款
            if payment.third_payment_date:
                date_str = payment.third_payment_date.strftime('%Y-%m')
                payment_dates.append(date_str)
                if start_date and end_date:
                    if start_date <= date_str <= end_date:
                        period_paid += float(payment.third_payment) if payment.third_payment else 0
                elif start_date:
                    if date_str >= start_date:
                        period_paid += float(payment.third_payment) if payment.third_payment else 0
                elif end_date:
                    if date_str <= end_date:
                        period_paid += float(payment.third_payment) if payment.third_payment else 0

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
            'teacher_user_name': customer.teacher_user.username if customer.teacher_user and customer.teacher_user.username else '-',
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
            'remaining': payment.get_remaining() if hasattr(payment, 'get_remaining') else 0,
            'period_paid': period_paid  # 筛选时间段内的付款总额
        })

    return render_template('payments/manage.html',
                         payment_data=payment_data,
                         start_date=start_date,
                         end_date=end_date,
                         show_teacher_column=show_teacher_column,
                         scope_filter=scope_filter,
                         can_switch_scope=can_switch_scope,
                         show_scope_switch=show_scope_switch,
                         private_owner_options=private_owner_options,
                         selected_private_owner_id=selected_private_owner_id)


@payments_bp.route('/update/<int:customer_id>', methods=['POST'])
@login_required
@teacher_supervisor_required
def update_payment(customer_id):
    """更新客户付款信息"""

    # 验证权限：只能更新自己负责的客户
    customer = Customer.query.get_or_404(customer_id)
    if customer.supervisor_user_id not in get_visible_teacher_supervisor_ids():
        return jsonify({'success': False, 'message': '您只能编辑自己或旗下班主任负责的客户付款信息'}), 403

    # 获取或创建付款记录
    payment = CustomerPayment.query.filter_by(customer_id=customer_id).first()
    if not payment:
        payment = CustomerPayment(
            customer_id=customer_id,
            supervisor_user_id=customer.supervisor_user_id,
            scope_snapshot=customer.customer_scope or PUBLIC_SCOPE
        )
        db.session.add(payment)

    try:
        # 更新字段
        data = request.get_json()

        # 获取锁定月份配置
        lock_config = SystemConfig.query.filter_by(config_key='payment_lock_month').first()
        lock_month = lock_config.config_value if lock_config else None
        
        # 总金额
        if 'total_amount' in data:
            payment.total_amount = Decimal(str(data['total_amount'])) if data['total_amount'] else None
        
        # 检查锁定：如果修改的是已有付款记录，检查是否被锁定
        def check_payment_locked(payment_date_str, field_name):
            """检查付款是否被锁定"""
            if lock_month and payment_date_str:
                # 比较年-月格式的字符串
                if payment_date_str <= lock_month:
                    return True, f'{field_name}已被锁定（锁定月份：{lock_month}），无法修改'
            return False, None

        # 第一笔付款
        if 'first_payment' in data or 'first_payment_date' in data:
            # 检查原有付款日期是否被锁定
            if payment.first_payment_date:
                original_month = payment.first_payment_date.strftime('%Y-%m')
                is_locked, error_msg = check_payment_locked(original_month, '第一笔付款')
                if is_locked:
                    return jsonify({'success': False, 'message': error_msg}), 403

            # 检查新的付款日期是否被锁定
            if 'first_payment_date' in data and data['first_payment_date']:
                new_month = data['first_payment_date']
                is_locked, error_msg = check_payment_locked(new_month, '第一笔付款')
                if is_locked:
                    return jsonify({'success': False, 'message': f'不能将付款日期设置为已锁定的月份（锁定月份：{lock_month}）'}), 403

            # 更新数据
            if 'first_payment' in data:
                payment.first_payment = Decimal(str(data['first_payment'])) if data['first_payment'] else None
            if 'first_payment_date' in data:
                if data['first_payment_date']:
                    payment.first_payment_date = datetime.strptime(data['first_payment_date'] + '-01', '%Y-%m-%d').date()
                else:
                    payment.first_payment_date = None

        # 第二笔付款
        if 'second_payment' in data or 'second_payment_date' in data:
            # 检查原有付款日期是否被锁定
            if payment.second_payment_date:
                original_month = payment.second_payment_date.strftime('%Y-%m')
                is_locked, error_msg = check_payment_locked(original_month, '第二笔付款')
                if is_locked:
                    return jsonify({'success': False, 'message': error_msg}), 403

            # 检查新的付款日期是否被锁定
            if 'second_payment_date' in data and data['second_payment_date']:
                new_month = data['second_payment_date']
                is_locked, error_msg = check_payment_locked(new_month, '第二笔付款')
                if is_locked:
                    return jsonify({'success': False, 'message': f'不能将付款日期设置为已锁定的月份（锁定月份：{lock_month}）'}), 403

            # 更新数据
            if 'second_payment' in data:
                payment.second_payment = Decimal(str(data['second_payment'])) if data['second_payment'] else None
            if 'second_payment_date' in data:
                if data['second_payment_date']:
                    payment.second_payment_date = datetime.strptime(data['second_payment_date'] + '-01', '%Y-%m-%d').date()
                else:
                    payment.second_payment_date = None

        # 第三笔付款
        if 'third_payment' in data or 'third_payment_date' in data:
            # 检查原有付款日期是否被锁定
            if payment.third_payment_date:
                original_month = payment.third_payment_date.strftime('%Y-%m')
                is_locked, error_msg = check_payment_locked(original_month, '第三笔付款')
                if is_locked:
                    return jsonify({'success': False, 'message': error_msg}), 403

            # 检查新的付款日期是否被锁定
            if 'third_payment_date' in data and data['third_payment_date']:
                new_month = data['third_payment_date']
                is_locked, error_msg = check_payment_locked(new_month, '第三笔付款')
                if is_locked:
                    return jsonify({'success': False, 'message': f'不能将付款日期设置为已锁定的月份（锁定月份：{lock_month}）'}), 403

            # 更新数据
            if 'third_payment' in data:
                payment.third_payment = Decimal(str(data['third_payment'])) if data['third_payment'] else None
            if 'third_payment_date' in data:
                if data['third_payment_date']:
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
        
        payment.scope_snapshot = customer.customer_scope or PUBLIC_SCOPE
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


@payments_bp.route('/get_lock_month', methods=['GET'])
@login_required
def get_lock_month():
    """获取当前付款锁定月份"""
    try:
        config = SystemConfig.query.filter_by(config_key='payment_lock_month').first()

        result = {
            'lock_month': config.config_value if config else None
        }

        # 如果有锁定信息，返回更新人和更新时间
        if config and config.updated_by:
            updater = User.query.get(config.updated_by)
            result['updated_by'] = updater.username if updater else '未知'
            result['updated_at'] = config.updated_at.strftime('%Y-%m-%d %H:%M:%S') if config.updated_at else None

        return jsonify(result)
    except Exception as e:
        return jsonify({'lock_month': None, 'error': str(e)})


@payments_bp.route('/set_lock_month', methods=['POST'])
@login_required
@sales_manager_required
def set_lock_month():
    """设置付款锁定月份（仅销售管理可操作）"""
    try:
        data = request.get_json()
        lock_month = data.get('lock_month')

        if not lock_month:
            return jsonify({'success': False, 'message': '请选择锁定月份'}), 400

        # 验证月份格式
        try:
            datetime.strptime(lock_month, '%Y-%m')
        except ValueError:
            return jsonify({'success': False, 'message': '月份格式错误，应为YYYY-MM'}), 400

        # 更新或创建配置
        config = SystemConfig.query.filter_by(config_key='payment_lock_month').first()
        if config:
            old_value = config.config_value
            config.config_value = lock_month
            config.updated_by = current_user.id
            config.updated_at = datetime.utcnow()
            action = '更新'
        else:
            config = SystemConfig(
                config_key='payment_lock_month',
                config_value=lock_month,
                description='付款记录锁定月份（该月份及之前的付款记录不可编辑）',
                updated_by=current_user.id
            )
            db.session.add(config)
            old_value = None
            action = '设置'

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'已{action}锁定月份为 {lock_month}，该月份及之前的所有付款记录将无法编辑',
            'lock_month': lock_month,
            'old_value': old_value
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'设置失败：{str(e)}'}), 500


@payments_bp.route('/clear_lock_month', methods=['POST'])
@login_required
@sales_manager_required
def clear_lock_month():
    """清除付款锁定（仅销售管理可操作）"""
    try:
        config = SystemConfig.query.filter_by(config_key='payment_lock_month').first()

        if not config:
            return jsonify({'success': False, 'message': '当前没有锁定设置'}), 400

        old_value = config.config_value
        db.session.delete(config)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'已清除锁定设置（原锁定月份：{old_value}），所有付款记录现在可以编辑',
            'old_value': old_value
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'清除失败：{str(e)}'}), 500

