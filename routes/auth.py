from datetime import datetime
import re

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user

from models import User, LoginLog, AdminImpersonationLog, db

auth_bp = Blueprint('auth', __name__)

PASSWORD_MIN_LENGTH = 6
PASSWORD_MAX_LENGTH = 32


def validate_phone(phone):
    """验证手机号格式"""
    pattern = r'^1[3-9]\d{9}$'
    return re.match(pattern, phone) is not None


def validate_new_password(new_password):
    """校验新密码格式"""
    if not new_password:
        return False, '请输入新密码'
    if len(new_password) < PASSWORD_MIN_LENGTH or len(new_password) > PASSWORD_MAX_LENGTH:
        return False, f'密码长度需在{PASSWORD_MIN_LENGTH}-{PASSWORD_MAX_LENGTH}位之间'
    if new_password == User.DEFAULT_PASSWORD:
        return False, '新密码不能与初始密码相同'
    return True, ''


def role_home_endpoint(user):
    """根据角色返回首页 endpoint"""
    if user.role == 'admin':
        return 'admin.dashboard'
    if user.role in ['sales_manager', 'salesperson']:
        return 'leads.dashboard'
    if user.role == 'teacher_supervisor':
        if user.is_private_only_teacher_supervisor():
            return 'customers.list_customers'
        return 'delivery.dashboard'
    if user.role == 'teacher':
        return 'teacher.student_list'
    return 'auth.logout'


def redirect_role_home(user):
    """按角色跳转首页"""
    return redirect(url_for(role_home_endpoint(user)))


def is_impersonating():
    """当前会话是否处于管理员代登入状态"""
    return bool(session.get('impersonator_user_id'))


def clear_impersonation_session():
    """清理代登入会话信息"""
    for key in [
        'impersonator_user_id',
        'impersonator_username',
        'impersonation_log_id',
        'impersonated_user_id',
        'impersonation_started_at',
    ]:
        session.pop(key, None)


def log_login_attempt(phone, user_id=None, result='success', ip_address=None, user_agent=None):
    """记录登录日志"""
    try:
        log = LoginLog(
            user_id=user_id,
            phone=phone,
            login_time=datetime.utcnow(),
            ip_address=ip_address or request.remote_addr,
            user_agent=user_agent or request.headers.get('User-Agent', ''),
            login_result=result
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"记录登录日志失败: {e}")


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """手机号+密码登录（支持所有角色）"""
    maintenance_entry = (request.args.get('maintenance_entry') or request.form.get('maintenance_entry') or '').strip().lower()
    maintenance_admin_only = maintenance_entry == 'admin'

    if current_user.is_authenticated:
        if maintenance_admin_only and current_user.role != 'admin':
            logout_user()
            clear_impersonation_session()
            flash('维护模式入口仅允许管理员登录', 'error')
            return redirect(url_for('auth.login', maintenance_entry='admin'))
        return redirect_role_home(current_user)

    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')

        if not phone:
            flash('请输入手机号', 'error')
            return render_template('auth/login.html')

        if not password:
            flash('请输入密码', 'error')
            return render_template('auth/login.html')

        if not validate_phone(phone):
            flash('手机号格式不正确', 'error')
            log_login_attempt(phone, result='failed')
            return render_template('auth/login.html')

        user = User.query.filter_by(phone=phone).first()
        if not user:
            flash('账号或密码错误', 'error')
            log_login_attempt(phone, result='failed')
            return render_template('auth/login.html')

        if not user.status:
            flash('账号已被禁用，请联系管理员', 'error')
            log_login_attempt(phone, user_id=user.id, result='failed')
            return render_template('auth/login.html')

        if maintenance_admin_only and user.role != 'admin':
            flash('维护模式入口仅允许管理员登录', 'error')
            log_login_attempt(phone, user_id=user.id, result='failed')
            return render_template('auth/login.html')

        # 兼容历史账号：无密码哈希时自动初始化为默认密码并强制改密
        if not user.password_hash:
            user.set_password(User.DEFAULT_PASSWORD)
            user.must_change_password = True
            user.password_changed_at = None
            db.session.commit()

        if not user.check_password(password):
            flash('账号或密码错误', 'error')
            log_login_attempt(phone, user_id=user.id, result='failed')
            return render_template('auth/login.html')

        login_user(user, remember=True)
        clear_impersonation_session()
        log_login_attempt(phone, user_id=user.id, result='success')

        if user.must_change_password:
            return redirect(url_for('auth.force_change_password'))

        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect_role_home(user)

    return render_template('auth/login.html')


