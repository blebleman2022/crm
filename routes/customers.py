from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from functools import wraps
from models import User, Customer, Lead, TutoringDelivery, CompetitionDelivery, db
from sqlalchemy.orm import joinedload
from datetime import datetime, date
from decimal import Decimal

customers_bp = Blueprint('customers', __name__)

def sales_or_admin_required(f):
    """销售管理或管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not (current_user.is_sales() or current_user.is_admin()):
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_teachers():
    """获取所有启用的班主任（包括销售管理角色）"""
    return User.query.filter(
        User.status == True,
        User.role.in_(['teacher', 'sales'])
    ).all()

@customers_bp.route('/list')
@login_required
def list_customers():
    """客户列表"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    teacher_filter = request.args.get('teacher', '', type=str)
    award_filter = request.args.get('award', '', type=str)

    # 时间段筛选参数（按客户新增时间）
    start_date = request.args.get('start_date', '', type=str)
    end_date = request.args.get('end_date', '', type=str)

    query = Customer.query.join(Lead).options(
        db.joinedload(Customer.tutoring_delivery),
        db.joinedload(Customer.competition_delivery)
    )

    # 如果是班主任，只能看到自己负责的客户
    if current_user.role == 'teacher':
        query = query.filter(Customer.teacher_user_id == current_user.id)

    # 搜索过滤
    if search:
        query = query.filter(
            (Lead.student_name.contains(search)) |
            (Lead.contact_info.contains(search))
        )

    # 班主任过滤（仅对非班主任角色有效）
    if teacher_filter and current_user.role != 'teacher':
        query = query.filter(Customer.teacher_user_id == teacher_filter)

    # 奖项要求过滤（从线索表读取）
    if award_filter:
        query = query.filter(Lead.competition_award_level == award_filter)

    # 时间段筛选（按客户新增时间）
    if start_date and end_date:
        try:
            from sqlalchemy import func, and_
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

            query = query.filter(
                and_(
                    func.date(Customer.created_at) >= start_dt,
                    func.date(Customer.created_at) <= end_dt
                )
            )
        except ValueError:
            pass

    # 分页
    customers = query.order_by(Customer.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    # 获取所有班主任用于筛选（包括销售管理角色）
    teachers = get_teachers()

    return render_template('customers/list.html',
                         customers=customers,
                         search=search,
                         teacher_filter=teacher_filter,
                         award_filter=award_filter,
                         teachers=teachers,
                         start_date=start_date,
                         end_date=end_date)

@customers_bp.route('/<int:customer_id>/detail')
@login_required
def customer_detail(customer_id):
    """客户详情"""
    customer = Customer.query.get_or_404(customer_id)

    # 如果是班主任，只能查看自己负责的客户
    if current_user.role == 'teacher' and customer.teacher_user_id != current_user.id:
        flash('您没有权限查看此客户', 'error')
        return redirect(url_for('customers.list_customers'))

    return render_template('customers/detail.html', customer=customer)

@customers_bp.route('/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
@sales_or_admin_required
def edit_customer(customer_id):
    """编辑客户"""
    customer = Customer.query.get_or_404(customer_id)

    if request.method == 'POST':
        # 获取表单数据
        student_name = request.form.get('student_name', '').strip()
        contact_info = request.form.get('contact_info', '').strip()
        sales_user_id = request.form.get('sales_user_id', type=int)
        teacher_user_id = request.form.get('teacher_user_id', type=int)
        competition_award_level = request.form.get('competition_award_level', '').strip()
        additional_requirements = request.form.get('additional_requirements', '').strip()
        exam_year = request.form.get('exam_year', type=int)
        notes = request.form.get('notes', '').strip()

        # 验证必填字段
        required_fields = [student_name, contact_info, sales_user_id, exam_year]

        if not all(required_fields):
            flash('请填写所有必填字段', 'error')
            sales_users = User.query.filter_by(role='sales', status=True).all()
            teacher_users = get_teachers()
            return render_template('customers/edit.html', customer=customer,
                                 sales_users=sales_users, teacher_users=teacher_users)

        # 验证销售用户
        sales_user = User.query.filter_by(id=sales_user_id, role='sales', status=True).first()
        if not sales_user:
            flash('选择的销售用户无效', 'error')
            sales_users = User.query.filter_by(role='sales', status=True).all()
            teacher_users = get_teachers()
            return render_template('customers/edit.html', customer=customer,
                                 sales_users=sales_users, teacher_users=teacher_users)

        # 验证班主任（可选）- 允许销售管理和班主任角色
        if teacher_user_id:
            teacher = User.query.filter(
                User.id == teacher_user_id,
                User.role.in_(['teacher', 'sales']),
                User.status == True
            ).first()
            if not teacher:
                flash('选择的班主任无效', 'error')
                sales_users = User.query.filter_by(role='sales', status=True).all()
                teacher_users = get_teachers()
                return render_template('customers/edit.html', customer=customer,
                                     sales_users=sales_users, teacher_users=teacher_users)

        try:
            # 更新线索信息
            customer.lead.student_name = student_name
            customer.lead.contact_info = contact_info
            customer.lead.sales_user_id = sales_user_id
            customer.lead.updated_at = datetime.utcnow()

            # 更新客户信息
            customer.teacher_user_id = teacher_user_id if teacher_user_id else None
            customer.competition_award_level = competition_award_level if competition_award_level else None
            customer.additional_requirements = additional_requirements if additional_requirements else None
            customer.exam_year = exam_year

            # 如果备注有变化，添加为沟通记录
            if notes and notes != customer.customer_notes:
                from communication_utils import CommunicationManager
                CommunicationManager.add_customer_communication(
                    lead_id=customer.lead_id,
                    customer_id=customer.id,
                    content=f"客户信息更新备注：{notes}"
                )

            customer.customer_notes = notes
            customer.updated_at = datetime.utcnow()

            # 如果分配了班主任，创建对应的交付记录
            if teacher_user_id and not customer.tutoring_delivery:
                tutoring_delivery = TutoringDelivery(customer_id=customer.id)
                db.session.add(tutoring_delivery)

            if teacher_user_id and not customer.competition_delivery:
                competition_delivery = CompetitionDelivery(customer_id=customer.id)
                db.session.add(competition_delivery)

            db.session.commit()
            flash(f'客户 {customer.lead.student_name} 更新成功', 'success')
            return redirect(url_for('customers.list_customers'))
        except Exception as e:
            db.session.rollback()
            flash(f'更新客户失败: {str(e)}', 'error')

    # GET 请求，显示编辑表单
    sales_users = User.query.filter_by(role='sales', status=True).all()
    teacher_users = get_teachers()
    return render_template('customers/edit.html', customer=customer,
                         sales_users=sales_users, teacher_users=teacher_users)

@customers_bp.route('/<int:customer_id>/assign_teacher', methods=['POST'])
@login_required
@sales_or_admin_required
def assign_teacher(customer_id):
    """分配班主任"""
    customer = Customer.query.get_or_404(customer_id)
    teacher_id = request.json.get('teacher_id')

    if not teacher_id:
        return jsonify({'success': False, 'message': '请选择班主任'})

    # 允许销售管理和班主任角色被分配为班主任
    teacher = User.query.filter(
        User.id == teacher_id,
        User.role.in_(['teacher', 'sales']),
        User.status == True
    ).first()
    if not teacher:
        return jsonify({'success': False, 'message': '选择的班主任无效'})
    
    try:
        customer.teacher_user_id = teacher_id
        customer.updated_at = datetime.utcnow()
        
        # 创建交付记录
        if not customer.tutoring_delivery:
            tutoring_delivery = TutoringDelivery(customer_id=customer.id)
            db.session.add(tutoring_delivery)
        
        if not customer.competition_delivery:
            competition_delivery = CompetitionDelivery(customer_id=customer.id)
            db.session.add(competition_delivery)
        
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': f'已将客户 {customer.lead.student_name} 分配给班主任 {teacher.username}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'分配失败: {str(e)}'})

