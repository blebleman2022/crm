from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from functools import wraps
from models import User, Customer, Lead, TutoringDelivery, CompetitionDelivery, CustomerCompetition, CompetitionName, CourseRecordImage, AwardCertificateImage, db
from sqlalchemy.orm import joinedload
from datetime import datetime, date
from decimal import Decimal
import os
from werkzeug.utils import secure_filename

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
    """获取所有启用的班主任"""
    return User.query.filter(
        User.status == True,
        User.role == 'teacher_supervisor'
    ).all()

@customers_bp.route('/list')
@login_required
def list_customers():
    """客户列表"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    sales_filter = request.args.get('sales', '', type=str)  # 销售筛选
    service_type = request.args.get('service_type', '', type=str)  # 服务类型筛选
    completed = request.args.get('completed', '', type=str)  # 已完成筛选

    # 时间段筛选参数（按客户新增时间）
    start_date = request.args.get('start_date', '', type=str)
    end_date = request.args.get('end_date', '', type=str)

    # 如果只填了开始日期，结束日期默认为当天
    if start_date and not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    query = Customer.query.join(Lead).options(
        db.joinedload(Customer.tutoring_delivery),
        db.joinedload(Customer.competition_delivery)
    )

    # 权限控制
    if current_user.role == 'teacher_supervisor':
        # 班主任只能看到自己负责的客户
        query = query.filter(Customer.teacher_user_id == current_user.id)
    elif current_user.is_salesperson():
        # 销售角色只能看到自己负责且已分配班主任的客户
        query = query.filter(
            (Lead.sales_user_id == current_user.id) &
            (Customer.teacher_user_id.isnot(None))
        )
    elif current_user.is_sales_manager():
        # 销售管理可以看到所有销售和销售管理负责的客户（参照线索列表逻辑）
        allowed_ids = db.session.query(User.id).filter(
            User.role.in_(['sales_manager', 'salesperson']),
            User.status == True
        ).subquery()
        query = query.filter(Lead.sales_user_id.in_(allowed_ids))
    # 管理员可以看到所有客户，不需要额外过滤

    # 搜索过滤
    if search:
        query = query.filter(
            (Lead.student_name.contains(search)) |
            (Lead.contact_info.contains(search))
        )

    # 销售筛选
    if sales_filter:
        query = query.filter(Lead.sales_user_id == sales_filter)

    # 服务类型筛选
    if service_type == 'tutoring':
        # 筛选有课题辅导服务的客户
        query = query.filter(Lead.service_types.contains('tutoring'))
    elif service_type == 'competition':
        # 筛选有竞赛辅导服务的客户
        query = query.filter(Lead.service_types.contains('competition'))
    elif service_type == 'upgrade_guidance':
        # 筛选有升学陪跑服务的客户
        query = query.filter(Lead.service_types.contains('upgrade_guidance'))

    # 已完成筛选
    if completed == 'true':
        # 筛选已完成的客户（课题辅导已完成或竞赛辅导已完成）
        query = query.filter(
            (TutoringDelivery.thesis_status == '已完成') |
            (CompetitionDelivery.delivery_status == '服务完结')
        )

    # 时间段筛选（按客户新增时间）
    if start_date:
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

    # 分页 - 按次笔付款时间倒序排列（NULL值排最后），相同时间按客户创建时间倒序
    customers = query.order_by(
        Lead.second_payment_at.desc().nullslast(),
        Customer.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)

    # 获取所有销售用户用于筛选
    sales_users = User.query.filter(
        User.role.in_(['sales_manager', 'salesperson']),
        User.status == True
    ).order_by(User.username).all()

    # 为当前页的客户批量查询次笔付款时间（性能优化）
    from models import Payment
    from sqlalchemy import func

    # 获取当前页所有客户的lead_id
    lead_ids = [customer.lead_id for customer in customers.items]

    # 批量查询每个线索的次笔付款时间
    # 使用子查询找出每个线索的第二笔付款
    second_payments = {}
    if lead_ids:
        # 为每个lead_id查询第二笔付款
        for lead_id in lead_ids:
            payments = Payment.query.filter_by(lead_id=lead_id).order_by(Payment.payment_date.asc()).limit(2).all()
            if len(payments) >= 2:
                second_payments[lead_id] = payments[1].payment_date

    # 批量查询每个客户的赛事数量
    customer_ids = [customer.id for customer in customers.items]
    competition_counts = {}
    if customer_ids:
        from sqlalchemy import func
        counts = db.session.query(
            CustomerCompetition.customer_id,
            func.count(CustomerCompetition.id).label('count')
        ).filter(
            CustomerCompetition.customer_id.in_(customer_ids)
        ).group_by(CustomerCompetition.customer_id).all()

        competition_counts = {customer_id: count for customer_id, count in counts}

    return render_template('customers/list.html',
                         customers=customers,
                         search=search,
                         sales_filter=sales_filter,
                         service_type=service_type,
                         completed=completed,
                         sales_users=sales_users,
                         start_date=start_date,
                         end_date=end_date,
                         second_payments=second_payments,
                         competition_counts=competition_counts)

@customers_bp.route('/<int:customer_id>/detail')
@login_required
def customer_detail(customer_id):
    """客户详情"""
    customer = Customer.query.get_or_404(customer_id)

    # 如果是班主任，只能查看自己负责的客户
    if current_user.role == 'teacher_supervisor' and customer.teacher_user_id != current_user.id:
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
                    content=f"客户信息更新备注：{notes}",
                    user_id=current_user.id
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
        'thesis_name': customer.thesis_name,  # 添加课题名称
        'service_types': customer.get_service_types(),  # 添加服务类型信息
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
    if current_user.role == 'teacher_supervisor' and customer.teacher_user_id != current_user.id:
        return jsonify({
            'success': False,
            'message': '您没有权限查看此客户'
        }), 403

    # 计算已付款总额
    from models import Payment
    payments = Payment.query.filter_by(lead_id=customer.lead_id).all()
    paid_amount = sum(payment.amount for payment in payments) if payments else 0

    # 获取客户阶段沟通记录
    from communication_utils import CommunicationManager
    communications = CommunicationManager.get_customer_communications(customer_id)
    communications_data = [{
        'id': comm.id,
        'content': comm.content,
        'created_at': comm.created_at.strftime('%Y-%m-%d %H:%M') if comm.created_at else None,
        'user_name': comm.user.username if comm.user else None,
        'user_role': comm.user.role if comm.user else None
    } for comm in communications]

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
        'thesis_name': customer.thesis_name,  # 添加课题名称
        'notes': customer.customer_notes,
        'communications': communications_data,
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
        notes = data.get('notes', '')
        thesis_name = data.get('thesis_name', '')

        # 如果备注有变化，添加为沟通记录
        if notes and notes != customer.customer_notes:
            from communication_utils import CommunicationManager
            CommunicationManager.add_customer_communication(
                lead_id=customer.lead_id,
                customer_id=customer.id,
                content=f"进度更新备注：{notes}",
                user_id=current_user.id
            )

        # 更新客户备注和课题名
        customer.customer_notes = notes
        customer.thesis_name = thesis_name if thesis_name else None
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

# ==================== 赛事管理 API ====================

@customers_bp.route('/api/<int:customer_id>/competitions', methods=['GET'])
@login_required
def get_customer_competitions(customer_id):
    """获取客户的所有赛事"""
    try:
        customer = Customer.query.get_or_404(customer_id)

        # 权限检查：班主任只能查看自己负责的客户
        if current_user.role == 'teacher_supervisor' and customer.teacher_user_id != current_user.id:
            return jsonify({'success': False, 'message': '无权限查看此客户的赛事'}), 403

        # 获取客户的所有赛事
        competitions = CustomerCompetition.query.filter_by(customer_id=customer_id)\
            .order_by(CustomerCompetition.created_at.desc()).all()

        # 构建返回数据
        data = []
        for comp in competitions:
            data.append({
                'id': comp.id,
                'competition_name': comp.competition_name.name,
                'competition_name_id': comp.competition_name_id,
                'status': comp.status,
                'custom_award': comp.custom_award,
                'display_status': comp.get_display_status(),
                'status_color': comp.get_status_color(),
                'created_at': comp.created_at.strftime('%Y-%m-%d %H:%M:%S') if comp.created_at else None
            })

        return jsonify({
            'success': True,
            'competitions': data,
            'count': len(data)
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'获取赛事列表失败: {str(e)}'}), 500

@customers_bp.route('/api/<int:customer_id>/competitions', methods=['POST'])
@login_required
def add_customer_competition(customer_id):
    """为客户添加赛事"""
    try:
        customer = Customer.query.get_or_404(customer_id)

        # 权限检查：只有班主任可以添加赛事
        if current_user.role != 'teacher_supervisor':
            return jsonify({'success': False, 'message': '只有班主任可以添加赛事'}), 403

        # 权限检查：班主任只能为自己负责的客户添加赛事
        if customer.teacher_user_id != current_user.id:
            return jsonify({'success': False, 'message': '无权限为此客户添加赛事'}), 403

        data = request.get_json()
        competition_name_id = data.get('competition_name_id')
        status = data.get('status', '未报名')
        custom_award = data.get('custom_award')

        # 验证必填字段
        if not competition_name_id:
            return jsonify({'success': False, 'message': '请选择赛事名称'}), 400

        # 验证赛事名称是否存在
        competition_name = CompetitionName.query.get(competition_name_id)
        if not competition_name:
            return jsonify({'success': False, 'message': '赛事名称不存在'}), 400

        # 检查是否已经添加过该赛事
        existing = CustomerCompetition.query.filter_by(
            customer_id=customer_id,
            competition_name_id=competition_name_id
        ).first()

        if existing:
            return jsonify({'success': False, 'message': '该客户已添加过此赛事'}), 400

        # 验证状态值
        valid_statuses = ['未报名', '已报名', '国家一等奖', '国家二等奖', '国家三等奖',
                         '市级一等奖', '市级二等奖', '市级三等奖', '其他奖项']
        if status not in valid_statuses:
            return jsonify({'success': False, 'message': '无效的状态值'}), 400

        # 如果是"其他奖项"，验证自定义奖项名称
        if status == '其他奖项' and not custom_award:
            return jsonify({'success': False, 'message': '请输入自定义奖项名称'}), 400

        # 创建新赛事记录
        new_competition = CustomerCompetition(
            customer_id=customer_id,
            competition_name_id=competition_name_id,
            status=status,
            custom_award=custom_award if status == '其他奖项' else None,
            created_by_user_id=current_user.id
        )

        db.session.add(new_competition)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '赛事添加成功',
            'competition': {
                'id': new_competition.id,
                'competition_name': competition_name.name,
                'status': new_competition.status,
                'custom_award': new_competition.custom_award,
                'display_status': new_competition.get_display_status(),
                'status_color': new_competition.get_status_color()
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'添加赛事失败: {str(e)}'}), 500

@customers_bp.route('/api/competitions/<int:competition_id>', methods=['PUT'])
@login_required
def update_competition_status(competition_id):
    """更新赛事状态"""
    try:
        competition = CustomerCompetition.query.get_or_404(competition_id)

        # 权限检查：只有班主任可以更新赛事状态
        if current_user.role != 'teacher_supervisor':
            return jsonify({'success': False, 'message': '只有班主任可以更新赛事状态'}), 403

        # 权限检查：班主任只能更新自己负责的客户的赛事
        if competition.customer.teacher_user_id != current_user.id:
            return jsonify({'success': False, 'message': '无权限更新此赛事'}), 403

        data = request.get_json()
        new_status = data.get('status')
        custom_award = data.get('custom_award')

        # 验证状态值
        valid_statuses = ['未报名', '已报名', '国家一等奖', '国家二等奖', '国家三等奖',
                         '市级一等奖', '市级二等奖', '市级三等奖', '其他奖项']
        if new_status not in valid_statuses:
            return jsonify({'success': False, 'message': '无效的状态值'}), 400

        # 如果是"其他奖项"，验证自定义奖项名称
        if new_status == '其他奖项' and not custom_award:
            return jsonify({'success': False, 'message': '请输入自定义奖项名称'}), 400

        # 更新状态
        competition.status = new_status
        competition.custom_award = custom_award if new_status == '其他奖项' else None
        competition.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '状态更新成功',
            'competition': {
                'id': competition.id,
                'status': competition.status,
                'custom_award': competition.custom_award,
                'display_status': competition.get_display_status(),
                'status_color': competition.get_status_color()
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新状态失败: {str(e)}'}), 500

@customers_bp.route('/api/competitions/<int:competition_id>', methods=['DELETE'])
@login_required
def delete_competition(competition_id):
    """删除赛事"""
    try:
        competition = CustomerCompetition.query.get_or_404(competition_id)

        # 权限检查：只有班主任可以删除赛事
        if current_user.role != 'teacher_supervisor':
            return jsonify({'success': False, 'message': '只有班主任可以删除赛事'}), 403

        # 权限检查：班主任只能删除自己负责的客户的赛事
        if competition.customer.teacher_user_id != current_user.id:
            return jsonify({'success': False, 'message': '无权限删除此赛事'}), 403

        competition_name = competition.competition_name.name

        db.session.delete(competition)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'赛事"{competition_name}"已删除'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除赛事失败: {str(e)}'}), 500

@customers_bp.route('/api/competition-names', methods=['GET'])
@login_required
def get_competition_names():
    """获取所有赛事名称（用于下拉选择）"""
    try:
        competition_names = CompetitionName.query.order_by(CompetitionName.name).all()

        data = [{'id': cn.id, 'name': cn.name} for cn in competition_names]

        return jsonify({
            'success': True,
            'competition_names': data
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'获取赛事名称失败: {str(e)}'}), 500


# ========== 客户图片上传相关 ==========

# 图片上传相关配置
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_IMAGES_PER_CUSTOMER = 10  # 每个客户每种类型最多10张图片
COURSE_RECORD_UPLOAD_FOLDER = 'static/uploads/course_records'
AWARD_CERTIFICATE_UPLOAD_FOLDER = 'static/uploads/award_certificates'

def allowed_image_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

@customers_bp.route('/<int:customer_id>/upload-course-record-image', methods=['POST'])
@login_required
def upload_course_record_image(customer_id):
    """上传课程记录图片"""
    customer = Customer.query.get_or_404(customer_id)

    # 权限检查：只有班主任可以上传
    if current_user.role != 'teacher_supervisor':
        return jsonify({'success': False, 'message': '只有班主任可以上传图片'}), 403

    # 权限检查：只能为自己负责的客户上传图片
    if customer.teacher_user_id != current_user.id:
        return jsonify({'success': False, 'message': '您只能为自己负责的客户上传图片'}), 403

    # 检查当前图片数量
    current_image_count = CourseRecordImage.query.filter_by(customer_id=customer_id).count()
    if current_image_count >= MAX_IMAGES_PER_CUSTOMER:
        return jsonify({'success': False, 'message': f'最多只能上传{MAX_IMAGES_PER_CUSTOMER}张图片'}), 400

    # 检查是否有文件
    if 'images' not in request.files:
        return jsonify({'success': False, 'message': '请选择要上传的图片'}), 400

    files = request.files.getlist('images')
    descriptions = request.form.getlist('descriptions')

    if not files or files[0].filename == '':
        return jsonify({'success': False, 'message': '请选择要上传的图片'}), 400

    # 检查上传数量
    if len(files) + current_image_count > MAX_IMAGES_PER_CUSTOMER:
        return jsonify({'success': False, 'message': f'最多只能上传{MAX_IMAGES_PER_CUSTOMER}张图片，当前已有{current_image_count}张'}), 400

    try:
        # 确保上传目录存在
        os.makedirs(COURSE_RECORD_UPLOAD_FOLDER, exist_ok=True)

        uploaded_images = []

        for idx, file in enumerate(files):
            # 检查文件类型
            if not allowed_image_file(file.filename):
                continue

            # 检查文件大小
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)

            if file_size > MAX_IMAGE_SIZE:
                return jsonify({'success': False, 'message': f'图片 {file.filename} 超过5MB限制'}), 400

            # 生成安全的文件名
            original_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"customer_{customer_id}_course_{timestamp}_{idx}_{original_filename}"
            filepath = os.path.join(COURSE_RECORD_UPLOAD_FOLDER, filename)

            # 保存文件
            file.save(filepath)

            # 获取对应的描述
            description = descriptions[idx] if idx < len(descriptions) else ''

            # 保存到数据库
            image = CourseRecordImage(
                customer_id=customer_id,
                image_path=f'uploads/course_records/{filename}',
                description=description.strip(),
                file_size=file_size,
                file_name=original_filename
            )
            db.session.add(image)
            uploaded_images.append({
                'id': image.id,
                'filename': original_filename,
                'description': description
            })

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'成功上传 {len(uploaded_images)} 张图片',
            'images': uploaded_images
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'}), 500

@customers_bp.route('/<int:customer_id>/upload-award-certificate-image', methods=['POST'])
@login_required
def upload_award_certificate_image(customer_id):
    """上传获奖证书图片"""
    customer = Customer.query.get_or_404(customer_id)

    # 权限检查：只有班主任可以上传
    if current_user.role != 'teacher_supervisor':
        return jsonify({'success': False, 'message': '只有班主任可以上传图片'}), 403

    # 权限检查：只能为自己负责的客户上传图片
    if customer.teacher_user_id != current_user.id:
        return jsonify({'success': False, 'message': '您只能为自己负责的客户上传图片'}), 403

    # 检查当前图片数量
    current_image_count = AwardCertificateImage.query.filter_by(customer_id=customer_id).count()
    if current_image_count >= MAX_IMAGES_PER_CUSTOMER:
        return jsonify({'success': False, 'message': f'最多只能上传{MAX_IMAGES_PER_CUSTOMER}张图片'}), 400

    # 检查是否有文件
    if 'images' not in request.files:
        return jsonify({'success': False, 'message': '请选择要上传的图片'}), 400

    files = request.files.getlist('images')
    descriptions = request.form.getlist('descriptions')

    if not files or files[0].filename == '':
        return jsonify({'success': False, 'message': '请选择要上传的图片'}), 400

    # 检查上传数量
    if len(files) + current_image_count > MAX_IMAGES_PER_CUSTOMER:
        return jsonify({'success': False, 'message': f'最多只能上传{MAX_IMAGES_PER_CUSTOMER}张图片，当前已有{current_image_count}张'}), 400

    try:
        # 确保上传目录存在
        os.makedirs(AWARD_CERTIFICATE_UPLOAD_FOLDER, exist_ok=True)

        uploaded_images = []

        for idx, file in enumerate(files):
            # 检查文件类型
            if not allowed_image_file(file.filename):
                continue

            # 检查文件大小
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)

            if file_size > MAX_IMAGE_SIZE:
                return jsonify({'success': False, 'message': f'图片 {file.filename} 超过5MB限制'}), 400

            # 生成安全的文件名
            original_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"customer_{customer_id}_award_{timestamp}_{idx}_{original_filename}"
            filepath = os.path.join(AWARD_CERTIFICATE_UPLOAD_FOLDER, filename)

            # 保存文件
            file.save(filepath)

            # 获取对应的描述
            description = descriptions[idx] if idx < len(descriptions) else ''

            # 保存到数据库
            image = AwardCertificateImage(
                customer_id=customer_id,
                image_path=f'uploads/award_certificates/{filename}',
                description=description.strip(),
                file_size=file_size,
                file_name=original_filename
            )
            db.session.add(image)
            uploaded_images.append({
                'id': image.id,
                'filename': original_filename,
                'description': description
            })

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'成功上传 {len(uploaded_images)} 张图片',
            'images': uploaded_images
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'}), 500

@customers_bp.route('/delete-course-record-image/<int:image_id>', methods=['POST'])
@login_required
def delete_course_record_image(image_id):
    """删除课程记录图片"""
    try:
        image = CourseRecordImage.query.get_or_404(image_id)
        customer = Customer.query.get_or_404(image.customer_id)

        # 权限检查：只有班主任可以删除
        if current_user.role != 'teacher_supervisor':
            return jsonify({'success': False, 'message': '只有班主任可以删除图片'}), 403

        # 权限检查：只能删除自己负责的客户的图片
        if customer.teacher_user_id != current_user.id:
            return jsonify({'success': False, 'message': '您只能删除自己负责的客户的图片'}), 403

        # 1. 先记录文件路径
        filepath = os.path.join('static', image.image_path)

        # 2. 删除数据库记录（先删除数据库，保证数据一致性）
        db.session.delete(image)
        db.session.commit()

        # 3. 最后删除文件（即使失败也不影响数据一致性）
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                import logging
                logging.warning(f"文件删除失败: {filepath}, 错误: {e}")

        return jsonify({'success': True, 'message': '图片已删除'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500

@customers_bp.route('/delete-award-certificate-image/<int:image_id>', methods=['POST'])
@login_required
def delete_award_certificate_image(image_id):
    """删除获奖证书图片"""
    try:
        image = AwardCertificateImage.query.get_or_404(image_id)
        customer = Customer.query.get_or_404(image.customer_id)

        # 权限检查：只有班主任可以删除
        if current_user.role != 'teacher_supervisor':
            return jsonify({'success': False, 'message': '只有班主任可以删除图片'}), 403

        # 权限检查：只能删除自己负责的客户的图片
        if customer.teacher_user_id != current_user.id:
            return jsonify({'success': False, 'message': '您只能删除自己负责的客户的图片'}), 403

        # 1. 先记录文件路径
        filepath = os.path.join('static', image.image_path)

        # 2. 删除数据库记录（先删除数据库，保证数据一致性）
        db.session.delete(image)
        db.session.commit()

        # 3. 最后删除文件（即使失败也不影响数据一致性）
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                import logging
                logging.warning(f"文件删除失败: {filepath}, 错误: {e}")

        return jsonify({'success': True, 'message': '图片已删除'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500

@customers_bp.route('/<int:customer_id>/course-record-images', methods=['GET'])
@login_required
def get_course_record_images(customer_id):
    """获取客户的课程记录图片列表"""
    try:
        customer = Customer.query.get_or_404(customer_id)

        images = CourseRecordImage.query.filter_by(customer_id=customer_id).order_by(CourseRecordImage.created_at.desc()).all()

        data = [{
            'id': img.id,
            'image_path': img.image_path,
            'description': img.description,
            'file_name': img.file_name,
            'file_size': img.get_file_size_display(),
            'created_at': img.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for img in images]

        return jsonify({
            'success': True,
            'images': data
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'获取图片失败: {str(e)}'}), 500

@customers_bp.route('/<int:customer_id>/award-certificate-images', methods=['GET'])
@login_required
def get_award_certificate_images(customer_id):
    """获取客户的获奖证书图片列表"""
    try:
        customer = Customer.query.get_or_404(customer_id)

        images = AwardCertificateImage.query.filter_by(customer_id=customer_id).order_by(AwardCertificateImage.created_at.desc()).all()

        data = [{
            'id': img.id,
            'image_path': img.image_path,
            'description': img.description,
            'file_name': img.file_name,
            'file_size': img.get_file_size_display(),
            'created_at': img.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for img in images]

        return jsonify({
            'success': True,
            'images': data
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'获取图片失败: {str(e)}'}), 500
