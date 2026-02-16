from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from functools import wraps
from models import User, Customer, Lead, TutoringDelivery, CustomerCompetition, Payment, DeliveryDocument, TopicTask, TopicSubmission, db
from datetime import datetime, date
from werkzeug.utils import secure_filename
from sqlalchemy import and_, func
import os

delivery_bp = Blueprint('delivery', __name__)


def normalize_parent_wechat_display_name(raw_name, student_name=None):
    """规范化家长微信名，去掉误拼接的“-学员名妈妈/爸爸/家长”后缀。"""
    name = (raw_name or '').strip()
    student = (student_name or '').strip()
    if not name or not student:
        return name

    suffixes = (
        f"-{student}妈妈",
        f"-{student}爸爸",
        f"-{student}家长",
        f"-{student}妈",
        f"-{student}爸",
    )
    for suffix in suffixes:
        if name.endswith(suffix):
            return name[:-len(suffix)].strip(" -")
    return name


def normalized_lead_scope(lead):
    """标准化线索归属域"""
    scope = (lead.customer_scope or Lead.SCOPE_PUBLIC).strip().lower()
    return Lead.SCOPE_PRIVATE if scope == Lead.SCOPE_PRIVATE else Lead.SCOPE_PUBLIC


def teacher_can_access_lead_scope(lead):
    """班主任是否可访问该线索（按服务范围限制）"""
    if not current_user.is_teacher_supervisor():
        return False

    visible_teacher_ids = get_visible_teacher_supervisor_ids()
    if lead.supervisor_user_id and lead.supervisor_user_id not in visible_teacher_ids:
        return False

    scope = normalized_lead_scope(lead)
    if current_user.is_public_only_teacher_supervisor() and scope == Lead.SCOPE_PRIVATE:
        return False
    if current_user.is_private_only_teacher_supervisor() and scope == Lead.SCOPE_PUBLIC:
        return False
    return True


def get_visible_teacher_supervisor_ids():
    """当前班主任可查看的数据归属班主任ID集合（主管=自己+旗下普通班主任）"""
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

def sort_teachers_by_pinyin(teachers):
    """按姓名拼音首字母排序（无库时退化为原始字符串排序）"""
    try:
        from pypinyin import lazy_pinyin
    except Exception:
        return sorted(teachers, key=lambda t: (t.username or ''))

    def key_func(user):
        name = user.username or ''
        if not name:
            return ''
        try:
            initials = ''.join([p[0] for p in lazy_pinyin(name) if p])
            return initials.upper()
        except Exception:
            return name

    return sorted(teachers, key=key_func)

