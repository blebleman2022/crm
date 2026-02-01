from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from functools import wraps
from models import User, Customer, Lead, TutoringDelivery, CustomerCompetition, Payment, DeliveryDocument, db
from datetime import datetime, date
from werkzeug.utils import secure_filename
from sqlalchemy import and_, func
import os

delivery_bp = Blueprint('delivery', __name__)

def teacher_supervisor_required(f):
    """班主任权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'teacher_supervisor':
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@delivery_bp.route('/dashboard')
@login_required
@teacher_supervisor_required
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

    # 已结束赛事统计（获奖）
    competition_completed = CustomerCompetition.query.join(Customer).filter(
        Customer.teacher_user_id == current_user.id,
        ~CustomerCompetition.status.in_(['未报名', '已报名'])
    ).count()

    # 最近的交付任务
    recent_tutoring = TutoringDelivery.query.join(Customer).filter(
        Customer.teacher_user_id == current_user.id
    ).order_by(TutoringDelivery.updated_at.desc()).limit(5).all()

    # 最近的赛事进展（使用 CustomerCompetition）
    recent_competition = CustomerCompetition.query.join(Customer).filter(
        Customer.teacher_user_id == current_user.id
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
    """班主任线索管理 - 只显示首笔支付阶段的线索"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    start_date = request.args.get('start_date', '', type=str)
    end_date = request.args.get('end_date', '', type=str)

    # 如果只填了开始日期，结束日期默认为当天
    if start_date and not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

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
@teacher_supervisor_required
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
@teacher_supervisor_required
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

# 赛事管理已迁移到 customer_competitions 表，在客户管理中进行


# ==================== 老师管理功能 ====================

@delivery_bp.route('/teachers')
@login_required
@teacher_supervisor_required
def teacher_list():
    """辅导老师列表（role='teacher'）"""
    # 获取该班主任创建的所有辅导老师
    # 先查询 User 表中由当前班主任创建的 teacher 角色用户
    user_query = User.query.filter(
        User.role == 'teacher',
        User.created_by_user_id == current_user.id
    ).all()
    user_ids = [u.id for u in user_query]

    # 再查询 Teacher 表中对应的老师信息
    teachers = Teacher.query.filter(Teacher.user_id.in_(user_ids)).all() if user_ids else []

    # 统计每个老师负责的学生数
    teacher_stats = {}
    for teacher in teachers:
        student_count = Customer.query.filter_by(teacher_id=teacher.user_id).count()
        teacher_stats[teacher.user_id] = student_count

    return render_template('delivery/teacher_list.html',
                         teachers=teachers,
                         teacher_stats=teacher_stats)

@delivery_bp.route('/teachers/create', methods=['GET', 'POST'])
@login_required
@teacher_supervisor_required
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
                status=True,
                created_by_user_id=current_user.id
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
@teacher_supervisor_required
def edit_teacher(teacher_id):
    """编辑辅导老师信息"""
    # teacher_id 是 User.id
    user = User.query.get_or_404(teacher_id)

    # 验证权限：只能编辑自己创建的辅导老师，且必须是 role='teacher'
    if user.created_by_user_id != current_user.id or user.role != 'teacher':
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
@teacher_supervisor_required
def toggle_teacher_status(teacher_id):
    """启用/禁用辅导老师账号"""
    # teacher_id 是 User.id
    user = User.query.get_or_404(teacher_id)

    # 验证权限：只能操作自己创建的辅导老师，且必须是 role='teacher'
    if user.created_by_user_id != current_user.id or user.role != 'teacher':
        return jsonify({'success': False, 'message': '您无权操作此老师账号'}), 403

    try:
        user.status = not user.status
        user.updated_at = datetime.utcnow()
        db.session.commit()

        status_text = '启用' if user.status else '禁用'
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

    # 验证权限 - 只能查看自己负责的客户
    if customer.teacher_user_id != current_user.id:
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
    if customer.teacher_user_id != current_user.id:
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
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()

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
    if customer.teacher_user_id != current_user.id:
        return jsonify({'success': False, 'message': '您无权删除此文档'}), 403
    if doc.uploaded_by_type != 'teacher_supervisor' or doc.uploaded_by_id != current_user.id:
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

    # 验证权限 - 只能下载自己负责的客户的文档
    customer = Customer.query.get_or_404(doc.customer_id)
    if customer.teacher_user_id != current_user.id:
        flash('您无权下载此文档', 'error')
        return redirect(url_for('delivery.dashboard'))

    # 检查文件是否存在
    if not os.path.exists(doc.file_path):
        flash('文件不存在', 'error')
        return redirect(url_for('customers.detail', customer_id=doc.customer_id))

    return send_file(doc.file_path, as_attachment=True, download_name=doc.file_name)
