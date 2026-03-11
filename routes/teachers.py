from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from models import User, Customer, Lead, Teacher, TeacherImage, TopicTask, LoginLog, db
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import os
from werkzeug.utils import secure_filename

teachers_bp = Blueprint('teachers', __name__)
EXTERNAL_EDIT_TOKEN_SALT = 'teacher-external-edit'
EXTERNAL_EDIT_LINK_SECONDS = 30 * 60


def build_education_summary(form):
    """从学历三行输入构建最高学历和学历说明文本。"""
    degree_rows = [
        ('博士', 'phd'),
        ('硕士', 'master'),
        ('本科', 'bachelor'),
    ]

    highest_degree = ''
    lines = []

    for degree_label, degree_key in degree_rows:
        removed = (form.get(f'education_{degree_key}_removed', '0') == '1')
        school = form.get(f'education_{degree_key}_school', '').strip()
        major = form.get(f'education_{degree_key}_major', '').strip()

        if removed or (not school and not major):
            continue

        if not highest_degree:
            highest_degree = degree_label

        school_text = school if school else '-'
        major_text = major if major else '-'
        lines.append(f'{degree_label}：{school_text} / {major_text}')

    return highest_degree, '\n'.join(lines)


def education_form_has_updates(form):
    """判断学历三行输入是否有显式修改，用于兼容历史自由文本数据。"""
    for degree_key in ('phd', 'master', 'bachelor'):
        if form.get(f'education_{degree_key}_removed', '0') == '1':
            return True
        if form.get(f'education_{degree_key}_school', '').strip():
            return True
        if form.get(f'education_{degree_key}_major', '').strip():
            return True
    return False


def parse_education_summary(teacher):
    """将已保存的学历说明解析为三行输入的初始值。"""
    initial = {
        'phd': {'school': '', 'major': ''},
        'master': {'school': '', 'major': ''},
        'bachelor': {'school': '', 'major': ''},
    }
    label_to_key = {
        '博士': 'phd',
        '硕士': 'master',
        '本科': 'bachelor',
    }

    description = (teacher.degree_description or '').strip()
    if not description:
        return initial

    parsed_any = False
    for raw_line in description.splitlines():
        line = (raw_line or '').strip()
        if not line:
            continue

        for label, key in label_to_key.items():
            prefix = f'{label}：'
            if not line.startswith(prefix):
                continue

            tail = line[len(prefix):].strip()
            if ' / ' in tail:
                school, major = tail.split(' / ', 1)
            elif '/' in tail:
                school, major = tail.split('/', 1)
            else:
                school, major = tail, ''

            school = school.strip()
            major = major.strip()
            initial[key]['school'] = '' if school == '-' else school
            initial[key]['major'] = '' if major == '-' else major
            parsed_any = True
            break

    # 兼容旧数据：若是历史自由文本，放入最高学历对应行，避免编辑后丢失。
    if not parsed_any:
        fallback_key = label_to_key.get((teacher.highest_degree or '').strip())
        if not fallback_key:
            fallback_key = 'bachelor'
        initial[fallback_key]['major'] = description

    return initial


def _external_edit_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])


def generate_external_edit_token(teacher_id):
    serializer = _external_edit_serializer()
    return serializer.dumps({'teacher_id': int(teacher_id)}, salt=EXTERNAL_EDIT_TOKEN_SALT)


def load_teacher_from_external_token(token):
    serializer = _external_edit_serializer()
    payload = serializer.loads(
        token,
        salt=EXTERNAL_EDIT_TOKEN_SALT,
        max_age=EXTERNAL_EDIT_LINK_SECONDS
    )
    teacher_id = int(payload.get('teacher_id', 0))
    if not teacher_id:
        raise BadSignature('missing teacher_id')

    user = User.query.get_or_404(teacher_id)
    if user.role != 'teacher':
        raise BadSignature('invalid role')
    teacher = Teacher.query.filter_by(user_id=teacher_id).first()
    if not teacher:
        raise BadSignature('teacher profile not found')

    return user, teacher