def teacher_supervisor_required(f):
    """班主任权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'teacher_supervisor':
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('您没有权限访问此页面，仅管理员可访问', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@delivery_bp.route('/dashboard')
@login_required
@teacher_supervisor_required
def dashboard():
    """交付管理仪表板"""
    teacher_user_ids = get_visible_teacher_supervisor_ids()

    # 我负责的客户统计
    my_customers = Customer.query.filter(Customer.supervisor_user_id.in_(teacher_user_ids)).count()
    
    # 课题辅导统计 - 基于实际服务类型
    tutoring_total = Customer.query.join(Customer.lead).filter(
        Customer.supervisor_user_id.in_(teacher_user_ids),
        Lead.service_types.contains('tutoring')
    ).count()

    tutoring_completed = TutoringDelivery.query.join(Customer).join(Customer.lead).filter(
        Customer.supervisor_user_id.in_(teacher_user_ids),
        Lead.service_types.contains('tutoring'),
        TutoringDelivery.thesis_status == '已完成'
    ).count()

    # 竞赛辅导统计 - 基于实际服务类型
    competition_total = Customer.query.join(Customer.lead).filter(
        Customer.supervisor_user_id.in_(teacher_user_ids),
        Lead.service_types.contains('competition')
    ).count()

    # 已结束赛事统计（获奖）
    competition_completed = CustomerCompetition.query.join(Customer).filter(
        Customer.supervisor_user_id.in_(teacher_user_ids),
        ~CustomerCompetition.status.in_(['未报名', '已报名'])
    ).count()

    # 最近的交付任务
    recent_tutoring = TutoringDelivery.query.join(Customer).filter(
        Customer.supervisor_user_id.in_(teacher_user_ids)
    ).order_by(TutoringDelivery.updated_at.desc()).limit(5).all()

    # 最近的赛事进展（使用 CustomerCompetition）
    recent_competition = CustomerCompetition.query.join(Customer).filter(
        Customer.supervisor_user_id.in_(teacher_user_ids)
    ).order_by(CustomerCompetition.updated_at.desc()).limit(5).all()

    return render_template('delivery/dashboard.html',
                         my_customers=my_customers,
                         tutoring_total=tutoring_total,
                         tutoring_completed=tutoring_completed,
                         competition_total=competition_total,
                         competition_completed=competition_completed,
                         recent_tutoring=recent_tutoring,
                         recent_competition=recent_competition)

@delivery_bp.route('/leads')
@login_required
@teacher_supervisor_required
def leads_list():
    """头脑风暴 - 班主任只看销售分配给自己的线索（已转客户且处于头脑风暴阶段）"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    start_date = request.args.get('start_date', '', type=str)
    end_date = request.args.get('end_date', '', type=str)
    teacher_user_ids = get_visible_teacher_supervisor_ids()
    show_teacher_column = current_user.is_teacher_supervisor_manager() and len(teacher_user_ids) > 1

    # 如果只填了开始日期，结束日期默认为当天
    if start_date and not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    # 基础查询：班主任主管看自己+旗下普通班主任；普通班主任仅看自己
    # 头脑风暴阶段：已发生首笔支付，但尚未发生次笔支付（即付款笔数=1）
    payment_count_subquery = db.session.query(
        Payment.lead_id.label('lead_id'),
        func.count(Payment.id).label('payment_count')
    ).group_by(Payment.lead_id).subquery()

    query = Lead.query.filter(
        Lead.supervisor_user_id.in_(teacher_user_ids)
    ).join(Customer, Customer.lead_id == Lead.id).filter(
        Customer.phase == Customer.PHASE_BRAINSTORM
    ).join(
        payment_count_subquery,
        Lead.id == payment_count_subquery.c.lead_id
    ).filter(
        payment_count_subquery.c.payment_count == 1
    )

    # 搜索过滤（学员姓名或家长微信名）
    if search:
        query = query.filter(
            db.or_(
                Lead.student_name.contains(search),
                Lead.parent_wechat_display_name.contains(search)
            )
        )

    # 首笔支付时间筛选
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

            # 查询首笔支付时间在指定范围内的线索
            # 首笔支付时间 = 第一笔付款的 payment_date
            # 使用子查询获取每个线索的首笔付款日期
            subquery = db.session.query(
                Payment.lead_id,
                func.min(Payment.payment_date).label('first_payment_date')
            ).filter(
                Payment.payment_date.isnot(None)
            ).group_by(Payment.lead_id).subquery()

            # 筛选首笔付款日期在范围内的线索
            lead_ids_in_range = db.session.query(subquery.c.lead_id).filter(
                and_(
                    func.date(subquery.c.first_payment_date) >= start_dt,
                    func.date(subquery.c.first_payment_date) <= end_dt
                )
            ).all()

            lead_ids = [lid[0] for lid in lead_ids_in_range]
            if lead_ids:
                query = query.filter(Lead.id.in_(lead_ids))
            else:
                # 如果没有符合条件的线索，返回空结果
                query = query.filter(Lead.id == -1)
        except ValueError:
            pass

    # 分页 - 按定金支付时间倒序（无付款记录则按更新时间）
    first_payment_subquery = db.session.query(
        Payment.lead_id,
        func.min(Payment.payment_date).label('first_payment_date')
    ).group_by(Payment.lead_id).subquery()

    leads = query.outerjoin(
        first_payment_subquery,
        Lead.id == first_payment_subquery.c.lead_id
    ).order_by(
        first_payment_subquery.c.first_payment_date.desc().nullslast(),
        Lead.updated_at.desc()
    ).paginate(
        page=page, per_page=20, error_out=False
    )

    # 计算头脑风暴已过天数（以结论保存时间为起点）
    now = datetime.utcnow()
    for lead in leads.items:
        # 仅用于页面展示：修正被误写成“家长名-学员名妈妈/爸爸”的历史数据
        lead.parent_wechat_display_name_normalized = normalize_parent_wechat_display_name(
            lead.parent_wechat_display_name,
            lead.student_name
        )
        if lead.brainstorm_conclusion_at:
            if lead.brainstorm_topics_at:
                delta_days = max((lead.brainstorm_topics_at - lead.brainstorm_conclusion_at).days, 0)
            else:
                delta_days = max((now - lead.brainstorm_conclusion_at).days, 0)
            lead.brainstorm_days_elapsed = delta_days
        else:
            lead.brainstorm_days_elapsed = None

    # 获取所有销售用户（用于显示）
    sales_users = User.query.filter(
        User.role.in_(['sales_manager', 'salesperson']),
        User.status == True
    ).order_by(User.username).all()

    # 批量查询定金支付日期（首笔付款日期）
    lead_ids = [lead.id for lead in leads.items]
    first_payment_dates = {}
    if lead_ids:
        for lead_id in lead_ids:
            payments = Payment.query.filter_by(lead_id=lead_id).order_by(Payment.payment_date.asc()).limit(1).all()
            if payments and payments[0].payment_date:
                first_payment_dates[lead_id] = payments[0].payment_date

    # 批量查询已指派老师数量（非草稿）
    assigned_counts = {}
    submitted_counts = {}
    if lead_ids:
        counts = db.session.query(
            TopicTask.lead_id,
            func.count(TopicTask.id).label('count')
        ).filter(
            TopicTask.lead_id.in_(lead_ids),
            TopicTask.status != TopicTask.STATUS_DRAFT
        ).group_by(TopicTask.lead_id).all()
        assigned_counts = {lead_id: count for lead_id, count in counts}

        submitted = db.session.query(
            TopicTask.lead_id,
            func.count(TopicSubmission.id).label('count')
        ).join(
            TopicSubmission, TopicSubmission.task_id == TopicTask.id
        ).filter(
            TopicTask.lead_id.in_(lead_ids),
            TopicTask.status != TopicTask.STATUS_DRAFT
        ).group_by(TopicTask.lead_id).all()
        submitted_counts = {lead_id: count for lead_id, count in submitted}

    return render_template('delivery/leads_list.html',
                          leads=leads,
                          search=search,
                          start_date=start_date,
                          end_date=end_date,
                          show_teacher_column=show_teacher_column,
                          sales_users=sales_users,
                          first_payment_dates=first_payment_dates,
                          assigned_counts=assigned_counts,
                         submitted_counts=submitted_counts,
                         teachers=sort_teachers_by_pinyin(
                             User.query.filter(User.role == 'teacher', User.status == True).all()
                         ))

