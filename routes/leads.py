from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import User, Lead, Customer, Payment, db
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import func, and_
import re

leads_bp = Blueprint('leads', __name__)

def sales_required(f):
    """销售管理权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_sales():
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def sales_or_admin_required(f):
    """销售或管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not (current_user.is_sales() or current_user.is_admin()):
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def validate_phone(phone):
    """验证手机号格式"""
    pattern = r'^1[3-9]\d{9}$'
    return re.match(pattern, phone) is not None

def auto_update_lead_stage(lead):
    """根据线索的各种操作自动更新阶段"""
    # 获取该线索的所有付款记录，按日期排序
    payments = Payment.query.filter_by(lead_id=lead.id).order_by(Payment.payment_date.asc()).all()

    # 计算已付款总额
    total_paid = sum(payment.amount for payment in payments) if payments else 0
    contract_amount = lead.contract_amount or 0

    # 阶段判断逻辑（按优先级从高到低）

    # 1. 如果已付款等于或超过合同金额，且合同金额大于0，则为"全款支付"
    if contract_amount > 0 and total_paid >= contract_amount:
        lead.stage = '全款支付'

    # 2. 如果有两笔或以上付款，则为"次笔支付"
    elif len(payments) >= 2:
        lead.stage = '次笔支付'

    # 3. 如果有一笔付款，则为"首笔支付"
    elif len(payments) >= 1:
        lead.stage = '首笔支付'

    # 4. 如果设置了见面时间，则为"线下见面"
    elif lead.meeting_at:
        lead.stage = '线下见面'

    # 5. 默认为"获取联系方式"
    else:
        lead.stage = '获取联系方式'

def update_lead_payment_times(lead):
    """根据付款记录自动更新线索的支付时间和阶段"""
    # 获取该线索的所有付款记录，按日期排序
    payments = Payment.query.filter_by(lead_id=lead.id).order_by(Payment.payment_date.asc()).all()

    if not payments:
        # 如果没有付款记录，清空支付时间，但不改变阶段
        lead.first_payment_at = None
        lead.second_payment_at = None
        # 同时更新旧字段以保持兼容性
        lead.deposit_paid_at = None
        lead.full_payment_at = None
        return

    # 设置首笔支付时间（第一笔付款的日期）
    first_payment = payments[0]
    lead.first_payment_at = datetime.combine(first_payment.payment_date, datetime.min.time())
    lead.deposit_paid_at = lead.first_payment_at  # 保持兼容性

    # 设置次笔支付时间（第二笔付款的日期，如果存在）
    if len(payments) >= 2:
        second_payment = payments[1]
        lead.second_payment_at = datetime.combine(second_payment.payment_date, datetime.min.time())
        lead.full_payment_at = lead.second_payment_at  # 保持兼容性
    else:
        lead.second_payment_at = None
        lead.full_payment_at = None

    # 使用新的自动阶段更新逻辑
    auto_update_lead_stage(lead)