def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('您没有权限访问此页面，仅管理员可访问', 'error')
            return redirect(url_for('leads.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def teacher_supervisor_required(f):
    """班主任角色权限装饰器（只有teacher_supervisor角色的用户可以访问）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'teacher_supervisor':
            flash('您没有权限访问此页面，仅班主任可访问', 'error')
            return redirect(url_for('leads.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def teacher_supervisor_or_admin_required(f):
    """班主任或管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('请先登录', 'error')
            return redirect(url_for('auth.login'))
        if current_user.role not in {'teacher_supervisor', 'admin'}:
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('leads.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def sales_manager_required(f):
    """销售管理角色权限装饰器（只有sales_manager角色的用户可以访问）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'sales_manager':
            flash('您没有权限访问此页面，仅销售管理可访问', 'error')
            return redirect(url_for('leads.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def get_visible_teacher_supervisor_ids():
    """当前班主任可见的数据归属班主任ID集合（主管=自己+旗下普通班主任）"""
    if current_user.role != 'teacher_supervisor':
        return []

    cached_ids = getattr(current_user, '_visible_teacher_supervisor_ids_cache', None)
    if cached_ids is not None:
        return cached_ids

    visible_ids = current_user.get_visible_teacher_supervisor_ids()
    if current_user.id not in visible_ids:
        visible_ids.append(current_user.id)

    current_user._visible_teacher_supervisor_ids_cache = visible_ids
    return visible_ids

@teachers_bp.route('/list')
@login_required
@teacher_supervisor_or_admin_required
def list_teachers():
    """辅导老师列表页（role='teacher'）"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    status_filter = request.args.get('status', '', type=str)
    is_admin_view = current_user.is_admin()

    # 老师创建人信息已移除，班主任和管理员均可查看全部老师
    teacher_query = Teacher.query.join(User, Teacher.user_id == User.id).filter(User.role == 'teacher')

    # 搜索过滤
    if search:
        teacher_query = teacher_query.filter(
            (User.username.contains(search)) |
            (Teacher.current_institution.contains(search)) |
            (Teacher.major_direction.contains(search))
        )

    # 状态筛选：停用老师仅管理员可见
    if is_admin_view:
        if status_filter == 'active':
            teacher_query = teacher_query.filter(User.status == True)
        elif status_filter == 'inactive':
            teacher_query = teacher_query.filter(User.status == False)
    else:
        teacher_query = teacher_query.filter(User.status == True)
        status_filter = 'active'

    # 按创建时间倒序排列
    teacher_query = teacher_query.order_by(User.created_at.desc())

    # 分页
    per_page = 20
    pagination = teacher_query.paginate(page=page, per_page=per_page, error_out=False)
    teachers = pagination.items

    # 统计每个老师负责的客户数量
    teacher_customer_counts = {}
    for teacher in teachers:
        count = Customer.query.filter(Customer.tutor_user_id == teacher.user_id).count()
        teacher_customer_counts[teacher.user_id] = count

    public_teacher_form_url = url_for('teachers.public_add_teacher', _external=True)

    return render_template('teachers/list.html',
                         teachers=teachers,
                         pagination=pagination,
                         search=search,
                         status_filter=status_filter,
                         can_view_inactive=is_admin_view,
                         public_teacher_form_url=public_teacher_form_url,
                         teacher_customer_counts=teacher_customer_counts)


@teachers_bp.route('/generate-external-edit-link/<int:teacher_id>', methods=['POST'])
@login_required
@admin_required
def generate_external_edit_link(teacher_id):
    """生成老师信息外部更新链接（30分钟有效）"""
    user = User.query.get_or_404(teacher_id)
    if user.role != 'teacher':
        return jsonify({'success': False, 'message': '仅可为老师账号生成链接'}), 400

    token = generate_external_edit_token(teacher_id)
    external_link = url_for('teachers.external_edit_teacher', token=token, _external=True)
    expires_at = (datetime.utcnow() + timedelta(seconds=EXTERNAL_EDIT_LINK_SECONDS)).strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        'success': True,
        'link': external_link,
        'expires_in_minutes': EXTERNAL_EDIT_LINK_SECONDS // 60,
        'expires_at': expires_at
    })


@teachers_bp.route('/external-edit/<token>', methods=['GET', 'POST'])
def external_edit_teacher(token):
    """老师信息外部更新页（临时签名链接）"""
    try:
        user, teacher = load_teacher_from_external_token(token)
    except SignatureExpired:
        return render_template(
            'teachers/external_edit.html',
            token_valid=False,
            error_message='链接已过期（30分钟）。请联系管理员重新获取。',
            expires_in_minutes=EXTERNAL_EDIT_LINK_SECONDS // 60
        ), 410
    except (BadSignature, ValueError):
        return render_template(
            'teachers/external_edit.html',
            token_valid=False,
            error_message='链接无效，请联系管理员重新获取。',
            expires_in_minutes=EXTERNAL_EDIT_LINK_SECONDS // 60
        ), 400

    if request.method == 'POST':
        try:
            name = request.form.get('chinese_name', '').strip()
            if not name:
                flash('姓名为必填项', 'error')
                education_initial = parse_education_summary(teacher)
                return render_template(
                    'teachers/external_edit.html',
                    token_valid=True,
                    user=user,
                    teacher=teacher,
                    education_initial=education_initial,
                    expires_in_minutes=EXTERNAL_EDIT_LINK_SECONDS // 60
                )

            education_updated = education_form_has_updates(request.form)
            highest_degree, degree_description = build_education_summary(request.form)

            user.username = name
            teacher.current_institution = request.form.get('current_institution', '').strip()
            teacher.major_direction = request.form.get('major_direction', '').strip()
            if education_updated:
                teacher.highest_degree = highest_degree
                teacher.degree_description = degree_description
            teacher.research_achievements = request.form.get('research_achievements', '').strip()
            teacher.innovation_coaching_achievements = request.form.get('innovation_coaching_achievements', '').strip()
            teacher.social_roles = request.form.get('social_roles', '').strip()
            teacher.updated_at = datetime.utcnow()

            db.session.commit()
            flash('信息更新成功', 'success')
            return redirect(url_for('teachers.external_edit_teacher', token=token))
        except Exception as e:
            db.session.rollback()
            flash(f'更新失败：{str(e)}', 'error')

    education_initial = parse_education_summary(teacher)
    return render_template(
        'teachers/external_edit.html',
        token_valid=True,
        user=user,
        teacher=teacher,
        education_initial=education_initial,
        expires_in_minutes=EXTERNAL_EDIT_LINK_SECONDS // 60
    )


@teachers_bp.route('/public-add', methods=['GET', 'POST'])
def public_add_teacher():
    """公开老师填写页（无需登录，提交后默认禁用，待后台启用）"""
    if request.method == 'POST':
        try:
            phone = request.form.get('phone', '').strip()
            if not phone:
                flash('手机号为必填项', 'error')
                return render_template('teachers/public_add.html')

            import re
            if not re.match(r'^1[3-9]\d{9}$', phone):
                flash('手机号格式不正确', 'error')
                return render_template('teachers/public_add.html')

            existing = User.query.filter_by(phone=phone).first()
            if existing:
                flash('该手机号已被使用', 'error')
                return render_template('teachers/public_add.html')

            name = request.form.get('chinese_name', '').strip()
            if not name:
                flash('中文名为必填项', 'error')
                return render_template('teachers/public_add.html')

            highest_degree, degree_description = build_education_summary(request.form)

            # 公开填写创建的老师默认禁用，待管理员审核后启用
            user = User(
                username=name,
                phone=phone,
                role='teacher',
                status=False,
                must_change_password=True,
                password_changed_at=None
            )
            user.set_password(User.DEFAULT_PASSWORD)
            db.session.add(user)
            db.session.flush()

            teacher = Teacher(
                user_id=user.id,
                current_institution=request.form.get('current_institution', '').strip(),
                major_direction=request.form.get('major_direction', '').strip(),
                highest_degree=highest_degree,
                degree_description=degree_description,
                research_achievements=request.form.get('research_achievements', '').strip(),
                innovation_coaching_achievements=request.form.get('innovation_coaching_achievements', '').strip(),
                social_roles=request.form.get('social_roles', '').strip(),
                email=request.form.get('email', '').strip(),
                subject=request.form.get('subject', '').strip()
            )
            db.session.add(teacher)
            db.session.commit()

            flash('提交成功，信息已进入后台，账号默认禁用，管理员审核后启用。', 'success')
            return redirect(url_for('teachers.public_add_teacher'))

        except Exception as e:
            db.session.rollback()
            flash(f'提交失败：{str(e)}', 'error')
            return render_template('teachers/public_add.html')

    return render_template('teachers/public_add.html')

@teachers_bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_teacher():
    """添加辅导老师（User 表存储登录信息，Teacher 表存储专业信息）"""
    if request.method == 'POST':
        try:
            # 获取手机号
            phone = request.form.get('phone', '').strip()

            if not phone:
                flash('手机号为必填项', 'error')
                return render_template('teachers/add.html')

            # 验证手机号格式
            import re
            if not re.match(r'^1[3-9]\d{9}$', phone):
                flash('手机号格式不正确', 'error')
                return render_template('teachers/add.html')

            # 检查手机号是否已存在
            existing = User.query.filter_by(phone=phone).first()
            if existing:
                flash('该手机号已被使用', 'error')
                return render_template('teachers/add.html')

            # 获取表单数据
            name = request.form.get('chinese_name', '').strip()
            if not name:
                flash('中文名为必填项', 'error')
                return render_template('teachers/add.html')

            highest_degree, degree_description = build_education_summary(request.form)

            # 创建用户（role='teacher'）
            user = User(
                username=name,
                phone=phone,
                role='teacher',
                status=True,
                must_change_password=True,
                password_changed_at=None
            )
            user.set_password(User.DEFAULT_PASSWORD)
            db.session.add(user)
            db.session.flush()  # 获取 user.id

            # 创建老师专业信息
            teacher = Teacher(
                user_id=user.id,
                current_institution=request.form.get('current_institution', '').strip(),
                major_direction=request.form.get('major_direction', '').strip(),
                highest_degree=highest_degree,
                degree_description=degree_description,
                research_achievements=request.form.get('research_achievements', '').strip(),
                innovation_coaching_achievements=request.form.get('innovation_coaching_achievements', '').strip(),
                social_roles=request.form.get('social_roles', '').strip(),
                email=request.form.get('email', '').strip(),
                subject=request.form.get('subject', '').strip()
            )
            db.session.add(teacher)
            db.session.commit()

            flash(f'辅导老师 {name} 添加成功，初始密码：{User.DEFAULT_PASSWORD}（首次登录需修改）', 'success')
            return redirect(url_for('teachers.list_teachers'))

        except Exception as e:
            db.session.rollback()
            flash(f'添加老师失败：{str(e)}', 'error')
            return render_template('teachers/add.html')

    return render_template('teachers/add.html')

@teachers_bp.route('/edit/<int:teacher_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_teacher(teacher_id):
    """编辑辅导老师"""
    # teacher_id 实际是 User.id
    user = User.query.get_or_404(teacher_id)

    # 权限检查：仅允许编辑老师账号
    if user.role != 'teacher':
        flash('仅可编辑老师账号', 'error')
        return redirect(url_for('teachers.list_teachers'))

    # 获取关联的 Teacher 记录
    teacher = Teacher.query.filter_by(user_id=teacher_id).first()
    if not teacher:
        flash('老师信息不存在', 'error')
        return redirect(url_for('teachers.list_teachers'))

    if request.method == 'POST':
        try:
            name = request.form.get('chinese_name', '').strip()
            if not name:
                flash('中文名为必填项', 'error')
                education_initial = parse_education_summary(teacher)
                return render_template('teachers/edit.html', teacher=teacher, user=user, education_initial=education_initial)

            phone = request.form.get('phone', '').strip()
            if not phone:
                flash('手机号为必填项', 'error')
                education_initial = parse_education_summary(teacher)
                return render_template('teachers/edit.html', teacher=teacher, user=user, education_initial=education_initial)

            import re
            if not re.match(r'^1[3-9]\d{9}$', phone):
                flash('手机号格式不正确', 'error')
                education_initial = parse_education_summary(teacher)
                return render_template('teachers/edit.html', teacher=teacher, user=user, education_initial=education_initial)

            existing = User.query.filter(User.phone == phone, User.id != user.id).first()
            if existing:
                flash('该手机号已被使用', 'error')
                education_initial = parse_education_summary(teacher)
                return render_template('teachers/edit.html', teacher=teacher, user=user, education_initial=education_initial)

            education_updated = education_form_has_updates(request.form)
            highest_degree, degree_description = build_education_summary(request.form)

            # 更新 User 表
            user.username = name
            user.phone = phone
            teacher.current_institution = request.form.get('current_institution', '').strip()
            teacher.major_direction = request.form.get('major_direction', '').strip()
            if education_updated:
                teacher.highest_degree = highest_degree
                teacher.degree_description = degree_description
            teacher.research_achievements = request.form.get('research_achievements', '').strip()
            teacher.innovation_coaching_achievements = request.form.get('innovation_coaching_achievements', '').strip()
            teacher.social_roles = request.form.get('social_roles', '').strip()
            teacher.updated_at = datetime.utcnow()

            db.session.commit()

            flash(f'辅导老师 {name} 更新成功', 'success')
            return redirect(url_for('teachers.list_teachers'))

        except Exception as e:
            db.session.rollback()
            flash(f'更新老师失败：{str(e)}', 'error')

    education_initial = parse_education_summary(teacher)
    return render_template('teachers/edit.html', teacher=teacher, user=user, education_initial=education_initial)

@teachers_bp.route('/detail/<int:teacher_id>')
@login_required
@teacher_supervisor_or_admin_required
def detail_teacher(teacher_id):
    """辅导老师详情页"""
    # teacher_id 实际是 User.id
    user = User.query.get_or_404(teacher_id)

    # 权限检查：仅允许查看老师账号
    if user.role != 'teacher':
        flash('仅可查看老师账号', 'error')
        return redirect(url_for('teachers.list_teachers'))
    if not current_user.is_admin() and not user.status:
        flash('该老师已停用，仅管理员可查看', 'error')
        return redirect(url_for('teachers.list_teachers'))

    # 获取关联的 Teacher 记录
    teacher = Teacher.query.filter_by(user_id=teacher_id).first()

    # 获取该老师负责的客户列表
    customers = Customer.query.filter(Customer.tutor_user_id == teacher_id).join(Lead).all()

    return render_template('teachers/detail.html',
                         teacher=teacher,
                         user=user,
                         customers=customers)

@teachers_bp.route('/delete/<int:teacher_id>', methods=['POST'])
@login_required
@admin_required
def delete_teacher(teacher_id):
    """删除辅导老师（软删除，设置status=False）"""
    try:
        user = User.query.get_or_404(teacher_id)

        # 权限检查：仅允许停用老师账号
        if user.role != 'teacher':
            flash('仅可停用老师账号', 'error')
            return redirect(url_for('teachers.list_teachers'))

        # 获取 Teacher 记录
        teacher = Teacher.query.filter_by(user_id=teacher_id).first()

        # 软删除
        user.status = False
        db.session.commit()

        teacher_name = teacher.user.username if teacher and teacher.user else user.username
        flash(f'辅导老师 {teacher_name} 已停用', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'删除老师失败：{str(e)}', 'error')

    return redirect(url_for('teachers.list_teachers'))

@teachers_bp.route('/permanent-delete/<int:teacher_id>', methods=['POST'])
@login_required
@admin_required
def permanent_delete_teacher(teacher_id):
    """管理员永久删除老师账号（删除 User + Teacher + 图片 + 登录日志）"""
    try:
        user = User.query.get_or_404(teacher_id)
        if user.role != 'teacher':
            flash('仅可删除老师账号', 'error')
            return redirect(url_for('teachers.list_teachers'))

        customer_count = Customer.query.filter(Customer.tutor_user_id == teacher_id).count()
        if customer_count > 0:
            flash(f'该老师仍负责 {customer_count} 位客户，无法删除', 'error')
            return redirect(url_for('teachers.list_teachers'))

        task_count = TopicTask.query.filter(
            db.or_(TopicTask.tutor_user_id == teacher_id, TopicTask.created_by == teacher_id)
        ).count()
        if task_count > 0:
            flash(f'该老师存在 {task_count} 条课题任务记录，无法删除', 'error')
            return redirect(url_for('teachers.list_teachers'))

        # 先删除图片记录与文件
        images = TeacherImage.query.filter_by(tutor_user_id=teacher_id).all()
        for image in images:
            image_path = os.path.join('static', image.image_path) if image.image_path else None
            db.session.delete(image)
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception:
                    pass

        # 删除老师登录日志
        LoginLog.query.filter_by(user_id=teacher_id).delete()

        # 删除老师资料和账号
        teacher = Teacher.query.filter_by(user_id=teacher_id).first()
        if teacher:
            db.session.delete(teacher)
        db.session.delete(user)
        db.session.commit()

        flash('老师账号已删除', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除老师失败：{str(e)}', 'error')

    return redirect(url_for('teachers.list_teachers'))

@teachers_bp.route('/activate/<int:teacher_id>', methods=['POST'])
@login_required
@admin_required
def activate_teacher(teacher_id):
    """启用辅导老师"""
    try:
        user = User.query.get_or_404(teacher_id)

        # 权限检查：仅允许启用老师账号
        if user.role != 'teacher':
            flash('仅可启用老师账号', 'error')
            return redirect(url_for('teachers.list_teachers'))

        user.status = True
        db.session.commit()

        # 获取 Teacher 记录
        teacher = Teacher.query.filter_by(user_id=teacher_id).first()
        teacher_name = teacher.user.username if teacher and teacher.user else user.username
        flash(f'辅导老师 {teacher_name} 已启用', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'启用老师失败：{str(e)}', 'error')

    return redirect(url_for('teachers.list_teachers'))

@teachers_bp.route('/get_active_teachers', methods=['GET'])
@login_required
def get_active_teachers():
    """获取所有启用的辅导老师（用于分配老师的下拉列表）"""
    # 创建人信息已移除，班主任可分配所有“启用”老师
    if current_user.role not in {'teacher_supervisor', 'admin', 'sales_manager'}:
        return jsonify([])

    users = User.query.filter(
        User.role == 'teacher',
        User.status == True
    ).order_by(User.username.asc()).all()
    user_ids = [u.id for u in users]
    teachers = Teacher.query.filter(Teacher.user_id.in_(user_ids)).all() if user_ids else []

    return jsonify([{
        'id': t.user_id,
        'username': t.user.username if t.user else '',
        'major_direction': t.major_direction
    } for t in teachers])

@teachers_bp.route('/assign/<int:customer_id>', methods=['POST'])
@login_required
def assign_teacher(customer_id):
    """分配辅导老师给客户"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        teacher_id = request.form.get('tutor_user_id', type=int)

        if not teacher_id:
            return jsonify({'success': False, 'message': '请选择老师'}), 400

        user = User.query.get_or_404(teacher_id)

        # 验证是辅导老师且已启用
        if user.role != 'teacher':
            return jsonify({'success': False, 'message': '无效的老师'}), 400
        if not user.status:
            return jsonify({'success': False, 'message': '该老师已被停用'}), 400

        # 检查权限：只有班主任角色可以分配老师
        if current_user.role != 'teacher_supervisor':
            return jsonify({'success': False, 'message': '只有班主任可以分配老师'}), 403
        if customer.supervisor_user_id not in get_visible_teacher_supervisor_ids():
            return jsonify({'success': False, 'message': '您没有权限为该客户分配老师'}), 403

        # 获取老师信息
        teacher = Teacher.query.filter_by(user_id=teacher_id).first()
        teacher_name = teacher.user.username if teacher and teacher.user else user.username

        old_teacher_name = customer.teacher.user.username if customer.teacher and customer.teacher.user else '未分配'
        customer.tutor_user_id = teacher_id
        customer.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'已将老师从 {old_teacher_name} 更换为 {teacher_name}',
            'teacher_name': teacher_name
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'分配老师失败：{str(e)}'}), 500

@teachers_bp.route('/change/<int:customer_id>', methods=['POST'])
@login_required
def change_teacher(customer_id):
    """更换客户的辅导老师（需要二次确认）"""
    try:
        customer = Customer.query.get_or_404(customer_id)

        # 获取JSON数据
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400

        teacher_id = data.get('tutor_user_id')
        confirmed = data.get('confirmed', False)

        if not teacher_id:
            return jsonify({'success': False, 'message': '请选择老师'}), 400

        # 转换为整数
        try:
            teacher_id = int(teacher_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': '无效的老师ID'}), 400

        user = User.query.get_or_404(teacher_id)

        # 验证是辅导老师且已启用
        if user.role != 'teacher':
            return jsonify({'success': False, 'message': '无效的老师'}), 400
        if not user.status:
            return jsonify({'success': False, 'message': '该老师已被停用'}), 400

        # 检查权限：只有班主任角色可以更换老师
        if current_user.role != 'teacher_supervisor':
            return jsonify({'success': False, 'message': '只有班主任可以更换老师'}), 403
        if customer.supervisor_user_id not in get_visible_teacher_supervisor_ids():
            return jsonify({'success': False, 'message': '您没有权限为该客户更换老师'}), 403

        # 获取老师信息
        teacher = Teacher.query.filter_by(user_id=teacher_id).first()
        teacher_name = teacher.user.username if teacher and teacher.user else user.username

        # 如果未确认，返回需要确认的信息
        if not confirmed:
            old_teacher_name = customer.teacher.user.username if customer.teacher and customer.teacher.user else '未分配'
            return jsonify({
                'success': False,
                'need_confirm': True,
                'message': f'确定要将老师从 {old_teacher_name} 更换为 {teacher_name} 吗？'
            })

        # 已确认，执行更换
        old_teacher_name = customer.teacher.user.username if customer.teacher and customer.teacher.user else '未分配'
        customer.tutor_user_id = teacher_id
        customer.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'已将老师从 {old_teacher_name} 更换为 {teacher_name}',
            'teacher_name': teacher_name
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更换老师失败：{str(e)}'}), 500


# 图片上传相关配置
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_IMAGES_PER_TEACHER = 5
UPLOAD_FOLDER = 'static/uploads/teacher_images'

def allowed_image_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

@teachers_bp.route('/upload-image/<int:teacher_id>', methods=['POST'])
@login_required
@admin_required
def upload_teacher_image(teacher_id):
    """上传辅导老师图片"""
    teacher = User.query.get_or_404(teacher_id)

    # 权限检查：仅允许管理员为老师账号上传图片
    if teacher.role != 'teacher':
        return jsonify({'success': False, 'message': '仅可为老师账号上传图片'}), 403

    # 检查当前图片数量
    current_image_count = TeacherImage.query.filter_by(tutor_user_id=teacher_id).count()
    if current_image_count >= MAX_IMAGES_PER_TEACHER:
        return jsonify({'success': False, 'message': f'最多只能上传{MAX_IMAGES_PER_TEACHER}张图片'}), 400

    # 检查是否有文件
    if 'images' not in request.files:
        return jsonify({'success': False, 'message': '请选择要上传的图片'}), 400

    files = request.files.getlist('images')
    descriptions = request.form.getlist('descriptions')

    if not files or files[0].filename == '':
        return jsonify({'success': False, 'message': '请选择要上传的图片'}), 400

    # 检查上传数量
    if len(files) + current_image_count > MAX_IMAGES_PER_TEACHER:
        return jsonify({'success': False, 'message': f'最多只能上传{MAX_IMAGES_PER_TEACHER}张图片，当前已有{current_image_count}张'}), 400

    try:
        # 确保上传目录存在
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
            filename = f"teacher_{teacher_id}_{timestamp}_{idx}_{original_filename}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)

            # 保存文件
            file.save(filepath)

            # 获取对应的描述
            description = descriptions[idx] if idx < len(descriptions) else ''

            # 保存到数据库
            teacher_image = TeacherImage(
                tutor_user_id=teacher_id,
                image_path=f'uploads/teacher_images/{filename}',
                description=description.strip(),
                file_size=file_size,
                file_name=original_filename
            )
            db.session.add(teacher_image)
            uploaded_images.append({
                'id': teacher_image.id,
                'filename': original_filename,
                'description': description
            })

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'成功上传{len(uploaded_images)}张图片',
            'images': uploaded_images
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'上传失败：{str(e)}'}), 500

@teachers_bp.route('/delete-image/<int:image_id>', methods=['POST'])
@login_required
@admin_required
def delete_teacher_image(image_id):
    """删除辅导老师图片"""
    try:
        image = TeacherImage.query.get_or_404(image_id)
        teacher = User.query.get_or_404(image.tutor_user_id)

        # 权限检查：仅允许管理员删除老师账号图片
        if teacher.role != 'teacher':
            return jsonify({'success': False, 'message': '仅可删除老师账号图片'}), 403

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
                # 记录日志，但不影响主流程
                import logging
                logging.warning(f"文件删除失败: {filepath}, 错误: {e}")

        return jsonify({'success': True, 'message': '图片删除成功'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败：{str(e)}'}), 500

@teachers_bp.route('/update-image-description/<int:image_id>', methods=['POST'])
@login_required
@admin_required
def update_image_description(image_id):
    """更新辅导老师图片描述"""
    try:
        image = TeacherImage.query.get_or_404(image_id)
        teacher = User.query.get_or_404(image.tutor_user_id)

        # 权限检查：仅允许管理员更新老师账号图片描述
        if teacher.role != 'teacher':
            return jsonify({'success': False, 'message': '仅可更新老师账号图片描述'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400

        description = data.get('description', '').strip()
        image.description = description

        db.session.commit()

        return jsonify({'success': True, 'message': '描述更新成功'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'}), 500


# ==================== 销售管理角色专用路由 ====================

@teachers_bp.route('/list_for_sales')
@login_required
@sales_manager_required
def list_teachers_for_sales():
    """销售管理角色的辅导老师列表页（只读，role='teacher'）"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    status_filter = 'active'

    # 销售管理仅可查看启用中的辅导老师
    query = Teacher.query.join(User, Teacher.user_id == User.id).filter(
        User.role == 'teacher',
        User.status == True
    )

    # 搜索过滤
    if search:
        query = query.filter(
            (User.username.contains(search)) |
            (Teacher.current_institution.contains(search)) |
            (Teacher.major_direction.contains(search))
        )

    # 按账号创建时间倒序排列
    query = query.order_by(User.created_at.desc())

    # 分页
    per_page = 20
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    teachers = pagination.items

    # 统计每个老师负责的客户数量
    teacher_customer_counts = {}
    for teacher in teachers:
        count = Customer.query.filter(Customer.tutor_user_id == teacher.user_id).count()
        teacher_customer_counts[teacher.user_id] = count

    return render_template('teachers/list_for_sales.html',
                         teachers=teachers,
                         pagination=pagination,
                         search=search,
                         status_filter=status_filter,
                         teacher_customer_counts=teacher_customer_counts)

@teachers_bp.route('/detail_for_sales/<int:teacher_id>')
@login_required
@sales_manager_required
def detail_teacher_for_sales(teacher_id):
    """销售管理角色的老师详情页（只读）"""
    teacher = Teacher.query.join(User, Teacher.user_id == User.id).filter(
        Teacher.user_id == teacher_id,
        User.role == 'teacher',
        User.status == True
    ).first()
    if not teacher:
        flash('该老师已停用或不存在', 'error')
        return redirect(url_for('teachers.list_teachers_for_sales'))

    # 获取该老师负责的客户列表
    customers = Customer.query.filter(Customer.tutor_user_id == teacher_id).join(Lead).all()

    return render_template('teachers/detail.html',
                         teacher=teacher,
                         customers=customers,
                         is_sales_manager_view=True)  # 标记为销售管理视图
