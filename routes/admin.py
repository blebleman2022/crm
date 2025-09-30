from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import User, LoginLog, Lead, db
from datetime import datetime, timedelta
import re
import os
from werkzeug.utils import secure_filename
from PIL import Image

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def validate_phone(phone):
    """验证手机号格式"""
    pattern = r'^1[3-9]\d{9}$'
    return re.match(pattern, phone) is not None

def get_service_types_display(service_types_list):
    """将服务类型列表转换为显示文本"""
    if not service_types_list:
        return '未设置'

    type_map = {
        'tutoring': '课题辅导',
        'competition': '竞赛辅导',
        'upgrade_guidance': '升学陪跑'
    }

    display_names = [type_map.get(service_type, service_type) for service_type in service_types_list]
    return ', '.join(display_names)

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """管理员仪表板"""
    # 统计数据
    total_users = User.query.count()
    active_users = User.query.filter_by(status=True).count()
    inactive_users = total_users - active_users
    
    # 最近登录记录
    recent_logins = LoginLog.query.order_by(LoginLog.login_time.desc()).limit(10).all()
    
    # 角色分布
    sales_count = User.query.filter_by(role='sales', status=True).count()
    teacher_count = User.query.filter_by(role='teacher', status=True).count()
    admin_count = User.query.filter_by(role='admin', status=True).count()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         active_users=active_users,
                         inactive_users=inactive_users,
                         recent_logins=recent_logins,
                         sales_count=sales_count,
                         teacher_count=teacher_count,
                         admin_count=admin_count)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """用户账号管理"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    role_filter = request.args.get('role', '', type=str)
    group_filter = request.args.get('group', '', type=str)
    
    query = User.query
    
    # 搜索过滤
    if search:
        query = query.filter(
            (User.username.contains(search)) | 
            (User.phone.contains(search))
        )
    
    # 角色过滤
    if role_filter:
        query = query.filter_by(role=role_filter)
    
    # 组别过滤
    if group_filter:
        query = query.filter_by(group_name=group_filter)
    
    # 分页
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # 获取所有组别用于筛选
    groups = db.session.query(User.group_name).filter(User.group_name.isnot(None)).distinct().all()
    groups = [g[0] for g in groups]
    
    return render_template('admin/users.html', 
                         users=users, 
                         search=search,
                         role_filter=role_filter,
                         group_filter=group_filter,
                         groups=groups)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    """添加用户"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', '').strip()
        group_name = request.form.get('group_name', '').strip()
        
        # 验证必填字段
        if not all([username, phone, role]):
            flash('用户名、手机号和角色为必填项', 'error')
            return render_template('admin/add_user.html')
        
        # 验证手机号格式
        if not validate_phone(phone):
            flash('手机号格式不正确', 'error')
            return render_template('admin/add_user.html')
        
        # 检查手机号唯一性
        if User.query.filter_by(phone=phone).first():
            flash('该手机号已注册', 'error')
            return render_template('admin/add_user.html')
        
        # 检查管理员数量限制
        if role == 'admin':
            admin_count = User.query.filter_by(role='admin').count()
            if admin_count >= 1:
                flash('系统只允许创建一个管理员账号', 'error')
                return render_template('admin/add_user.html')
        
        # 创建用户
        try:
            user = User(
                username=username,
                phone=phone,
                role=role,
                group_name=group_name if group_name else None,
                status=True
            )
            db.session.add(user)
            db.session.commit()
            flash(f'用户 {username} 创建成功', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建用户失败: {str(e)}', 'error')
    
    return render_template('admin/add_user.html')

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """编辑用户"""
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        group_name = request.form.get('group_name', '').strip()

        if not username:
            flash('用户名为必填项', 'error')
            return render_template('admin/edit_user.html', user=user)

        try:
            user.username = username
            user.group_name = group_name if group_name else None
            user.updated_at = datetime.utcnow()

            db.session.commit()
            flash(f'用户 {username} 更新成功', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash(f'更新用户失败: {str(e)}', 'error')

    return render_template('admin/edit_user.html', user=user)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """删除用户"""
    user = User.query.get_or_404(user_id)

    # 不能删除自己
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': '不能删除自己的账号'})

    # 检查是否有关联数据
    leads_count = user.leads_as_sales.count()
    customers_count = user.customers_as_teacher.count()

    if leads_count > 0 or customers_count > 0:
        return jsonify({
            'success': False,
            'message': f'用户 {user.username} 有关联的线索或客户数据，无法删除'
        })

    try:
        username = user.username

        # 删除该用户的所有登录日志
        LoginLog.query.filter_by(user_id=user.id).delete()

        # 删除用户
        db.session.delete(user)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'用户 {username} 已删除'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@admin_bp.route('/login_logs')
@login_required
@admin_required
def login_logs():
    """登录日志查看"""
    page = request.args.get('page', 1, type=int)
    days = request.args.get('days', 7, type=int)  # 默认查看7天内的日志

    # 计算时间范围
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # 查询日志
    logs = LoginLog.query.filter(
        LoginLog.login_time >= start_date,
        LoginLog.login_time <= end_date
    ).order_by(LoginLog.login_time.desc()).paginate(
        page=page, per_page=50, error_out=False
    )

    return render_template('admin/login_logs.html', logs=logs, days=days)


# Logo管理相关配置
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = 'static/images'
LOGO_FILENAME = 'custom-logo'

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_current_logo():
    """获取当前logo文件路径"""
    for ext in ALLOWED_EXTENSIONS:
        logo_path = f"{UPLOAD_FOLDER}/{LOGO_FILENAME}.{ext}"
        if os.path.exists(logo_path):
            return f"images/{LOGO_FILENAME}.{ext}"
    return None

@admin_bp.route('/logo-management')
@login_required
@admin_required
def logo_management():
    """Logo管理页面"""
    current_logo = get_current_logo()
    return render_template('admin/logo_management.html', current_logo=current_logo)

@admin_bp.route('/upload-logo', methods=['POST'])
@login_required
@admin_required
def upload_logo():
    """上传logo"""
    if 'logo' not in request.files:
        flash('请选择要上传的文件', 'error')
        return redirect(url_for('admin.logo_management'))

    file = request.files['logo']
    if file.filename == '':
        flash('请选择要上传的文件', 'error')
        return redirect(url_for('admin.logo_management'))

    if file and allowed_file(file.filename):
        try:
            # 获取文件扩展名
            file_ext = file.filename.rsplit('.', 1)[1].lower()

            # 删除旧的logo文件
            for ext in ALLOWED_EXTENSIONS:
                old_logo_path = os.path.join(UPLOAD_FOLDER, f"{LOGO_FILENAME}.{ext}")
                if os.path.exists(old_logo_path):
                    os.remove(old_logo_path)

            # 保存新文件
            filename = f"{LOGO_FILENAME}.{file_ext}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)

            # 确保目录存在
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

            # 使用PIL调整图片尺寸为150x50
            image = Image.open(file.stream)

            # 目标尺寸
            target_width, target_height = 150, 50

            # 计算缩放比例，保持宽高比
            img_width, img_height = image.size
            scale_w = target_width / img_width
            scale_h = target_height / img_height
            scale = min(scale_w, scale_h)

            # 计算新的尺寸
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            # 调整图片尺寸
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 创建目标尺寸的画布，背景透明（PNG）或白色（其他格式）
            if file_ext.lower() == 'png':
                canvas = Image.new('RGBA', (target_width, target_height), (255, 255, 255, 0))
            else:
                canvas = Image.new('RGB', (target_width, target_height), (255, 255, 255))

            # 计算居中位置
            x = (target_width - new_width) // 2
            y = (target_height - new_height) // 2

            # 将调整后的图片粘贴到画布中心
            if image.mode == 'RGBA' or 'transparency' in image.info:
                canvas.paste(image, (x, y), image)
            else:
                canvas.paste(image, (x, y))

            image = canvas

            # 如果是PNG，保持透明度
            if file_ext.lower() == 'png':
                image.save(filepath, 'PNG', optimize=True)
            else:
                # 对于其他格式，转换为RGB
                if image.mode in ('RGBA', 'LA', 'P'):
                    image = image.convert('RGB')
                image.save(filepath, quality=95, optimize=True)

            flash('Logo上传成功！', 'success')

        except Exception as e:
            flash(f'上传失败：{str(e)}', 'error')
    else:
        flash('不支持的文件格式，请上传 PNG、JPG、JPEG 或 GIF 文件', 'error')

    return redirect(url_for('admin.logo_management'))

@admin_bp.route('/delete-logo', methods=['POST'])
@login_required
@admin_required
def delete_logo():
    """删除当前logo"""
    try:
        # 删除所有可能的logo文件
        for ext in ALLOWED_EXTENSIONS:
            logo_path = os.path.join(UPLOAD_FOLDER, f"{LOGO_FILENAME}.{ext}")
            if os.path.exists(logo_path):
                os.remove(logo_path)

        flash('Logo删除成功！', 'success')
    except Exception as e:
        flash(f'删除失败：{str(e)}', 'error')

    return redirect(url_for('admin.logo_management'))

# ==================== 线索管理 ====================

@admin_bp.route('/leads')
@login_required
@admin_required
def leads():
    """线索管理页面"""
    from sqlalchemy import func, and_

    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    stage_filter = request.args.get('stage', '', type=str)
    sales_filter = request.args.get('sales', '', type=str)

    # 时间段筛选参数
    date_type = request.args.get('date_type', '', type=str)
    start_date = request.args.get('start_date', '', type=str)
    end_date = request.args.get('end_date', '', type=str)

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

    # 时间段筛选
    if date_type and start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

            if date_type == 'first_payment':
                query = query.filter(
                    and_(
                        Lead.first_payment_at.isnot(None),
                        func.date(Lead.first_payment_at) >= start_dt,
                        func.date(Lead.first_payment_at) <= end_dt
                    )
                )
            elif date_type == 'second_payment':
                query = query.filter(
                    and_(
                        Lead.second_payment_at.isnot(None),
                        func.date(Lead.second_payment_at) >= start_dt,
                        func.date(Lead.second_payment_at) <= end_dt
                    )
                )
            elif date_type == 'full_payment':
                query = query.filter(
                    and_(
                        Lead.stage == '全款支付',
                        Lead.updated_at.isnot(None),
                        func.date(Lead.updated_at) >= start_dt,
                        func.date(Lead.updated_at) <= end_dt
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

    return render_template('admin/leads.html',
                         leads=leads,
                         search=search,
                         stage_filter=stage_filter,
                         sales_filter=sales_filter,
                         sales_users=sales_users,
                         stages=stages,
                         date_type=date_type,
                         start_date=start_date,
                         end_date=end_date)

@admin_bp.route('/leads/search')
@login_required
@admin_required
def search_leads():
    """搜索线索API"""
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({'leads': []})

    # 搜索学员姓名或家长微信名
    leads = Lead.query.filter(
        (Lead.student_name.ilike(f'%{query}%')) |
        (Lead.parent_wechat_display_name.ilike(f'%{query}%'))
    ).order_by(Lead.created_at.desc()).all()

    # 转换为JSON格式
    leads_data = []
    for lead in leads:
        leads_data.append({
            'id': lead.id,
            'student_name': lead.student_name or '未填写',
            'parent_wechat_display_name': lead.parent_wechat_display_name or '未填写',
            'parent_wechat_name': lead.parent_wechat_name or '未填写',
            'contact_info': lead.contact_info or '未填写',
            'grade': lead.grade or '未填写',
            'school': lead.school or '未填写',
            'district': lead.district or '未填写',
            'lead_source': lead.lead_source or '未填写',
            'stage': lead.stage,
            'sales_user': lead.sales_user.username if lead.sales_user else '未分配',
            'service_types': get_service_types_display(lead.get_service_types_list()),
            'created_at': lead.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_at': lead.updated_at.strftime('%Y-%m-%d %H:%M') if lead.updated_at else ''
        })

    return jsonify({'leads': leads_data})

@admin_bp.route('/leads/<int:lead_id>/edit-form')
@login_required
@admin_required
def edit_lead_form(lead_id):
    """获取编辑线索表单（AJAX）"""
    lead = Lead.query.get_or_404(lead_id)
    sales_users = User.query.filter_by(role='sales', status=True).all()

    # 返回编辑表单HTML片段
    return render_template('admin/edit_lead_form.html', lead=lead, sales_users=sales_users)

@admin_bp.route('/leads/<int:lead_id>/update', methods=['POST'])
@login_required
@admin_required
def update_lead(lead_id):
    """更新线索基本信息（AJAX）"""
    lead = Lead.query.get_or_404(lead_id)

    try:
        # 仅更新基本信息字段
        lead.parent_wechat_display_name = request.form.get('parent_wechat_display_name', '').strip()
        lead.parent_wechat_name = request.form.get('parent_wechat_name', '').strip()
        lead.student_name = request.form.get('student_name', '').strip()
        lead.contact_info = request.form.get('contact_info', '').strip()
        lead.grade = request.form.get('grade', '').strip()
        lead.school = request.form.get('school', '').strip()
        lead.district = request.form.get('district', '').strip()

        # 处理线索来源（支持自定义）
        lead_source = request.form.get('lead_source', '').strip()
        custom_source = request.form.get('custom_source', '').strip()

        if lead_source == '其他':
            if not custom_source:
                return jsonify({'success': False, 'message': '选择"其他"时必须填写自定义线索来源'})
            lead.lead_source = custom_source
        else:
            lead.lead_source = lead_source

        # 更新责任销售
        sales_user_id = request.form.get('sales_user_id')
        if sales_user_id:
            lead.sales_user_id = int(sales_user_id)

        # 更新时间戳
        lead.updated_at = datetime.now()

        db.session.commit()
        return jsonify({'success': True, 'message': '线索基本信息更新成功！'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'})

@admin_bp.route('/leads/<int:lead_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_lead(lead_id):
    """删除线索及其关联的客户数据"""
    from models import Customer, Payment, TutoringDelivery, CompetitionDelivery, CommunicationRecord

    lead = Lead.query.get_or_404(lead_id)
    lead_name = lead.student_name or "未命名"

    try:
        # 1. 查找关联的客户
        customer = Customer.query.filter_by(lead_id=lead_id).first()

        # 2. 如果存在关联客户，删除客户的交付记录和沟通记录
        if customer:
            # 删除课题辅导交付记录
            TutoringDelivery.query.filter_by(customer_id=customer.id).delete()

            # 删除竞赛辅导交付记录
            CompetitionDelivery.query.filter_by(customer_id=customer.id).delete()

            # 删除客户记录
            db.session.delete(customer)

        # 3. 删除线索的沟通记录（包括线索阶段和客户阶段的所有沟通记录）
        CommunicationRecord.query.filter_by(lead_id=lead_id).delete()

        # 4. 删除线索的付款记录
        Payment.query.filter_by(lead_id=lead_id).delete()

        # 5. 删除线索
        db.session.delete(lead)

        # 6. 提交事务
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'线索"{lead_name}"及其关联数据已成功删除'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'删除失败：{str(e)}'
        })