@leads_bp.route('/dashboard')
@login_required
@sales_required
def dashboard():
    """线索管理仪表板"""
    from datetime import date, timedelta
    from flask import request
    from sqlalchemy import and_, func

    # 获取时间段参数，默认为上个月15日到当日
    today = date.today()
    default_start = date(today.year, today.month - 1 if today.month > 1 else 12, 15)
    if today.month == 1:
        default_start = date(today.year - 1, 12, 15)

    start_date_str = request.args.get('start_date', default_start.strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', today.strftime('%Y-%m-%d'))

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

    except ValueError:
        start_date = default_start
        end_date = today

    # 1. 合同额统计 - 基于首笔支付时间
    contract_amount_result = db.session.query(func.sum(Lead.contract_amount)).filter(
        and_(
            Lead.first_payment_at.isnot(None),
            func.date(Lead.first_payment_at) >= start_date,
            func.date(Lead.first_payment_at) <= end_date
        )
    ).scalar()
    total_contract_amount = float(contract_amount_result or 0)



    # 2. 首笔客户数 - 处于"首笔支付"阶段的客户
    first_payment_customers = db.session.query(Lead.id).filter(
        and_(
            Lead.stage == '首笔支付',
            Lead.created_at >= start_date,
            Lead.created_at <= end_date
        )
    ).count()

    # 3. 付款客户数 - 基于Payment表统计有实际付款记录的客户
    paid_customers = db.session.query(Lead.id).join(Payment).filter(
        and_(
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date
        )
    ).distinct().count()

    # 4. 付款金额 - 指定时间段内的总付款金额
    total_payment_amount = db.session.query(func.sum(Payment.amount)).filter(
        and_(
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date
        )
    ).scalar() or 0



    return render_template('leads/dashboard.html',
                         start_date=start_date.strftime('%Y-%m-%d'),
                         end_date=end_date.strftime('%Y-%m-%d'),
                         total_contract_amount=total_contract_amount,
                         first_payment_customers=first_payment_customers,
                         paid_customers=paid_customers,
                         total_payment_amount=total_payment_amount)

@leads_bp.route('/list')
@login_required
@sales_required
def list_leads():
    """线索列表"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    stage_filter = request.args.get('stage', '', type=str)
    sales_filter = request.args.get('sales', '', type=str)

    # 新增：仪表板跳转的筛选参数
    first_payment_date_start = request.args.get('first_payment_date_start', '', type=str)
    first_payment_date_end = request.args.get('first_payment_date_end', '', type=str)
    has_contract_amount = request.args.get('has_contract_amount', '', type=str)
    contract_date_start = request.args.get('contract_date_start', '', type=str)
    contract_date_end = request.args.get('contract_date_end', '', type=str)

    query = Lead.query

    # 搜索过滤
    if search:
        query = query.filter(
            (Lead.parent_wechat_display_name.contains(search)) |
            (Lead.parent_wechat_name.contains(search)) |
            (Lead.contact_info.contains(search)) |
            (Lead.student_name.contains(search) if Lead.student_name else False)
        )

    # 阶段过滤
    if stage_filter:
        query = query.filter_by(stage=stage_filter)

    # 销售过滤
    if sales_filter:
        query = query.filter_by(sales_user_id=sales_filter)



    # 新增：已付款客户筛选 - 基于Payment表
    if first_payment_date_start and first_payment_date_end:
        try:
            start_date = datetime.strptime(first_payment_date_start, '%Y-%m-%d').date()
            end_date = datetime.strptime(first_payment_date_end, '%Y-%m-%d').date()
            # 基于Payment表筛选有实际付款记录的客户
            payment_lead_ids = db.session.query(Payment.lead_id).filter(
                and_(
                    Payment.payment_date >= start_date,
                    Payment.payment_date <= end_date
                )
            ).distinct().subquery()

            query = query.filter(Lead.id.in_(payment_lead_ids))
        except ValueError:
            pass



    # 新增：合同金额筛选
    if has_contract_amount == 'true':
        query = query.filter(Lead.contract_amount.isnot(None))
        query = query.filter(Lead.contract_amount > 0)

        # 如果指定了合同日期范围，进一步筛选
        if contract_date_start and contract_date_end:
            try:
                start_date = datetime.strptime(contract_date_start, '%Y-%m-%d').date()
                end_date = datetime.strptime(contract_date_end, '%Y-%m-%d').date()
                # 这里我们使用首笔付款时间作为合同签订的参考时间
                query = query.filter(
                    and_(
                        Lead.first_payment_at.isnot(None),
                        func.date(Lead.first_payment_at) >= start_date,
                        func.date(Lead.first_payment_at) <= end_date
                    )
                )
            except ValueError:
                pass

    # 分页
    leads = query.order_by(Lead.updated_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # 获取所有销售人员用于筛选
    sales_users = User.query.filter_by(role='sales', status=True).all()
    
    # 线索阶段选项
    stages = ['获取联系方式', '线下见面', '首笔支付', '次笔支付', '全款支付']
    
    # 确定筛选类型（用于页面标题显示）
    filter_type = None
    filter_period = None
    if has_contract_amount == 'true':
        filter_type = "有合同金额客户"
        if contract_date_start and contract_date_end:
            filter_period = f"{contract_date_start} 至 {contract_date_end}"
        else:
            filter_period = "所有时间"
    elif first_payment_date_start and first_payment_date_end:
        filter_type = "付款客户"
        filter_period = f"{first_payment_date_start} 至 {first_payment_date_end}"

    return render_template('leads/list.html',
                         leads=leads,
                         search=search,
                         stage_filter=stage_filter,
                         sales_filter=sales_filter,
                         sales_users=sales_users,
                         stages=stages,
                         filter_type=filter_type,
                         filter_period=filter_period)

@leads_bp.route('/add', methods=['GET', 'POST'])
@login_required
@sales_required
def add_lead():
    """添加线索"""
    if request.method == 'POST':
        parent_wechat_display_name = request.form.get('parent_wechat_display_name', '').strip()
        parent_wechat_name = request.form.get('parent_wechat_name', '').strip()
        phone = request.form.get('phone', '').strip()
        source = request.form.get('source', '').strip()
        grade = request.form.get('grade', '').strip()
        assigned_sales_id = request.form.get('assigned_sales_id', type=int)
        notes = request.form.get('notes', '').strip()
        contact_obtained_at = request.form.get('contact_obtained_at', '').strip()
        meeting_at = request.form.get('meeting_at', '').strip()
        meeting_location = request.form.get('meeting_location', '').strip()

        # 验证必填字段
        if not all([parent_wechat_display_name, parent_wechat_name, source, grade]):
            flash('家长微信名、家长微信号、线索来源和年级为必填项', 'error')
            return render_template('leads/add.html', sales_users=get_sales_users())

        # 验证家长微信号是否重复
        existing_wechat = Lead.query.filter_by(parent_wechat_name=parent_wechat_name).first()
        if existing_wechat:
            flash('家长微信号不能重复', 'error')
            return render_template('leads/add.html', sales_users=get_sales_users())



        # 验证手机号格式（如果填写了手机号）
        if phone:
            import re
            phone_pattern = r'^1[0-9]\d{9}$'
            if not re.match(phone_pattern, phone):
                flash('请输入正确的11位手机号', 'error')
                return render_template('leads/add.html', sales_users=get_sales_users())

        # 检查手机号是否已存在（如果填写了手机号）
        if phone:
            # 检查contact_info字段中是否包含该手机号
            existing_leads = Lead.query.filter(Lead.contact_info.like(f'%{phone}%')).all()
            for existing_lead in existing_leads:
                # 提取contact_info中的手机号进行精确匹配
                contact_parts = existing_lead.contact_info.split()
                existing_phone = contact_parts[0] if contact_parts else existing_lead.contact_info
                if existing_phone == phone:
                    flash('手机号不能重复', 'error')
                    return render_template('leads/add.html', sales_users=get_sales_users())

        # 如果没有指定销售，分配给当前用户
        if not assigned_sales_id:
            assigned_sales_id = current_user.id

        # 验证销售人员
        sales_user = User.query.filter_by(id=assigned_sales_id, role='sales', status=True).first()
        if not sales_user:
            flash('选择的销售人员无效', 'error')
            return render_template('leads/add.html', sales_users=get_sales_users())

        # 阶段将通过自动更新逻辑设置

        # contact_info 存储手机号（可选）
        contact_info = phone if phone else None

        # 备注将作为沟通记录处理，不再存储在follow_up_notes字段

        # 解析时间字段
        contact_obtained_datetime = None
        meeting_datetime = None

        if contact_obtained_at:
            try:
                # 解析日期格式 (YYYY-MM-DD)，转换为datetime对象
                from datetime import date
                contact_date = date.fromisoformat(contact_obtained_at)
                contact_obtained_datetime = datetime.combine(contact_date, datetime.min.time())
            except ValueError:
                flash('获取联系方式日期格式不正确', 'error')
                return render_template('leads/add.html', sales_users=get_sales_users())

        if meeting_at:
            try:
                meeting_datetime = datetime.fromisoformat(meeting_at)
            except ValueError:
                flash('线下见面时间格式不正确', 'error')
                return render_template('leads/add.html', sales_users=get_sales_users())

        # 创建线索
        try:
            lead = Lead(
                parent_wechat_display_name=parent_wechat_display_name,  # 家长微信名必填
                parent_wechat_name=parent_wechat_name,  # 家长微信号必填
                contact_info=contact_info,  # 联系方式可选
                lead_source=source,
                grade=grade,  # 年级必填
                sales_user_id=assigned_sales_id,
                stage='获取联系方式',  # 临时设置，稍后会自动更新
                follow_up_notes=None,  # 不再使用此字段，备注作为沟通记录处理
                contract_amount=None,  # 合同金额在后续通过专门接口设置
                service_types='["tutoring"]'  # 默认设置为课题辅导
            )

            # 设置时间字段
            if contact_obtained_datetime:
                lead.contact_obtained_at = contact_obtained_datetime
            else:  # 如果没有手动设置，则使用当前时间
                lead.contact_obtained_at = datetime.utcnow()

            if meeting_datetime:
                lead.meeting_at = meeting_datetime

            # 设置见面地点
            if meeting_location:
                lead.meeting_location = meeting_location

            # 根据当前状态自动更新阶段
            auto_update_lead_stage(lead)

            db.session.add(lead)
            db.session.commit()

            # 如果有备注信息，添加为沟通记录
            if notes:
                try:
                    from communication_utils import CommunicationManager
                    # 添加线索阶段沟通记录
                    CommunicationManager.add_lead_communication(
                        lead_id=lead.id,
                        content=notes,
                        created_at=contact_obtained_datetime or datetime.utcnow()
                    )
                except Exception as e:
                    # 如果创建沟通记录失败，不影响线索创建
                    print(f"创建沟通记录失败: {str(e)}")

            flash(f'线索 {parent_wechat_display_name} 创建成功，已分配给 {sales_user.username}', 'success')
            return redirect(url_for('leads.list_leads'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建线索失败: {str(e)}', 'error')

    return render_template('leads/add.html', sales_users=get_sales_users())

@leads_bp.route('/check-phone', methods=['POST'])
@login_required
@sales_required
def check_phone():
    """检查手机号是否重复"""
    data = request.get_json()
    phone = data.get('phone', '').strip()

    if not phone:
        return jsonify({'exists': False})

    # 查找是否存在相同手机号的线索
    existing_lead = Lead.query.filter(Lead.contact_info.like(f'{phone}%')).first()

    if existing_lead:
        return jsonify({
            'exists': True,
            'student_name': existing_lead.get_display_name(),
            'lead_id': existing_lead.id
        })
    else:
        return jsonify({'exists': False})

@leads_bp.route('/check-wechat', methods=['POST'])
@login_required
@sales_required
def check_wechat():
    """检查家长微信号是否重复"""
    data = request.get_json()
    wechat_name = data.get('wechat_name', '').strip()
    lead_id = data.get('lead_id')  # 编辑时排除自己

    if not wechat_name:
        return jsonify({'exists': False})

    # 查找是否存在相同微信号的线索
    query = Lead.query.filter_by(parent_wechat_name=wechat_name)
    if lead_id:
        query = query.filter(Lead.id != lead_id)

    existing_lead = query.first()

    if existing_lead:
        return jsonify({
            'exists': True,
            'display_name': existing_lead.get_display_name(),
            'lead_id': existing_lead.id
        })
    else:
        return jsonify({'exists': False})

def get_sales_users():
    """获取所有启用的销售人员"""
    return User.query.filter_by(role='sales', status=True).all()

def is_field_locked(value):
    """判断单个字段是否应该被锁定"""
    # 如果字段有值且不为空字符串，则锁定
    return bool(value and str(value).strip())

def is_basic_info_locked(lead):
    """判断基本信息是否应该被锁定（保留兼容性）"""
    # 只有当学员姓名不为空时才锁定基本信息
    has_student_name = lead.student_name and lead.student_name.strip()

    return bool(has_student_name)

@leads_bp.route('/<int:lead_id>/edit', methods=['GET', 'POST'])
@login_required
@sales_or_admin_required
def edit_lead(lead_id):
    """编辑线索"""
    lead = Lead.query.get_or_404(lead_id)

    # 阶段映射
    stage_mapping = {
        'contact': '获取联系方式',
        'meeting': '线下见面',
        'deposit': '首笔支付',
        'payment': '次笔支付',
        'full_payment': '全款支付'
    }

    # 反向映射
    reverse_stage_mapping = {v: k for k, v in stage_mapping.items()}

    if request.method == 'POST':
        # 检查基本信息是否已锁定
        basic_info_locked = is_basic_info_locked(lead)

        # 基本信息字段处理
        if basic_info_locked:
            # 如果基本信息已锁定，保持原有值
            student_name = lead.student_name
            lead_source = lead.lead_source
            sales_user_id = lead.sales_user_id
        else:
            # 如果基本信息未锁定，允许修改
            student_name = request.form.get('student_name', '').strip()
            lead_source = request.form.get('lead_source', '').strip()
            sales_user_id = request.form.get('sales_user_id', type=int)

        # 家长微信名和微信号不可修改，保持原有值
        parent_wechat_display_name = lead.parent_wechat_display_name
        parent_wechat_name = lead.parent_wechat_name

        # 其他字段正常处理
        contact_info = request.form.get('contact_info', '').strip()
        follow_up_notes = request.form.get('follow_up_notes', '').strip()
        contract_amount = request.form.get('contract_amount', '').strip()

        # 获取多选服务类型
        service_types = request.form.getlist('service_types')
        competition_award_level = request.form.get('competition_award_level', '').strip()
        additional_requirements = request.form.get('additional_requirements', '').strip()

        # 检查是否确认转换为客户
        confirm_convert = request.form.get('confirm_convert') == 'true'

        # 获取时间字段
        contact_obtained_at = request.form.get('contact_obtained_at')
        meeting_at = request.form.get('meeting_at')
        meeting_location = request.form.get('meeting_location', '').strip()
        deposit_paid_at = request.form.get('deposit_paid_at')
        full_payment_at = request.form.get('full_payment_at')

        # 验证必填字段（只验证未锁定的字段）
        missing_fields = []

        # 家长微信号：如果未锁定且为空，则为必填
        if not is_field_locked(lead.parent_wechat_name) and not parent_wechat_name:
            missing_fields.append('家长微信号')

        # 责任销售：如果未锁定且为空，则为必填
        if not is_field_locked(lead.sales_user_id) and not sales_user_id:
            missing_fields.append('责任销售')

        if missing_fields:
            flash(f'{", ".join(missing_fields)}为必填项', 'error')
            return render_template('leads/edit.html', lead=lead, sales_users=get_sales_users(), is_basic_info_locked=is_basic_info_locked, is_field_locked=is_field_locked)

        # 验证服务类型
        if not service_types:
            flash('请至少选择一种服务类型', 'error')
            return render_template('leads/edit.html', lead=lead, sales_users=get_sales_users(), is_basic_info_locked=is_basic_info_locked, is_field_locked=is_field_locked)

        # 验证竞赛辅导和奖项等级的关联
        if 'competition' in service_types and not competition_award_level:
            flash('选择竞赛辅导时，奖项等级为必填项', 'error')
            return render_template('leads/edit.html', lead=lead, sales_users=get_sales_users(), is_basic_info_locked=is_basic_info_locked, is_field_locked=is_field_locked)

        # 验证家长微信号是否重复（只在未锁定且有值时验证）
        if not is_field_locked(lead.parent_wechat_name) and parent_wechat_name:
            existing_wechat = Lead.query.filter(
                Lead.parent_wechat_name == parent_wechat_name,
                Lead.id != lead.id
            ).first()
            if existing_wechat:
                flash('家长微信号不能重复', 'error')
                return render_template('leads/edit.html', lead=lead, sales_users=get_sales_users(), is_basic_info_locked=is_basic_info_locked, is_field_locked=is_field_locked)

        # 验证销售人员（只在未锁定且有值时验证）
        if not is_field_locked(lead.sales_user_id) and sales_user_id:
            sales_user = User.query.filter_by(id=sales_user_id, role='sales', status=True).first()
            if not sales_user:
                flash('选择的销售人员无效', 'error')
                return render_template('leads/edit.html', lead=lead, sales_users=get_sales_users(), is_basic_info_locked=is_basic_info_locked, is_field_locked=is_field_locked)

        # 阶段将通过自动更新逻辑设置，不再从表单获取

        # 移除自动转客户机制，用户可以手动选择转客户时机

        try:
            # 记录责任销售变更（只在未锁定时）
            sales_change_note = None
            if not is_field_locked(lead.sales_user_id) and lead.sales_user_id != sales_user_id:
                old_sales = User.query.get(lead.sales_user_id)
                new_sales = User.query.get(sales_user_id)
                sales_change_note = f"责任销售从 {old_sales.username} 变更为 {new_sales.username}"

            # 更新线索信息（只更新未锁定的字段）
            if not is_field_locked(lead.student_name):
                lead.student_name = student_name if student_name else None
            if not is_field_locked(lead.parent_wechat_display_name):
                lead.parent_wechat_display_name = parent_wechat_display_name
            if not is_field_locked(lead.parent_wechat_name):
                lead.parent_wechat_name = parent_wechat_name
            if not is_field_locked(lead.contact_info):
                lead.contact_info = contact_info if contact_info else None
            if not is_field_locked(lead.lead_source):
                lead.lead_source = lead_source if lead_source else None
            if not is_field_locked(lead.sales_user_id):
                lead.sales_user_id = sales_user_id

            # 不再更新follow_up_notes字段，而是作为沟通记录处理
            lead.competition_award_level = competition_award_level if competition_award_level else None
            lead.additional_requirements = additional_requirements if additional_requirements else None
            lead.updated_at = datetime.utcnow()

            # 设置多选服务类型
            lead.set_service_types_list(service_types)

            # 合同金额现在通过专门的接口更新，这里不再处理

            # 更新时间字段
            try:
                # 获取联系方式时间（只需要日期）
                if contact_obtained_at:
                    contact_date = datetime.strptime(contact_obtained_at, '%Y-%m-%d')
                    lead.contact_obtained_at = contact_date

                # 线下见面时间（需要具体时间）
                if meeting_at:
                    lead.meeting_at = datetime.fromisoformat(meeting_at.replace('T', ' '))
                else:
                    # 如果清空了见面时间，也要清空见面地点
                    lead.meeting_at = None
                    meeting_location = ''

                # 设置见面地点
                if meeting_location:
                    lead.meeting_location = meeting_location
                elif not lead.meeting_at:
                    # 如果没有见面时间，清空见面地点
                    lead.meeting_location = None

                # 定金支付时间（只需要日期）
                if deposit_paid_at:
                    deposit_date = datetime.strptime(deposit_paid_at, '%Y-%m-%d')
                    lead.deposit_paid_at = deposit_date

                # 次笔款项支付时间（只需要日期）
                if full_payment_at:
                    payment_date = datetime.strptime(full_payment_at, '%Y-%m-%d')
                    lead.full_payment_at = payment_date
            except ValueError:
                pass  # 忽略时间格式错误

            # 自动设置获取联系方式时间（如果没有手动设置）
            if not lead.contact_obtained_at:
                lead.contact_obtained_at = datetime.utcnow()

            # 根据当前状态自动更新阶段
            auto_update_lead_stage(lead)

            db.session.commit()

            # 处理备注作为沟通记录
            from communication_utils import CommunicationManager

            # 如果有跟进备注，添加为沟通记录
            if follow_up_notes:
                # 获取该线索的付款记录，判断当前阶段
                payments = Payment.query.filter_by(lead_id=lead.id).order_by(Payment.payment_date.asc()).all()
                has_second_payment = len(payments) >= 2

                if has_second_payment:
                    # 有次笔付款，检查是否已转为客户
                    customer = Customer.query.filter_by(lead_id=lead.id).first()
                    if customer:
                        # 客户阶段沟通记录
                        CommunicationManager.add_customer_communication(
                            lead_id=lead.id,
                            customer_id=customer.id,
                            content=follow_up_notes
                        )
                    else:
                        # 线索阶段沟通记录
                        CommunicationManager.add_lead_communication(
                            lead_id=lead.id,
                            content=follow_up_notes
                        )
                else:
                    # 线索阶段沟通记录
                    CommunicationManager.add_lead_communication(
                        lead_id=lead.id,
                        content=follow_up_notes
                    )

            # 如果有销售变更记录，也添加为沟通记录
            if sales_change_note:
                # 销售变更记录始终作为线索阶段记录
                CommunicationManager.add_lead_communication(
                    lead_id=lead.id,
                    content=sales_change_note
                )

            # 移除自动转客户逻辑，用户可以通过"转客户"按钮手动转换
            flash(f'线索 {student_name} 更新成功', 'success')
            return redirect(url_for('leads.list_leads'))
        except Exception as e:
            db.session.rollback()
            flash(f'更新线索失败: {str(e)}', 'error')

    # 为模板准备当前阶段的英文键值
    current_stage_key = reverse_stage_mapping.get(lead.stage, 'contact')

    # 获取付款记录
    payments = Payment.query.filter_by(lead_id=lead.id).order_by(Payment.payment_date.desc()).all()

    # 计算已付款总额
    paid_amount = sum(payment.amount for payment in payments) if payments else Decimal('0')

    return render_template('leads/edit.html',
                         lead=lead,
                         sales_users=get_sales_users(),
                         current_stage_key=current_stage_key,
                         payments=payments,
                         paid_amount=paid_amount,
                         is_basic_info_locked=is_basic_info_locked,
                         is_field_locked=is_field_locked)

@leads_bp.route('/<int:lead_id>/detail')
@login_required
@sales_required
def lead_detail(lead_id):
    """线索详情"""
    lead = Lead.query.get_or_404(lead_id)
    return render_template('leads/detail.html', lead=lead)

@leads_bp.route('/<int:lead_id>/convert', methods=['POST'])
@login_required
@sales_required
def convert_to_customer(lead_id):
    """将线索转换为客户"""
    lead = Lead.query.get_or_404(lead_id)

    # 检查线索是否已经是次笔支付或全款支付阶段
    if lead.stage not in ['次笔支付', '全款支付']:
        return jsonify({'success': False, 'message': '只有次笔支付或全款支付阶段的线索才能转换为客户'})

    # 检查是否已经转换过
    if lead.customer:
        return jsonify({'success': False, 'message': '该线索已经转换为客户'})

    try:
        from datetime import datetime
        # 创建客户记录
        customer = Customer(
            lead_id=lead.id,
            sales_user_id=lead.sales_user_id,
            payment_amount=0,  # 需要后续填写
            award_requirement='无',  # 默认为无奖项要求
            converted_at=datetime.now()  # 记录转换时间
        )
        db.session.add(customer)
        db.session.commit()

        return jsonify({'success': True, 'message': f'线索 {lead.student_name} 已成功转换为客户'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'转换失败: {str(e)}'})

@leads_bp.route('/add_payment', methods=['POST'])
@login_required
@sales_required
def add_payment():
    """添加付款记录"""
    try:
        lead_id = request.form.get('lead_id', type=int)
        payment_date_str = request.form.get('payment_date', '').strip()
        payment_amount_str = request.form.get('payment_amount', '').strip()
        payment_notes = request.form.get('payment_notes', '').strip()

        # 验证必填字段
        if not all([lead_id, payment_date_str, payment_amount_str]):
            return jsonify({'success': False, 'message': '线索ID、付款日期和付款金额为必填项'})

        # 验证线索存在
        lead = Lead.query.get(lead_id)
        if not lead:
            return jsonify({'success': False, 'message': '线索不存在'})

        # 解析付款日期
        try:
            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': '付款日期格式错误'})

        # 解析付款金额
        try:
            payment_amount = Decimal(payment_amount_str)
            if payment_amount <= 0:
                return jsonify({'success': False, 'message': '付款金额必须大于0'})
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': '付款金额格式错误'})

        # 创建付款记录
        payment = Payment(
            lead_id=lead_id,
            amount=payment_amount,
            payment_date=payment_date,
            payment_notes=payment_notes if payment_notes else None
        )

        db.session.add(payment)

        # 自动更新线索的支付时间
        update_lead_payment_times(lead)

        db.session.commit()

        return jsonify({'success': True, 'message': '付款记录添加成功'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'添加付款记录失败: {str(e)}'})

@leads_bp.route('/delete_payment/<int:payment_id>', methods=['DELETE'])
@login_required
@sales_required
def delete_payment(payment_id):
    """删除付款记录"""
    try:
        payment = Payment.query.get(payment_id)
        if not payment:
            return jsonify({'success': False, 'message': '付款记录不存在'})

        # 获取关联的线索
        lead = payment.lead

        db.session.delete(payment)

        # 自动更新线索的支付时间
        update_lead_payment_times(lead)

        db.session.commit()

        return jsonify({'success': True, 'message': '付款记录删除成功'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除付款记录失败: {str(e)}'})

@leads_bp.route('/update_contract_amount', methods=['POST'])
@login_required
@sales_required
def update_contract_amount():
    """更新合同金额"""
    try:
        lead_id = request.form.get('lead_id', type=int)
        contract_amount_str = request.form.get('contract_amount', '').strip()

        # 验证必填字段
        if not all([lead_id, contract_amount_str]):
            return jsonify({'success': False, 'message': '线索ID和合同金额为必填项'})

        # 验证线索存在
        lead = Lead.query.get(lead_id)
        if not lead:
            return jsonify({'success': False, 'message': '线索不存在'})

        # 解析合同金额
        try:
            contract_amount = Decimal(contract_amount_str)
            if contract_amount < 0:
                return jsonify({'success': False, 'message': '合同金额不能为负数'})
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': '合同金额格式错误'})

        # 更新合同金额
        lead.contract_amount = contract_amount
        lead.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({'success': True, 'message': '合同金额更新成功'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新合同金额失败: {str(e)}'})


