from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from models import User, LoginLog, db
from datetime import datetime
import re

auth_bp = Blueprint('auth', __name__)

def validate_phone(phone):
    """验证手机号格式"""
    pattern = r'^1[3-9]\d{9}$'
    return re.match(pattern, phone) is not None

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
    """手机号免密登录 - 支持所有角色（admin/sales_manager/salesperson/teacher_supervisor/teacher）"""
    if current_user.is_authenticated:
        # 添加调试日志
        print(f"[DEBUG] login - 用户已登录: {current_user.is_authenticated}")
        print(f"[DEBUG] login - hasattr role: {hasattr(current_user, 'role')}")
        if hasattr(current_user, 'role'):
            print(f"[DEBUG] login - role: {current_user.role}")

        # 已登录用户根据角色重定向
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role in ['sales_manager', 'salesperson']:
            return redirect(url_for('leads.dashboard'))
        elif current_user.role == 'teacher_supervisor':
            return redirect(url_for('delivery.dashboard'))
        elif current_user.role == 'teacher':
            print(f"[DEBUG] login - 重定向到 teacher.student_list")
            return redirect(url_for('teacher.student_list'))
        else:
            flash('用户角色异常，请联系管理员', 'error')
            return redirect(url_for('auth.logout'))

    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()

        # 验证手机号格式
        if not phone:
            flash('请输入手机号', 'error')
            return render_template('auth/login.html')

        if not validate_phone(phone):
            flash('手机号格式不正确', 'error')
            log_login_attempt(phone, result='failed')
            return render_template('auth/login.html')

        # 只查询 User 表
        user = User.query.filter_by(phone=phone).first()

        if not user:
            flash('手机号未注册，请联系管理员', 'error')
            log_login_attempt(phone, result='failed')
            return render_template('auth/login.html')

        if not user.status:
            flash('账号已被禁用，请联系管理员', 'error')
            log_login_attempt(phone, user_id=user.id, result='failed')
            return render_template('auth/login.html')

        # 登录成功
        login_user(user, remember=True)
        log_login_attempt(phone, user_id=user.id, result='success')

        # 根据角色重定向
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)

        if user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user.role in ['sales_manager', 'salesperson']:
            return redirect(url_for('leads.dashboard'))
        elif user.role == 'teacher_supervisor':
            return redirect(url_for('delivery.dashboard'))
        elif user.role == 'teacher':
            # 辅导老师显示中文名
            name = user.username
            flash(f'欢迎回来，{name}老师！', 'success')
            return redirect(url_for('teacher.student_list'))
        else:
            flash('用户角色异常，请联系管理员', 'error')
            return render_template('auth/login.html')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash('您已成功登出', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/check_session')
@login_required
def check_session():
    """检查会话状态（AJAX接口）"""
    if current_user.role == 'teacher':
        name = current_user.username
        return {'status': 'active', 'user': name, 'type': 'teacher'}
    return {'status': 'active', 'user': current_user.username, 'type': 'user'}

@auth_bp.before_app_request
def check_user_status():
    """检查用户状态中间件"""
    if current_user.is_authenticated:
        # 检查用户是否被禁用
        if not current_user.status:
            logout_user()
            flash('您的账号已被禁用，请联系管理员', 'error')
            return redirect(url_for('auth.login'))

        # 更新最后活动时间
        session.permanent = True