@delivery_bp.route('/leads/<int:lead_id>/topic_tasks', methods=['GET', 'POST'])
@login_required
@teacher_supervisor_required
def manage_topic_tasks(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    if not teacher_can_access_lead_scope(lead):
        return jsonify({'success': False, 'message': '您没有权限访问该线索'}), 403

    if request.method == 'GET':
        tasks = TopicTask.query.filter_by(lead_id=lead.id).all()
        now = datetime.utcnow()
        updated = False
        for task in tasks:
            if task.status == TopicTask.STATUS_DRAFT:
                continue
            submission = TopicSubmission.query.filter_by(task_id=task.id).first()
            if submission:
                if task.status != TopicTask.STATUS_SUBMITTED:
                    task.status = TopicTask.STATUS_SUBMITTED
                    updated = True
            else:
                if task.due_at and task.due_at < now and task.status != TopicTask.STATUS_OVERDUE:
                    task.status = TopicTask.STATUS_OVERDUE
                    updated = True
        if updated:
            db.session.commit()
        response_tasks = []
        for task in tasks:
            if not task.teacher or task.teacher.role != 'teacher' or not task.teacher.status:
                continue
            submission = TopicSubmission.query.filter_by(task_id=task.id).first()
            response_tasks.append({
                'id': task.id,
                'tutor_user_id': task.tutor_user_id,
                'teacher_name': task.teacher.username if task.teacher else '',
                'due_at': task.due_at.isoformat() if task.due_at else None,
                'status': task.status,
                'submitted_at': submission.submitted_at.isoformat() if submission and submission.submitted_at else None,
                'content': submission.content if submission else None
            })
        return jsonify({'success': True, 'tasks': response_tasks})

    data = request.get_json(silent=True) or {}
    raw_teacher_ids = data.get('tutor_user_ids') or []
    teacher_ids = []
    for teacher_id in raw_teacher_ids:
        try:
            teacher_ids.append(int(teacher_id))
        except (TypeError, ValueError):
            return jsonify({'success': False, 'message': '老师参数格式不正确'}), 400
    # 去重并保持顺序
    teacher_ids = list(dict.fromkeys(teacher_ids))
    due_at_str = (data.get('due_at') or '').strip()
    send_flag = data.get('send', True)

    if not teacher_ids:
        return jsonify({'success': False, 'message': '请选择老师'}), 400
    valid_teacher_ids = {
        row.id for row in User.query.with_entities(User.id).filter(
            User.id.in_(teacher_ids),
            User.role == 'teacher',
            User.status == True
        ).all()
    }
    if any(teacher_id not in valid_teacher_ids for teacher_id in teacher_ids):
        return jsonify({'success': False, 'message': '所选老师包含已停用或无效账号'}), 400
    if not due_at_str:
        return jsonify({'success': False, 'message': '请选择截止时间'}), 400

    try:
        due_at = datetime.fromisoformat(due_at_str.replace('T', ' '))
    except ValueError:
        return jsonify({'success': False, 'message': '截止时间格式不正确'}), 400

    existing_tasks = TopicTask.query.filter_by(lead_id=lead.id).all()
    incoming_teacher_ids = set(teacher_ids)

    # 删除未包含在当前选择中的任务
    for task in existing_tasks:
        if task.tutor_user_id not in incoming_teacher_ids:
            TopicSubmission.query.filter_by(task_id=task.id).delete()
            db.session.delete(task)

    created_tasks = []
    for teacher_id in teacher_ids:
        task = TopicTask.query.filter_by(lead_id=lead.id, tutor_user_id=teacher_id).first()
        if task:
            task.due_at = due_at
            task.status = TopicTask.STATUS_PENDING if send_flag else TopicTask.STATUS_DRAFT
        else:
            task = TopicTask(
                lead_id=lead.id,
                tutor_user_id=teacher_id,
                due_at=due_at,
                status=TopicTask.STATUS_PENDING if send_flag else TopicTask.STATUS_DRAFT,
                created_by=current_user.id
            )
            db.session.add(task)
        created_tasks.append(task)

    db.session.commit()

    return jsonify({'success': True, 'message': '指派成功' if send_flag else '保存成功'})

@delivery_bp.route('/tutoring')
@login_required
@teacher_supervisor_required
def tutoring_list():
    """课题辅导交付列表"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    status_filter = request.args.get('status', '', type=str)
    teacher_user_ids = get_visible_teacher_supervisor_ids()
    
    query = TutoringDelivery.query.join(Customer).join(Customer.lead).filter(
        Customer.supervisor_user_id.in_(teacher_user_ids)
    )
    
    # 搜索过滤
    if search:
        from models import Lead
        query = query.filter(Lead.student_name.contains(search))
    
    # 状态过滤
    if status_filter:
        query = query.filter(TutoringDelivery.thesis_status == status_filter)
    
    # 分页
    deliveries = query.order_by(TutoringDelivery.updated_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('delivery/tutoring_list.html', 
                         deliveries=deliveries, 
                         search=search,
                         status_filter=status_filter)

@delivery_bp.route('/tutoring/<int:delivery_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_supervisor_required
def edit_tutoring(delivery_id):
    """编辑课题辅导交付"""
    delivery = TutoringDelivery.query.get_or_404(delivery_id)
    
    # 检查权限
    if delivery.customer.supervisor_user_id not in get_visible_teacher_supervisor_ids():
        flash('您没有权限编辑此交付记录', 'error')
        return redirect(url_for('delivery.tutoring_list'))
    
    if request.method == 'POST':
        completed_sessions = request.form.get('completed_sessions', 0, type=int)
        thesis_status = request.form.get('thesis_status', '').strip()
        last_class_date = request.form.get('last_class_date', '').strip()
        next_class_date = request.form.get('next_class_date', '').strip()
        delivery_notes = request.form.get('delivery_notes', '').strip()
        
        total_sessions = delivery.total_sessions or 6

        # 验证课时数
        if completed_sessions < 0 or completed_sessions > total_sessions:
            flash(f'已上课时数必须在0-{total_sessions}之间', 'error')
            return render_template('delivery/edit_tutoring.html', delivery=delivery)
        
        try:
            # 转换日期
            last_class = None
            next_class = None
            if last_class_date:
                last_class = datetime.strptime(last_class_date, '%Y-%m-%d').date()
            if next_class_date:
                next_class = datetime.strptime(next_class_date, '%Y-%m-%d').date()
            
            # 如果交付备注有变化，添加为沟通记录
            if delivery_notes and delivery_notes != delivery.delivery_notes:
                from communication_utils import CommunicationManager
                CommunicationManager.add_customer_communication(
                    lead_id=delivery.customer.lead_id,
                    customer_id=delivery.customer_id,
                    content=f"交付备注更新：{delivery_notes}",
                    user_id=current_user.id
                )

            # 更新交付信息
            delivery.completed_sessions = completed_sessions
            delivery.remaining_sessions = total_sessions - completed_sessions
            delivery.thesis_status = thesis_status
            delivery.last_class_date = last_class
            delivery.next_class_date = next_class
            delivery.delivery_notes = delivery_notes
            delivery.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash(f'课题辅导交付记录更新成功', 'success')
            return redirect(url_for('delivery.tutoring_list'))
        except ValueError:
            flash('日期格式不正确', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败: {str(e)}', 'error')
    
    return render_template('delivery/edit_tutoring.html', delivery=delivery)

# 赛事管理已迁移到 customer_competitions 表，在客户管理中进行


# ==================== 老师管理功能 ====================

@delivery_bp.route('/teachers')
@login_required
@teacher_supervisor_required
def teacher_list():
    """辅导老师列表（role='teacher'）"""
    # 老师创建人信息已移除，展示全部辅导老师
    user_query = User.query.filter(
        User.role == 'teacher',
        User.status == True
    ).all()
    user_ids = [u.id for u in user_query]

    # 再查询 Teacher 表中对应的老师信息
    teachers = Teacher.query.filter(Teacher.user_id.in_(user_ids)).all() if user_ids else []

    # 统计每个老师负责的学生数
    teacher_stats = {}
    for teacher in teachers:
        student_count = Customer.query.filter_by(tutor_user_id=teacher.user_id).count()
        teacher_stats[teacher.user_id] = student_count

    return render_template('delivery/teacher_list.html',
                         teachers=teachers,
                         teacher_stats=teacher_stats)

@delivery_bp.route('/teachers/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_teacher():
    """创建辅导老师账号 - 免密登录（保存到 User 表，role='teacher'）"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()

        # 验证输入
        if not name or not phone:
            flash('姓名和手机号为必填项', 'error')
            return render_template('delivery/create_teacher.html')

        # 验证手机号格式
        import re
        if not re.match(r'^1[3-9]\d{9}$', phone):
            flash('手机号格式不正确', 'error')
            return render_template('delivery/create_teacher.html')

        # 检查手机号是否已存在（User 表或 Teacher 表）
        if User.query.filter_by(phone=phone).first():
            flash('该手机号已被注册', 'error')
            return render_template('delivery/create_teacher.html')

        try:
            # 创建辅导老师账号（保存到 User 表，role='teacher'）
            user = User(
                username=name,
                phone=phone,
                role='teacher',
                status=True
            )

            db.session.add(user)
            db.session.flush()

            teacher = Teacher(
                user_id=user.id,
                email=email,
                subject=subject
            )
            db.session.add(teacher)
            db.session.commit()

            flash(f'辅导老师账号创建成功！登录手机号：{phone}（免密登录）', 'success')
            return redirect(url_for('delivery.teacher_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}', 'error')

    return render_template('delivery/create_teacher.html')

@delivery_bp.route('/teachers/<int:teacher_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_teacher(teacher_id):
    """编辑辅导老师信息"""
    # teacher_id 是 User.id
    user = User.query.get_or_404(teacher_id)

    # 验证权限：仅允许编辑老师账号
    if user.role != 'teacher':
        flash('您无权编辑此老师信息', 'error')
        return redirect(url_for('delivery.teacher_list'))

    # 获取关联的 Teacher 记录
    teacher = Teacher.query.filter_by(user_id=teacher_id).first_or_404()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()

        if not name:
            flash('姓名不能为空', 'error')
            return render_template('delivery/edit_teacher.html', teacher=teacher, user=user)

        try:
            user.username = name
            teacher.email = email
            teacher.subject = subject
            teacher.updated_at = datetime.utcnow()
            db.session.commit()

            flash('辅导老师信息更新成功', 'success')
            return redirect(url_for('delivery.teacher_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')

    return render_template('delivery/edit_teacher.html', teacher=teacher, user=user)

@delivery_bp.route('/teachers/<int:teacher_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_teacher_status(teacher_id):
    """启用/停用辅导老师账号"""
    # teacher_id 是 User.id
    user = User.query.get_or_404(teacher_id)

    # 验证权限：仅允许操作老师账号
    if user.role != 'teacher':
        return jsonify({'success': False, 'message': '您无权操作此老师账号'}), 403

    try:
        user.status = not user.status
        user.updated_at = datetime.utcnow()
        db.session.commit()

        status_text = '启用' if user.status else '停用'
        return jsonify({'success': True, 'message': f'已{status_text}辅导老师账号', 'status': user.status})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== 班主任文档查看功能 ====================

@delivery_bp.route('/customers/<int:customer_id>/documents')
@login_required
@teacher_supervisor_required
def view_customer_documents(customer_id):
    """班主任查看学生的所有文档"""
    customer = Customer.query.get_or_404(customer_id)

    # 验证权限 - 主管可查看自己及旗下普通班主任客户
    if customer.supervisor_user_id not in get_visible_teacher_supervisor_ids():
        return jsonify({'success': False, 'message': '您无权查看此客户的文档'}), 403

    # 获取所有文档（其他材料允许多份）
    documents = DeliveryDocument.query.filter_by(
        customer_id=customer_id
    ).order_by(DeliveryDocument.created_at.desc()).all()

    # 按文档类型分组并转换为字典
    docs_by_type = {}
    for doc in documents:
        payload = {
            'id': doc.id,
            'file_name': doc.file_name,
            'version': doc.version,
            'created_at': doc.created_at.isoformat(),
            'uploaded_by_name': doc.uploaded_by_name
        }
        if doc.doc_type == 'other_materials':
            docs_by_type.setdefault(doc.doc_type, []).append(payload)
        else:
            if doc.is_latest or doc.doc_type not in docs_by_type:
                docs_by_type[doc.doc_type] = payload

    return jsonify({
        'success': True,
        'documents': docs_by_type
    })


# ==================== 班主任文档上传/删除 ====================

ALLOWED_DOC_EXTENSIONS = {'doc', 'docx', 'pdf', 'ppt', 'pptx'}
MAX_DOC_SIZE = 10 * 1024 * 1024  # 10MB

DOC_TYPE_NAMES = {
    'thesis_draft': '课题初稿',
    'thesis_final': '终稿',
    'presentation': '演示方案',
    'novelty_report': '查新报告',
    'plagiarism_report': '查重报告',
    'evaluation_material': '综评材料',
    'preview_material': '预习材料',
    'other_materials': '其他材料'
}

def allowed_doc_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_DOC_EXTENSIONS

def get_doc_upload_folder():
    upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'documents')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    return upload_folder

@delivery_bp.route('/customers/<int:customer_id>/upload/<doc_type>', methods=['POST'])
@login_required
@teacher_supervisor_required
def upload_customer_document(customer_id, doc_type):
    """班主任上传文档"""
    customer = Customer.query.get_or_404(customer_id)
    if customer.supervisor_user_id not in get_visible_teacher_supervisor_ids():
        return jsonify({'success': False, 'message': '您无权为此客户上传文档'}), 403

    if doc_type not in DOC_TYPE_NAMES:
        return jsonify({'success': False, 'message': '无效的文档类型'}), 400

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'}), 400

    if not allowed_doc_file(file.filename):
        return jsonify({'success': False, 'message': '不支持的文件格式，仅支持: doc, docx, pdf, ppt, pptx'}), 400

    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_DOC_SIZE:
        return jsonify({'success': False, 'message': f'文件大小超过限制（最大{MAX_DOC_SIZE // 1024 // 1024}MB）'}), 400

    try:
        # 从原始文件名提取扩展名；secure_filename 对中文名可能仅返回 "pdf"（无点）
        # 这里保留原始文件名用于展示，保存时仍使用系统生成的安全文件名
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        original_filename = file.filename.replace('\\', '/').split('/')[-1].strip()
        if not original_filename:
            original_filename = secure_filename(file.filename) or f"upload.{file_ext}"

        if doc_type == 'other_materials':
            latest_doc = DeliveryDocument.query.filter_by(
                customer_id=customer_id,
                doc_type=doc_type
            ).order_by(DeliveryDocument.version.desc()).first()
        else:
            latest_doc = DeliveryDocument.query.filter_by(
                customer_id=customer_id,
                doc_type=doc_type,
                is_latest=True
            ).first()

        if doc_type != 'other_materials' and latest_doc:
            old_file_path = latest_doc.file_path
            if os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                except Exception:
                    pass

        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        new_filename = f"{customer_id}_{doc_type}_{timestamp}.{file_ext}"
        upload_folder = get_doc_upload_folder()
        file_path = os.path.join(upload_folder, new_filename)
        file.save(file_path)

        if doc_type != 'other_materials' and latest_doc:
            db.session.delete(latest_doc)

        next_version = 1
        if doc_type == 'other_materials' and latest_doc:
            next_version = (latest_doc.version or 1) + 1

        new_doc = DeliveryDocument(
            customer_id=customer_id,
            doc_type=doc_type,
            file_name=original_filename,
            file_path=file_path,
            file_size=file_size,
            file_ext=file_ext,
            uploaded_by_type='teacher_supervisor',
            uploaded_by_id=current_user.id,
            uploaded_by_name=current_user.username,
            version=next_version,
            is_latest=True,
            description=''
        )

        db.session.add(new_doc)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{DOC_TYPE_NAMES[doc_type]}上传成功',
            'document': {
                'id': new_doc.id,
                'file_name': new_doc.file_name,
                'version': new_doc.version,
                'file_size': new_doc.file_size,
                'created_at': new_doc.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'}), 500

@delivery_bp.route('/documents/<int:doc_id>/delete', methods=['POST'])
@login_required
@teacher_supervisor_required
def delete_customer_document(doc_id):
    """班主任删除文档（仅删除自己上传的）"""
    doc = DeliveryDocument.query.get_or_404(doc_id)
    customer = Customer.query.get_or_404(doc.customer_id)
    if customer.supervisor_user_id not in get_visible_teacher_supervisor_ids():
        return jsonify({'success': False, 'message': '您无权删除此文档'}), 403
    if doc.uploaded_by_type != 'teacher_supervisor':
        return jsonify({'success': False, 'message': '您无权删除该文档'}), 403
    if doc.uploaded_by_id != current_user.id and not current_user.is_teacher_supervisor_manager():
        return jsonify({'success': False, 'message': '您无权删除该文档'}), 403

    try:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        doc_type_name = DOC_TYPE_NAMES.get(doc.doc_type, '文档')
        db.session.delete(doc)
        db.session.commit()
        return jsonify({'success': True, 'message': f'{doc_type_name}删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500

@delivery_bp.route('/documents/<int:doc_id>/download')
@login_required
@teacher_supervisor_required
def download_document(doc_id):
    """班主任下载文档"""
    doc = DeliveryDocument.query.get_or_404(doc_id)

    # 验证权限 - 主管可下载自己及旗下普通班主任客户文档
    customer = Customer.query.get_or_404(doc.customer_id)
    if customer.supervisor_user_id not in get_visible_teacher_supervisor_ids():
        flash('您无权下载此文档', 'error')
        return redirect(url_for('delivery.dashboard'))

    # 检查文件是否存在
    if not os.path.exists(doc.file_path):
        flash('文件不存在', 'error')
        return redirect(url_for('customers.detail', customer_id=doc.customer_id))

    return send_file(doc.file_path, as_attachment=True, download_name=doc.file_name)