@auth_bp.route('/force-change-password', methods=['GET', 'POST'])
@login_required
def force_change_password():
    """首次登录强制改密"""
    if is_impersonating():
        return redirect_role_home(current_user)

    if not current_user.must_change_password:
        return redirect_role_home(current_user)

    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not current_user.check_password(current_password):
            flash('当前密码错误', 'error')
            return render_template('auth/force_change_password.html')

        is_valid, message = validate_new_password(new_password)
        if not is_valid:
            flash(message, 'error')
            return render_template('auth/force_change_password.html')

        if new_password != confirm_password:
            flash('两次输入的新密码不一致', 'error')
            return render_template('auth/force_change_password.html')

        current_user.set_password(new_password)
        current_user.must_change_password = False
        current_user.password_changed_at = datetime.utcnow()
        db.session.commit()
        flash('密码修改成功，请妥善保管新密码', 'success')
        return redirect_role_home(current_user)

    return render_template('auth/force_change_password.html')


@auth_bp.route('/settings/password', methods=['GET', 'POST'])
@login_required
def settings_password():
    """账号设置 - 修改密码"""
    if is_impersonating():
        flash('代登入状态下不可修改密码，请先退出代登入', 'error')
        return redirect_role_home(current_user)

    if current_user.must_change_password:
        return redirect(url_for('auth.force_change_password'))

    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not current_user.check_password(current_password):
            flash('当前密码错误', 'error')
            return render_template('auth/password_settings.html')

        is_valid, message = validate_new_password(new_password)
        if not is_valid:
            flash(message, 'error')
            return render_template('auth/password_settings.html')

        if new_password != confirm_password:
            flash('两次输入的新密码不一致', 'error')
            return render_template('auth/password_settings.html')

        if current_user.check_password(new_password):
            flash('新密码不能与当前密码相同', 'error')
            return render_template('auth/password_settings.html')

        current_user.set_password(new_password)
        current_user.must_change_password = False
        current_user.password_changed_at = datetime.utcnow()
        db.session.commit()
        flash('密码修改成功', 'success')
        return redirect(url_for('auth.settings_password'))

    return render_template('auth/password_settings.html')


@auth_bp.route('/impersonation/stop', methods=['POST'])
@login_required
def stop_impersonation():
    """退出代登入，恢复管理员账号"""
    impersonator_user_id = session.get('impersonator_user_id')
    if not impersonator_user_id:
        flash('当前不在代登入状态', 'info')
        return redirect_role_home(current_user)

    admin_user = User.query.get(impersonator_user_id)
    if not admin_user or not admin_user.is_admin():
        clear_impersonation_session()
        logout_user()
        flash('代登入会话异常，请重新登录', 'error')
        return redirect(url_for('auth.login'))

    log_id = session.get('impersonation_log_id')
    if log_id:
        try:
            log = AdminImpersonationLog.query.get(log_id)
            if log and not log.ended_at:
                log.ended_at = datetime.utcnow()
                db.session.commit()
        except Exception:
            db.session.rollback()

    clear_impersonation_session()
    login_user(admin_user, remember=True)
    flash(f'已退出代登入，当前账号：{admin_user.username}', 'success')
    return redirect(url_for('admin.dashboard'))


@auth_bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    clear_impersonation_session()
    logout_user()
    flash('您已成功登出', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/check_session')
@login_required
def check_session():
    """检查会话状态（AJAX接口）"""
    if current_user.role == 'teacher':
        name = current_user.username
        return {'status': 'active', 'user': name, 'type': 'teacher', 'is_impersonating': is_impersonating()}
    return {'status': 'active', 'user': current_user.username, 'type': 'user', 'is_impersonating': is_impersonating()}


@auth_bp.before_app_request
def check_user_status():
    """检查用户状态和首次改密中间件"""
    if not current_user.is_authenticated:
        return None

    if not current_user.status:
        clear_impersonation_session()
        logout_user()
        flash('您的账号已被禁用，请联系管理员', 'error')
        return redirect(url_for('auth.login'))

    session.permanent = True

    # 管理员代登入期间，不触发首次改密拦截
    if is_impersonating():
        return None

    if not getattr(current_user, 'must_change_password', False):
        return None

    endpoint = request.endpoint or ''
    if endpoint.startswith('static'):
        return None

    allowed_endpoints = {
        'auth.force_change_password',
        'auth.logout',
        'auth.check_session',
    }
    if endpoint in allowed_endpoints:
        return None

    return redirect(url_for('auth.force_change_password'))
