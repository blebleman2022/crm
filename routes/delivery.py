from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import User, Customer, Lead, TutoringDelivery, CompetitionDelivery, Payment, db
from datetime import datetime, date
from sqlalchemy import and_, func

delivery_bp = Blueprint('delivery', __name__)

def teacher_required(f):
    """班主任权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_teacher():
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@delivery_bp.route('/dashboard')
@login_required
@teacher_required
def dashboard():
    """交付管理仪表板"""
    # 我负责的客户统计
    my_customers = Customer.query.filter_by(teacher_user_id=current_user.id).count()
    
    # 课题辅导统计 - 基于实际服务类型
    tutoring_total = Customer.query.join(Customer.lead).filter(
        Customer.teacher_user_id == current_user.id,
        Lead.service_types.contains('tutoring')
    ).count()

    tutoring_completed = TutoringDelivery.query.join(Customer).join(Customer.lead).filter(
        Customer.teacher_user_id == current_user.id,
        Lead.service_types.contains('tutoring'),
        TutoringDelivery.thesis_status == '已完成'
    ).count()

    # 竞赛辅导统计 - 基于实际服务类型
    competition_total = Customer.query.join(Customer.lead).filter(
        Customer.teacher_user_id == current_user.id,
        Lead.service_types.contains('competition')
    ).count()

    competition_completed = CompetitionDelivery.query.join(Customer).join(Customer.lead).filter(
        Customer.teacher_user_id == current_user.id,
        Lead.service_types.contains('competition'),
        CompetitionDelivery.delivery_status == '服务完结'
    ).count()
    
    # 最近的交付任务
    recent_tutoring = TutoringDelivery.query.join(Customer).filter(
        Customer.teacher_user_id == current_user.id
    ).order_by(TutoringDelivery.updated_at.desc()).limit(5).all()
    
    recent_competition = CompetitionDelivery.query.join(Customer).filter(
        Customer.teacher_user_id == current_user.id
    ).order_by(CompetitionDelivery.updated_at.desc()).limit(5).all()
    
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
@teacher_required
def leads_list():
    """班主任线索管理 - 只显示首笔支付阶段的线索"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    start_date = request.args.get('start_date', '', type=str)
    end_date = request.args.get('end_date', '', type=str)

    # 基础查询：只显示首笔支付阶段的线索
    query = Lead.query.filter(Lead.stage == '首笔支付')

    # 搜索过滤（学员姓名或家长微信名）
    if search:
        query = query.filter(
            db.or_(
                Lead.student_name.contains(search),
                Lead.parent_wechat_display_name.contains(search)
            )
        )

    # 首笔支付时间筛选
    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

            # 查询首笔支付时间在指定范围内的线索
            # 首笔支付时间 = 第一笔付款的 payment_date
            lead_ids_in_range = db.session.query(Payment.lead_id).filter(
                and_(
                    func.date(Payment.payment_date) >= start_dt,
                    func.date(Payment.payment_date) <= end_dt
                )
            ).group_by(Payment.lead_id).having(
                func.min(Payment.payment_date) >= start_dt
            ).all()

            lead_ids = [lid[0] for lid in lead_ids_in_range]
            if lead_ids:
                query = query.filter(Lead.id.in_(lead_ids))
            else:
                # 如果没有符合条件的线索，返回空结果
                query = query.filter(Lead.id == -1)
        except ValueError:
            pass

    # 分页 - 按更新时间倒序
    leads = query.order_by(Lead.updated_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

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

    return render_template('delivery/leads_list.html',
                         leads=leads,
                         search=search,
                         start_date=start_date,
                         end_date=end_date,
                         sales_users=sales_users,
                         first_payment_dates=first_payment_dates)

@delivery_bp.route('/tutoring')
@login_required
@teacher_required
def tutoring_list():
    """课题辅导交付列表"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    status_filter = request.args.get('status', '', type=str)
    
    query = TutoringDelivery.query.join(Customer).join(Customer.lead).filter(
        Customer.teacher_user_id == current_user.id
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
@teacher_required
def edit_tutoring(delivery_id):
    """编辑课题辅导交付"""
    delivery = TutoringDelivery.query.get_or_404(delivery_id)
    
    # 检查权限
    if delivery.customer.teacher_user_id != current_user.id:
        flash('您没有权限编辑此交付记录', 'error')
        return redirect(url_for('delivery.tutoring_list'))
    
    if request.method == 'POST':
        completed_sessions = request.form.get('completed_sessions', 0, type=int)
        thesis_status = request.form.get('thesis_status', '').strip()
        last_class_date = request.form.get('last_class_date', '').strip()
        next_class_date = request.form.get('next_class_date', '').strip()
        delivery_notes = request.form.get('delivery_notes', '').strip()
        
        # 验证课时数
        if completed_sessions < 0 or completed_sessions > 6:
            flash('已上课时数必须在0-6之间', 'error')
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
            delivery.remaining_sessions = 6 - completed_sessions
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

@delivery_bp.route('/competition')
@login_required
@teacher_required
def competition_list():
    """竞赛奖项交付列表"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    status_filter = request.args.get('status', '', type=str)
    
    query = CompetitionDelivery.query.join(Customer).join(Customer.lead).filter(
        Customer.teacher_user_id == current_user.id
    )
    
    # 搜索过滤
    if search:
        from models import Lead
        query = query.filter(Lead.student_name.contains(search))
    
    # 状态过滤
    if status_filter:
        query = query.filter(CompetitionDelivery.delivery_status == status_filter)
    
    # 分页
    deliveries = query.order_by(CompetitionDelivery.updated_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('delivery/competition_list.html', 
                         deliveries=deliveries, 
                         search=search,
                         status_filter=status_filter)

@delivery_bp.route('/competition/<int:delivery_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_competition(delivery_id):
    """编辑竞赛奖项交付"""
    delivery = CompetitionDelivery.query.get_or_404(delivery_id)
    
    # 检查权限
    if delivery.customer.teacher_user_id != current_user.id:
        flash('您没有权限编辑此交付记录', 'error')
        return redirect(url_for('delivery.competition_list'))
    
    if request.method == 'POST':
        competition_name = request.form.get('competition_name', '').strip()
        delivery_status = request.form.get('delivery_status', '').strip()
        registration_date = request.form.get('registration_date', '').strip()
        competition_date = request.form.get('competition_date', '').strip()
        award_result = request.form.get('award_result', '').strip()
        delivery_notes = request.form.get('delivery_notes', '').strip()
        
        try:
            # 转换日期
            reg_date = None
            comp_date = None
            if registration_date:
                reg_date = datetime.strptime(registration_date, '%Y-%m-%d').date()
            if competition_date:
                comp_date = datetime.strptime(competition_date, '%Y-%m-%d').date()
            
            # 更新交付信息
            delivery.competition_name = competition_name
            delivery.delivery_status = delivery_status
            delivery.registration_date = reg_date
            delivery.competition_date = comp_date
            delivery.award_result = award_result
            delivery.delivery_notes = delivery_notes
            delivery.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash(f'竞赛奖项交付记录更新成功', 'success')
            return redirect(url_for('delivery.competition_list'))
        except ValueError:
            flash('日期格式不正确', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败: {str(e)}', 'error')
    
    return render_template('delivery/edit_competition.html', delivery=delivery)
