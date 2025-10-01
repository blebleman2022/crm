from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user

def require_roles(*roles):
    """
    权限装饰器，要求用户具有指定角色之一
    
    Args:
        *roles: 允许的角色列表，如 'admin', 'sales', 'teacher'
    
    Usage:
        @require_roles('admin')
        @require_roles('admin', 'sales')
        @require_roles('teacher')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('请先登录以访问此页面', 'error')
                return redirect(url_for('auth.login'))
            
            if current_user.role not in roles:
                flash('您没有权限访问此页面', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """管理员权限装饰器"""
    return require_roles('admin')(f)

def sales_manager_required(f):
    """销售管理权限装饰器"""
    return require_roles('sales_manager')(f)

def salesperson_required(f):
    """销售权限装饰器"""
    return require_roles('salesperson')(f)

def sales_required(f):
    """销售相关权限装饰器（包括销售管理和销售）"""
    return require_roles('sales_manager', 'salesperson')(f)

def teacher_required(f):
    """班主任权限装饰器"""
    return require_roles('teacher')(f)

def sales_manager_or_admin_required(f):
    """销售管理或管理员权限装饰器"""
    return require_roles('sales_manager', 'admin')(f)

def sales_or_admin_required(f):
    """销售相关或管理员权限装饰器"""
    return require_roles('sales_manager', 'salesperson', 'admin')(f)

def teacher_or_admin_required(f):
    """班主任或管理员权限装饰器"""
    return require_roles('teacher', 'admin')(f)

def check_data_access_permission(user, target_user_id=None, customer_id=None, lead_id=None):
    """
    检查用户是否有权限访问特定数据
    
    Args:
        user: 当前用户对象
        target_user_id: 目标用户ID（用于检查是否可以访问其他用户的数据）
        customer_id: 客户ID（用于检查是否可以访问特定客户数据）
        lead_id: 线索ID（用于检查是否可以访问特定线索数据）
    
    Returns:
        bool: 是否有权限访问
    """
    # 管理员可以访问所有数据
    if user.role == 'admin':
        return True
    
    # 检查用户数据访问权限
    if target_user_id:
        # 用户只能访问自己的数据
        if user.id != target_user_id:
            return False
    
    # 检查客户数据访问权限
    if customer_id:
        from models import Customer
        customer = Customer.query.get(customer_id)
        if not customer:
            return False
        
        # 销售管理和销售可以访问自己负责的客户
        if user.role in ['sales_manager', 'salesperson']:
            return customer.sales_user_id == user.id
        
        # 班主任可以访问分配给自己的客户
        if user.role == 'teacher':
            return customer.teacher_user_id == user.id
    
    # 检查线索数据访问权限
    if lead_id:
        from models import Lead
        lead = Lead.query.get(lead_id)
        if not lead:
            return False
        
        # 销售管理和销售可以访问自己负责的线索
        if user.role in ['sales_manager', 'salesperson']:
            return lead.sales_user_id == user.id
        
        # 班主任不能直接访问线索数据
        if user.role == 'teacher':
            return False
    
    return True

def require_data_access(customer_id=None, lead_id=None, target_user_id=None):
    """
    数据访问权限装饰器
    
    Args:
        customer_id: 客户ID参数名（从路由参数中获取）
        lead_id: 线索ID参数名（从路由参数中获取）
        target_user_id: 目标用户ID参数名（从路由参数中获取）
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('请先登录以访问此页面', 'error')
                return redirect(url_for('auth.login'))
            
            # 获取参数值
            customer_id_value = kwargs.get(customer_id) if customer_id else None
            lead_id_value = kwargs.get(lead_id) if lead_id else None
            target_user_id_value = kwargs.get(target_user_id) if target_user_id else None
            
            # 检查数据访问权限
            if not check_data_access_permission(
                current_user, 
                target_user_id=target_user_id_value,
                customer_id=customer_id_value,
                lead_id=lead_id_value
            ):
                flash('您没有权限访问此数据', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_accessible_data_filter(user, model_class):
    """
    根据用户角色获取可访问数据的过滤条件
    
    Args:
        user: 当前用户对象
        model_class: 模型类（Lead, Customer等）
    
    Returns:
        SQLAlchemy查询过滤条件
    """
    # 管理员可以访问所有数据
    if user.role == 'admin':
        return None
    
    # 销售管理和销售只能访问自己负责的数据
    if user.role in ['sales_manager', 'salesperson']:
        if model_class.__name__ == 'Lead':
            return model_class.sales_user_id == user.id
        elif model_class.__name__ == 'Customer':
            # 销售角色只能看到已分配班主任的客户
            if user.role == 'salesperson':
                return (model_class.sales_user_id == user.id) & (model_class.teacher_user_id.isnot(None))
            else:  # sales_manager
                return model_class.sales_user_id == user.id
    
    # 班主任只能访问分配给自己的客户数据
    if user.role == 'teacher':
        if model_class.__name__ == 'Customer':
            return model_class.teacher_user_id == user.id
        elif model_class.__name__ == 'TutoringDelivery':
            from models import Customer
            return model_class.customer_id.in_(
                Customer.query.filter_by(teacher_user_id=user.id).with_entities(Customer.id)
            )
        elif model_class.__name__ == 'CompetitionDelivery':
            from models import Customer
            return model_class.customer_id.in_(
                Customer.query.filter_by(teacher_user_id=user.id).with_entities(Customer.id)
            )
    
    # 默认返回空结果
    return model_class.id == -1
