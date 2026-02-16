from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import User, LoginLog, Lead, Customer, SystemConfig, db
from datetime import datetime, timedelta
import re
import os
from werkzeug.utils import secure_filename
# from PIL import Image  # 暂时注释，避免依赖问题

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

def normalize_supervisor_scope(value):
    """标准化班主任服务范围"""
    value = (value or '').strip().lower()
    if value in User.ALLOWED_TEACHER_SCOPES:
        return value
    return User.TEACHER_SCOPE_ALL


def normalize_supervisor_level(value):
    """标准化班主任层级"""
    value = (value or '').strip().lower()
    if value in User.ALLOWED_TEACHER_LEVELS:
        return value
    return User.TEACHER_LEVEL_REGULAR


def get_teacher_profile_type(user):
    """获取班主任配置类型（public_manager/public_regular/private）"""
    if not user or user.role != 'teacher_supervisor':
        return ''
    if user.get_supervisor_scope() == User.TEACHER_SCOPE_PRIVATE_ONLY:
        return 'private'
    if user.get_supervisor_level() == User.TEACHER_LEVEL_MANAGER:
        return 'public_manager'
    return 'public_regular'


def public_teacher_supervisor_filter():
    """公域班主任过滤条件"""
    return db.or_(
        User.supervisor_scope.is_(None),
        User.supervisor_scope == '',
        User.supervisor_scope.in_([User.TEACHER_SCOPE_ALL, User.TEACHER_SCOPE_PUBLIC_ONLY])
    )


def get_public_teacher_managers(exclude_user_id=None):
    """获取可用的公域班主任主管列表"""
    query = User.query.filter(
        User.role == 'teacher_supervisor',
        User.status == True,
        public_teacher_supervisor_filter(),
        User.supervisor_level == User.TEACHER_LEVEL_MANAGER
    )
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)
    return query.order_by(User.username.asc()).all()


def get_assignable_public_regular_teachers(exclude_user_id=None):
    """获取可归属到主管名下的普通班主任列表"""
    query = User.query.filter(
        User.role == 'teacher_supervisor',
        User.status == True,
        public_teacher_supervisor_filter(),
        db.or_(
            User.supervisor_level.is_(None),
            User.supervisor_level == '',
            User.supervisor_level != User.TEACHER_LEVEL_MANAGER
        )
    )
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)
    return query.order_by(User.username.asc()).all()


def is_config_enabled(value):
    """将系统配置值转换为布尔开关"""
    return str(value or '').strip().lower() in {'1', 'true', 'on', 'yes', 'enabled'}

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

    # 今日登录统计
    from datetime import date
    today = date.today()
    today_logins = LoginLog.query.filter(
        db.func.date(LoginLog.login_time) == today
    ).count()

    # 角色分布（salesperson已合并到sales_manager）
    sales_manager_count = User.query.filter(User.role.in_(['sales_manager', 'salesperson']), User.status == True).count()
    teacher_count = User.query.filter_by(role='teacher', status=True).count()
    admin_count = User.query.filter_by(role='admin', status=True).count()

    # 线索和客户统计
    total_leads = Lead.query.count()
    total_customers = Customer.query.count()

    # 维护模式状态
    maintenance_config = SystemConfig.query.filter_by(config_key='maintenance_mode').first()
    maintenance_mode_enabled = is_config_enabled(maintenance_config.config_value if maintenance_config else None)

    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         active_users=active_users,
                         inactive_users=inactive_users,
                         recent_logins=recent_logins,
                         today_logins=today_logins,
                         sales_manager_count=sales_manager_count,
                         teacher_count=teacher_count,
                         admin_count=admin_count,
                         total_leads=total_leads,
                         total_customers=total_customers,
                         maintenance_mode_enabled=maintenance_mode_enabled)