@customers_bp.route('/<int:customer_id>/progress')
@login_required
def get_customer_progress(customer_id):
    """获取客户进度信息"""
    customer = Customer.query.get_or_404(customer_id)

    # 构建返回数据
    customer_data = {
        'id': customer.id,
        'lead_id': customer.lead_id,
        'student_name': customer.lead.student_name,
        'customer_notes': customer.customer_notes,
        'is_priority': customer.is_priority,
        'tutoring_delivery': None,
        'competition_delivery': None
    }

    # 课程进度信息
    if customer.tutoring_delivery:
        customer_data['tutoring_delivery'] = {
            'total_sessions': customer.tutoring_delivery.total_sessions,
            'completed_sessions': customer.tutoring_delivery.completed_sessions,
        }

    # 奖项完成信息
    if customer.competition_delivery:
        customer_data['competition_delivery'] = {
            'delivery_status': customer.competition_delivery.delivery_status,
            'award_obtained_at': customer.competition_delivery.award_obtained_at.isoformat() if customer.competition_delivery.award_obtained_at else None
        }

    return jsonify({'success': True, 'customer': customer_data})

@customers_bp.route('/<int:customer_id>/api')
@login_required
def customer_api(customer_id):
    """客户API详情 - 用于弹窗显示"""
    customer = Customer.query.get_or_404(customer_id)

    # 权限检查：班主任只能查看自己负责的客户
    if current_user.role == 'teacher' and customer.teacher_user_id != current_user.id:
        return jsonify({
            'success': False,
            'message': '您没有权限查看此客户'
        }), 403

    # 计算已付款总额
    from models import Payment
    payments = Payment.query.filter_by(lead_id=customer.lead_id).all()
    paid_amount = sum(payment.amount for payment in payments) if payments else 0

    customer_data = {
        'id': customer.id,
        'student_name': customer.lead.student_name,
        'parent_wechat_display_name': customer.lead.parent_wechat_display_name,
        'parent_wechat_name': customer.lead.parent_wechat_name,
        'contact_info': customer.lead.contact_info,
        'grade': customer.lead.grade,
        'school': customer.lead.school,
        'district': customer.lead.district,
        'sales_user': customer.lead.sales_user.username if customer.lead.sales_user else None,
        'teacher_user': customer.teacher_user.username if customer.teacher_user else None,
        'service_types': customer.lead.get_service_types_list(),
        'competition_award_level': customer.competition_award_level,
        'additional_requirements': customer.additional_requirements,
        'exam_year': customer.exam_year,
        'notes': customer.customer_notes,
        'created_at': customer.created_at.isoformat() if customer.created_at else None,
        'updated_at': customer.updated_at.isoformat() if customer.updated_at else None
    }

    # 辅导交付状态
    if customer.tutoring_delivery:
        customer_data['tutoring_delivery'] = {
            'thesis_status': customer.tutoring_delivery.thesis_status,
            'total_sessions': customer.tutoring_delivery.total_sessions,
            'completed_sessions': customer.tutoring_delivery.completed_sessions,
            'thesis_completed_at': customer.tutoring_delivery.thesis_completed_at.isoformat() if customer.tutoring_delivery.thesis_completed_at else None
        }

    # 竞赛交付状态
    if customer.competition_delivery:
        customer_data['competition_delivery'] = {
            'delivery_status': customer.competition_delivery.delivery_status,
            'award_obtained_at': customer.competition_delivery.award_obtained_at.isoformat() if customer.competition_delivery.award_obtained_at else None
        }

    return jsonify({'success': True, 'customer': customer_data})

