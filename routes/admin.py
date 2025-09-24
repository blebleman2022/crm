from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import User, LoginLog, db
from datetime import datetime, timedelta
import re

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
        status = request.form.get('status') == 'on'
        
        if not username:
            flash('用户名为必填项', 'error')
            return render_template('admin/edit_user.html', user=user)
        
        try:
            user.username = username
            user.group_name = group_name if group_name else None
            user.status = status
            user.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash(f'用户 {username} 更新成功', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash(f'更新用户失败: {str(e)}', 'error')
    
    return render_template('admin/edit_user.html', user=user)

@admin_bp.route('/users/<int:user_id>/toggle_status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """切换用户状态"""
    user = User.query.get_or_404(user_id)

    # 不能禁用自己
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': '不能禁用自己的账号'})

    try:
        user.status = not user.status
        user.updated_at = datetime.utcnow()
        db.session.commit()

        status_text = '启用' if user.status else '禁用'
        return jsonify({
            'success': True,
            'message': f'用户 {user.username} 已{status_text}',
            'status': user.status
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})

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
