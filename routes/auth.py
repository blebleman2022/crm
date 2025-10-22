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
    """手机号免密登录"""
    if current_user.is_authenticated:
        # 已登录用户根据角色重定向
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role in ['sales_manager', 'salesperson']:
            return redirect(url_for('leads.dashboard'))
        elif current_user.role == 'teacher_supervisor':
            return redirect(url_for('delivery.dashboard'))
    
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
        
        # 查找用户
        user = User.query.filter_by(phone=phone).first()
        
        if not user:
            flash('手机号未注册或已禁用，请联系管理员', 'error')
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
    return {'status': 'active', 'user': current_user.username}

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