@customers_bp.route('/<int:customer_id>/update_progress', methods=['POST'])
@login_required
def update_customer_progress(customer_id):
    """更新客户进度"""
    customer = Customer.query.get_or_404(customer_id)

    try:
        data = request.get_json()
        total_sessions = data.get('total_sessions', 0)
        completed_sessions = data.get('completed_sessions', 0)
        award_status = data.get('award_status', '未报名')
        notes = data.get('notes', '')

        # 如果备注有变化，添加为沟通记录
        if notes and notes != customer.customer_notes:
            from communication_utils import CommunicationManager
            CommunicationManager.add_customer_communication(
                lead_id=customer.lead_id,
                customer_id=customer.id,
                content=f"进度更新备注：{notes}"
            )

        # 更新客户备注
        customer.customer_notes = notes
        customer.updated_at = datetime.utcnow()

        # 更新或创建课程进度记录
        if not customer.tutoring_delivery:
            tutoring_delivery = TutoringDelivery(customer_id=customer.id)
            db.session.add(tutoring_delivery)
            customer.tutoring_delivery = tutoring_delivery

        customer.tutoring_delivery.total_sessions = total_sessions
        customer.tutoring_delivery.completed_sessions = completed_sessions
        customer.tutoring_delivery.update_remaining_sessions()
        customer.tutoring_delivery.updated_at = datetime.utcnow()

        # 更新或创建奖项状态记录
        # 检查是否有竞赛服务类型且有奖项等级要求
        has_competition = 'competition' in customer.get_service_types()
        has_award_requirement = customer.competition_award_level and customer.competition_award_level != '无'

        if has_competition and has_award_requirement:
            if not customer.competition_delivery:
                competition_delivery = CompetitionDelivery(customer_id=customer.id)
                db.session.add(competition_delivery)
                customer.competition_delivery = competition_delivery

            # 根据奖项状态更新记录
            if award_status == '已获奖':
                if not customer.competition_delivery.award_obtained_at:
                    customer.competition_delivery.award_obtained_at = datetime.utcnow()
                customer.competition_delivery.delivery_status = '已完成'
            elif award_status == '已报名':
                customer.competition_delivery.award_obtained_at = None
                customer.competition_delivery.delivery_status = '已报名待竞赛'
            else:  # 未报名
                customer.competition_delivery.award_obtained_at = None
                customer.competition_delivery.delivery_status = '未报名'

            customer.competition_delivery.updated_at = datetime.utcnow()

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'客户 {customer.lead.student_name} 的进度已更新'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@customers_bp.route('/<int:customer_id>/toggle_priority', methods=['POST'])
@login_required
def toggle_customer_priority(customer_id):
    """切换客户重点关注状态"""
    try:
        customer = Customer.query.get_or_404(customer_id)

        # 获取请求数据
        data = request.get_json()
        is_priority = data.get('is_priority', False)

        # 更新客户重点关注状态
        customer.is_priority = is_priority
        customer.updated_at = datetime.utcnow()

        db.session.commit()

        # 记录操作日志
        action = '标记为重点关注客户' if is_priority else '取消重点关注标记'
        print(f"用户 {session.get('user_id')} 对客户 {customer.lead.student_name} 执行了操作: {action}")

        return jsonify({
            'success': True,
            'is_priority': customer.is_priority,
            'message': f'客户 {customer.lead.student_name} 已{"标记为重点关注" if is_priority else "取消重点关注标记"}'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})