@admin_bp.route('/maintenance/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_maintenance_mode():
    """切换全站维护模式"""
    desired_mode = (request.form.get('maintenance_mode') or '').strip().lower()

    try:
        config = SystemConfig.query.filter_by(config_key='maintenance_mode').first()
        current_enabled = is_config_enabled(config.config_value if config else None)

        if desired_mode in {'on', '1', 'true'}:
            target_enabled = True
        elif desired_mode in {'off', '0', 'false'}:
            target_enabled = False
        else:
            target_enabled = not current_enabled

        if config is None:
            config = SystemConfig(
                config_key='maintenance_mode',
                description='全站维护模式开关（on/off）'
            )
            db.session.add(config)

        config.config_value = 'on' if target_enabled else 'off'
        config.updated_by = current_user.id
        config.updated_at = datetime.utcnow()
        db.session.commit()

        if target_enabled:
            flash('系统已进入维护状态，除管理员入口外其余页面将显示维护提示', 'success')
        else:
            flash('系统已退出维护状态，访问已恢复', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'维护状态更新失败: {str(e)}', 'error')

    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """用户账号管理"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    role_filter = request.args.get('role', '', type=str)
    group_filter = request.args.get('group', '', type=str)

    visible_role_filters = {'admin', 'sales_manager', 'teacher_supervisor'}
    if role_filter not in visible_role_filters:
        role_filter = ''

    # 用户管理页不展示老师账号；老师信息统一在“老师管理”页维护
    query = User.query.filter(User.role != 'teacher')
    
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
    groups = db.session.query(User.group_name).filter(
        User.group_name.isnot(None),
        User.role != 'teacher'
    ).distinct().all()
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
    def render_add_user_page():
        return render_template(
            'admin/add_user.html',
            public_manager_options=get_public_teacher_managers()
        )

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', '').strip()
        group_name = request.form.get('group_name', '').strip()
        is_private_owner = request.form.get('is_private_owner') == 'on'
        supervisor_scope = normalize_supervisor_scope(request.form.get('supervisor_scope'))
        supervisor_level = normalize_supervisor_level(request.form.get('supervisor_level'))
        teacher_profile_type = (request.form.get('teacher_profile_type') or '').strip().lower()
        supervisor_user_id = request.form.get('supervisor_user_id', type=int)
        
        # 验证必填字段
        if not all([username, phone, role]):
            flash('用户名、手机号和角色为必填项', 'error')
            return render_add_user_page()

        allowed_roles = {'admin', 'sales_manager', 'teacher_supervisor'}
        if role == 'teacher':
            flash('老师账号请由管理员在“老师管理-添加老师”中创建', 'error')
            return render_add_user_page()
        if role not in allowed_roles:
            flash('用户角色无效，请重新选择', 'error')
            return render_add_user_page()
        
        # 验证手机号格式
        if not validate_phone(phone):
            flash('手机号格式不正确', 'error')
            return render_add_user_page()
        
        # 检查手机号唯一性
        if User.query.filter_by(phone=phone).first():
            flash('该手机号已注册', 'error')
            return render_add_user_page()
        
        # 检查管理员数量限制
        if role == 'admin':
            admin_count = User.query.filter_by(role='admin').count()
            if admin_count >= 1:
                flash('系统只允许创建一个管理员账号', 'error')
                return render_add_user_page()

        # 私域负责人仅支持销售管理角色
        if role != 'sales_manager':
            is_private_owner = False

        # 班主任类型配置（公域主管/公域普通/私域）
        if role == 'teacher_supervisor':
            if teacher_profile_type not in {'public_manager', 'public_regular', 'private'}:
                flash('请选择班主任类型', 'error')
                return render_add_user_page()

            if teacher_profile_type == 'private':
                supervisor_scope = User.TEACHER_SCOPE_PRIVATE_ONLY
                supervisor_level = User.TEACHER_LEVEL_REGULAR
                supervisor_user_id = None
            elif teacher_profile_type == 'public_manager':
                supervisor_scope = User.TEACHER_SCOPE_PUBLIC_ONLY
                supervisor_level = User.TEACHER_LEVEL_MANAGER
                supervisor_user_id = None
            else:
                supervisor_scope = User.TEACHER_SCOPE_PUBLIC_ONLY
                supervisor_level = User.TEACHER_LEVEL_REGULAR
                if not supervisor_user_id:
                    flash('公域普通班主任必须选择班主任主管', 'error')
                    return render_add_user_page()
                supervisor = User.query.filter(
                    User.id == supervisor_user_id,
                    User.role == 'teacher_supervisor',
                    User.status == True,
                    public_teacher_supervisor_filter(),
                    User.supervisor_level == User.TEACHER_LEVEL_MANAGER
                ).first()
                if not supervisor:
                    flash('选择的班主任主管无效', 'error')
                    return render_add_user_page()
        else:
            supervisor_scope = User.TEACHER_SCOPE_ALL
            supervisor_level = User.TEACHER_LEVEL_REGULAR
            supervisor_user_id = None
        
        # 创建用户
        try:
            user = User(
                username=username,
                phone=phone,
                role=role,
                group_name=group_name if group_name else None,
                status=True,
                is_private_owner=is_private_owner,
                supervisor_scope=supervisor_scope,
                supervisor_level=supervisor_level,
                supervisor_user_id=supervisor_user_id
            )
            db.session.add(user)
            db.session.commit()
            flash(f'用户 {username} 创建成功', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建用户失败: {str(e)}', 'error')
    
    return render_add_user_page()

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """编辑用户"""
    user = User.query.get_or_404(user_id)

    def render_edit_user_page():
        with db.session.no_autoflush:
            teacher_profile_type = get_teacher_profile_type(user)
            public_manager_options = get_public_teacher_managers(exclude_user_id=user.id)
            assignable_public_regular_teachers = get_assignable_public_regular_teachers(exclude_user_id=user.id)
            managed_teacher_ids = set()
            if user.role == 'teacher_supervisor' and user.get_supervisor_level() == User.TEACHER_LEVEL_MANAGER:
                managed_teacher_ids = {
                    row.id for row in User.query.filter(
                        User.role == 'teacher_supervisor',
                        User.supervisor_user_id == user.id
                    ).with_entities(User.id).all()
                }

        return render_template(
            'admin/edit_user.html',
            user=user,
            teacher_profile_type=teacher_profile_type,
            public_manager_options=public_manager_options,
            assignable_public_regular_teachers=assignable_public_regular_teachers,
            managed_teacher_ids=managed_teacher_ids
        )

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        phone = request.form.get('phone', '').strip()
        phone_confirm = request.form.get('phone_confirm', '').strip()
        group_name = request.form.get('group_name', '').strip()
        teacher_profile_type = (request.form.get('teacher_profile_type') or '').strip().lower()
        requested_supervisor_user_id = request.form.get('supervisor_user_id', type=int)
        managed_teacher_ids_raw = request.form.getlist('managed_teacher_ids')

        if not username:
            flash('用户名为必填项', 'error')
            return render_edit_user_page()
        if not phone:
            flash('手机号为必填项', 'error')
            return render_edit_user_page()
        if not validate_phone(phone):
            flash('手机号格式不正确', 'error')
            return render_edit_user_page()

        # 修改手机号时需要二次确认，并校验唯一性
        if phone != user.phone:
            if not phone_confirm:
                flash('修改手机号时请再次输入确认手机号', 'error')
                return render_edit_user_page()
            if phone != phone_confirm:
                flash('两次输入的手机号不一致', 'error')
                return render_edit_user_page()

            existing_user = User.query.filter(
                User.phone == phone,
                User.id != user.id
            ).first()
            if existing_user:
                flash('该手机号已被其他账号使用', 'error')
                return render_edit_user_page()

        try:
            user.username = username
            user.phone = phone
            user.group_name = group_name if group_name else None

            if user.role == 'teacher_supervisor':
                if teacher_profile_type not in {'public_manager', 'public_regular', 'private'}:
                    flash('请选择班主任类型', 'error')
                    return render_edit_user_page()

                if teacher_profile_type == 'private':
                    user.supervisor_scope = User.TEACHER_SCOPE_PRIVATE_ONLY
                    user.supervisor_level = User.TEACHER_LEVEL_REGULAR
                    user.supervisor_user_id = None
                elif teacher_profile_type == 'public_manager':
                    user.supervisor_scope = User.TEACHER_SCOPE_PUBLIC_ONLY
                    user.supervisor_level = User.TEACHER_LEVEL_MANAGER
                    user.supervisor_user_id = None
                else:
                    user.supervisor_scope = User.TEACHER_SCOPE_PUBLIC_ONLY
                    user.supervisor_level = User.TEACHER_LEVEL_REGULAR
                    available_managers = get_public_teacher_managers(exclude_user_id=user.id)
                    if not requested_supervisor_user_id:
                        if available_managers:
                            flash('公域普通班主任必须选择班主任主管', 'error')
                            return render_edit_user_page()
                        user.supervisor_user_id = None
                    else:
                        if requested_supervisor_user_id == user.id:
                            flash('班主任不能归属自己', 'error')
                            return render_edit_user_page()
                        supervisor = User.query.filter(
                            User.id == requested_supervisor_user_id,
                            User.role == 'teacher_supervisor',
                            User.status == True,
                            public_teacher_supervisor_filter(),
                            User.supervisor_level == User.TEACHER_LEVEL_MANAGER
                        ).first()
                        if not supervisor:
                            flash('选择的班主任主管无效', 'error')
                            return render_edit_user_page()
                        user.supervisor_user_id = requested_supervisor_user_id
            else:
                user.supervisor_scope = User.TEACHER_SCOPE_ALL
                user.supervisor_level = User.TEACHER_LEVEL_REGULAR
                user.supervisor_user_id = None

            # 主管编辑页维护旗下普通班主任归属关系
            if user.role == 'teacher_supervisor' and user.get_supervisor_level() == User.TEACHER_LEVEL_MANAGER:
                normalized_ids = set()
                for value in managed_teacher_ids_raw:
                    try:
                        normalized_ids.add(int(value))
                    except (TypeError, ValueError):
                        continue

                assignable_teachers = get_assignable_public_regular_teachers(exclude_user_id=user.id)
                assignable_ids = {teacher.id for teacher in assignable_teachers}
                if not normalized_ids.issubset(assignable_ids):
                    flash('所选普通班主任中包含无效账号，请刷新页面后重试', 'error')
                    return render_edit_user_page()

                # 取消此前归属但未被选中的普通班主任
                if normalized_ids:
                    User.query.filter(
                        User.role == 'teacher_supervisor',
                        User.supervisor_user_id == user.id,
                        ~User.id.in_(list(normalized_ids))
                    ).update({User.supervisor_user_id: None}, synchronize_session=False)
                else:
                    User.query.filter(
                        User.role == 'teacher_supervisor',
                        User.supervisor_user_id == user.id
                    ).update({User.supervisor_user_id: None}, synchronize_session=False)

                # 设置当前选中普通班主任归属
                if normalized_ids:
                    User.query.filter(
                        User.id.in_(list(normalized_ids))
                    ).update(
                        {
                            User.supervisor_user_id: user.id,
                            User.supervisor_scope: User.TEACHER_SCOPE_PUBLIC_ONLY,
                            User.supervisor_level: User.TEACHER_LEVEL_REGULAR
                        },
                        synchronize_session=False
                    )
            else:
                # 非主管时，清空其下属归属关系
                User.query.filter(
                    User.role == 'teacher_supervisor',
                    User.supervisor_user_id == user.id
                ).update({User.supervisor_user_id: None}, synchronize_session=False)

            user.updated_at = datetime.utcnow()

            db.session.commit()
            flash(f'用户 {username} 更新成功', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash(f'更新用户失败: {str(e)}', 'error')

    return render_edit_user_page()

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
    customers_count = user.customers_as_teacher_user.count()

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

            # 简化版：直接保存文件（暂时不进行图片处理）
            file.save(filepath)

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

    # 如果只填了开始日期，结束日期默认为当天
    if date_type and start_date and not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

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
    if date_type and start_date:
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
    sales_users = User.query.filter(User.role.in_(['sales_manager', 'salesperson']), User.status == True).all()

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
    from models import Payment

    lead = Lead.query.get_or_404(lead_id)
    customer = Customer.query.filter_by(lead_id=lead.id).first()
    current_supervisor_user_id = lead.supervisor_user_id
    if not current_supervisor_user_id and customer:
        current_supervisor_user_id = customer.supervisor_user_id
    can_assign_teacher = lead.stage in ['首笔支付', '次笔支付', '全款支付']
    lead_scope = (lead.customer_scope or Lead.SCOPE_PUBLIC).strip().lower()
    if lead_scope != Lead.SCOPE_PRIVATE:
        lead_scope = Lead.SCOPE_PUBLIC

    # 列出所有销售与销售管理角色
    sales_users = User.query.filter(
        User.role.in_(['sales_manager', 'salesperson']),
        User.status == True
    ).order_by(User.role.desc(), User.username.asc()).all()

    # 可分配班主任（按线索归属域过滤班主任服务范围）
    teacher_users_query = User.query.filter(
        User.role == 'teacher_supervisor',
        User.status == True
    )
    if lead_scope == Lead.SCOPE_PUBLIC:
        teacher_users_query = teacher_users_query.filter(db.or_(
            User.supervisor_scope != User.TEACHER_SCOPE_PRIVATE_ONLY,
            User.supervisor_scope.is_(None),
            User.supervisor_scope == ''
        ))
    elif lead_scope == Lead.SCOPE_PRIVATE:
        # 私域线索可分配给：仅私域班主任 或 公私域都可分配的班主任
        # 即排除那些只能服务公域的班主任（但当前设计中不存在这样的scope）
        # 所以这里实际上是允许所有班主任
        pass
    teacher_users = teacher_users_query.order_by(User.username.asc()).all()

    # 若当前已分配班主任不在筛选结果中，追加以保证可见
    if current_supervisor_user_id and not any(t.id == current_supervisor_user_id for t in teacher_users):
        current_teacher = User.query.filter(
            User.id == current_supervisor_user_id,
            User.role == 'teacher_supervisor'
        ).first()
        if current_teacher:
            teacher_users.append(current_teacher)

    # 获取付款记录
    payments = Payment.query.filter_by(lead_id=lead.id).order_by(Payment.payment_date.desc()).all()

    # 返回编辑表单HTML片段
    return render_template(
        'admin/edit_lead_form.html',
        lead=lead,
        sales_users=sales_users,
        payments=payments,
        teacher_users=teacher_users,
        current_supervisor_user_id=current_supervisor_user_id,
        can_assign_teacher=can_assign_teacher,
        customer_exists=bool(customer),
        lead_scope=lead_scope
    )

@admin_bp.route('/leads/<int:lead_id>/update', methods=['POST'])
@login_required
@admin_required
def update_lead(lead_id):
    """更新线索信息（AJAX）"""
    from decimal import Decimal

    lead = Lead.query.get_or_404(lead_id)

    try:
        # 更新基本信息字段
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

        # 更新服务内容
        service_types = request.form.getlist('service_types')
        if service_types:
            lead.service_types = ','.join(service_types)
        else:
            lead.service_types = None
        tutoring_topic_type = request.form.get('tutoring_topic_type', '').strip()

        # 更新竞赛奖项等级和申报数量
        competition_award_level = request.form.get('competition_award_level', '').strip()
        competition_count = request.form.get('competition_count', '').strip()

        if 'competition' in service_types:
            if not competition_award_level:
                return jsonify({'success': False, 'message': '选择了竞赛辅导服务，必须设置目标奖项等级'})
            if not competition_count or int(competition_count) < 1:
                return jsonify({'success': False, 'message': '选择了竞赛辅导服务，必须填写申报赛事数量'})

        if 'tutoring' in service_types:
            if tutoring_topic_type not in Lead.ALLOWED_TUTORING_TOPIC_TYPES:
                return jsonify({'success': False, 'message': '选择了课题辅导服务，必须选择课题类型（储备课题或定制课题）'})
        else:
            tutoring_topic_type = ''

        lead.competition_award_level = competition_award_level if competition_award_level else None
        lead.competition_count = int(competition_count) if competition_count else None
        lead.tutoring_topic_type = tutoring_topic_type if 'tutoring' in service_types else None

        # 更新额外要求
        lead.additional_requirements = request.form.get('additional_requirements', '').strip()

        # 更新合同金额
        contract_amount = request.form.get('contract_amount', '').strip()
        if contract_amount:
            try:
                lead.contract_amount = Decimal(contract_amount)
            except:
                return jsonify({'success': False, 'message': '合同金额格式不正确'})

        # 更新班主任（首笔支付后可选择；写入线索表，客户已存在时同步）
        customer = Customer.query.filter_by(lead_id=lead.id).first()
        supervisor_user_id_raw = request.form.get('supervisor_user_id')
        can_assign_teacher = lead.stage in ['首笔支付', '次笔支付', '全款支付']
        supervisor_user_id = supervisor_user_id_raw.strip() if supervisor_user_id_raw is not None else None
        if supervisor_user_id:
            if not can_assign_teacher:
                return jsonify({'success': False, 'message': '线索未到首笔支付阶段，暂不能分配班主任'})
            try:
                supervisor_user_id_int = int(supervisor_user_id)
            except ValueError:
                return jsonify({'success': False, 'message': '班主任参数格式不正确'})

            teacher = User.query.filter(
                User.id == supervisor_user_id_int,
                User.role == 'teacher_supervisor',
                User.status == True
            ).first()
            if not teacher:
                return jsonify({'success': False, 'message': '选择的班主任无效'})

            lead_scope = (lead.customer_scope or Lead.SCOPE_PUBLIC).strip().lower()
            if lead_scope != Lead.SCOPE_PRIVATE:
                lead_scope = Lead.SCOPE_PUBLIC
            if not teacher.can_serve_customer_scope(lead_scope):
                return jsonify({'success': False, 'message': '该班主任仅可分配私域客户，当前客户为公域客户'})

            lead.supervisor_user_id = supervisor_user_id_int
            if customer:
                customer.supervisor_user_id = supervisor_user_id_int
        elif supervisor_user_id is not None:
            lead.supervisor_user_id = None
            if customer:
                customer.supervisor_user_id = None

        # 更新时间戳
        lead.updated_at = datetime.now()

        db.session.commit()
        return jsonify({'success': True, 'message': '线索信息更新成功！'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'})

@admin_bp.route('/leads/<int:lead_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_lead(lead_id):
    """删除线索及其关联的客户数据

    注意：由于已配置级联删除（cascade='all, delete-orphan'），
    删除 Lead 时会自动删除关联的 Customer、Payment、CommunicationRecord，
    以及 Customer 关联的 TutoringDelivery 和 CompetitionDelivery。
    """
    lead = Lead.query.get_or_404(lead_id)
    lead_name = lead.student_name or "未命名"

    try:
        # 直接删除线索，级联删除会自动处理所有关联数据
        db.session.delete(lead)
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

