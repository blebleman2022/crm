import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from models import User, Lead, Customer, CompetitionConfig

def validate_phone(phone):
    """
    验证手机号格式
    
    Args:
        phone (str): 手机号码
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not phone:
        return False, "手机号不能为空"
    
    # 去除空格和特殊字符
    phone = re.sub(r'[^\d]', '', phone)
    
    # 中国大陆手机号格式验证
    pattern = r'^1[3-9]\d{9}$'
    if not re.match(pattern, phone):
        return False, "手机号格式不正确，请输入11位有效手机号"
    
    return True, ""

def validate_username(username, exclude_user_id=None):
    """
    验证用户名
    
    Args:
        username (str): 用户名
        exclude_user_id (int): 排除的用户ID（用于编辑时检查）
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not username:
        return False, "用户名不能为空"
    
    if len(username) < 2:
        return False, "用户名至少需要2个字符"
    
    if len(username) > 50:
        return False, "用户名不能超过50个字符"
    
    # 检查用户名是否已存在
    query = User.query.filter_by(username=username)
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)
    
    if query.first():
        return False, "用户名已存在"
    
    return True, ""

def validate_phone_unique(phone, exclude_user_id=None):
    """
    验证手机号唯一性
    
    Args:
        phone (str): 手机号码
        exclude_user_id (int): 排除的用户ID（用于编辑时检查）
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not phone:
        return False, "手机号不能为空"
    
    # 检查手机号是否已存在
    query = User.query.filter_by(phone=phone)
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)
    
    if query.first():
        return False, "手机号已被其他用户使用"
    
    return True, ""

def validate_decimal(value, field_name="金额", min_value=0, max_value=None):
    """
    验证金额格式
    
    Args:
        value (str): 金额字符串
        field_name (str): 字段名称
        min_value (float): 最小值
        max_value (float): 最大值
    
    Returns:
        tuple: (is_valid, decimal_value, error_message)
    """
    if not value:
        return False, None, f"{field_name}不能为空"
    
    try:
        decimal_value = Decimal(str(value))
        
        if min_value is not None and decimal_value < Decimal(str(min_value)):
            return False, None, f"{field_name}不能小于{min_value}"
        
        if max_value is not None and decimal_value > Decimal(str(max_value)):
            return False, None, f"{field_name}不能大于{max_value}"
        
        return True, decimal_value, ""
    except (InvalidOperation, ValueError):
        return False, None, f"{field_name}格式不正确"

def validate_date(date_str, field_name="日期", allow_empty=True):
    """
    验证日期格式
    
    Args:
        date_str (str): 日期字符串
        field_name (str): 字段名称
        allow_empty (bool): 是否允许为空
    
    Returns:
        tuple: (is_valid, date_value, error_message)
    """
    if not date_str:
        if allow_empty:
            return True, None, ""
        else:
            return False, None, f"{field_name}不能为空"
    
    try:
        date_value = datetime.strptime(date_str, '%Y-%m-%d').date()
        return True, date_value, ""
    except ValueError:
        return False, None, f"{field_name}格式不正确，请使用YYYY-MM-DD格式"

def validate_lead_stage_transition(current_stage, new_stage):
    """
    验证线索阶段转换是否合法

    Args:
        current_stage (str): 当前阶段
        new_stage (str): 新阶段

    Returns:
        tuple: (is_valid, error_message)
    """
    # 标准线索阶段定义（按业务流程顺序）
    stages = ['获取联系方式', '线下见面', '首笔支付', '次笔支付', '全款支付']

    if new_stage not in stages:
        return False, "无效的线索阶段"

    if not current_stage:
        return True, ""  # 新建线索，任何阶段都可以

    current_index = stages.index(current_stage) if current_stage in stages else -1
    new_index = stages.index(new_stage)

    # 允许向前推进或保持当前阶段
    if new_index >= current_index:
        return True, ""
    else:
        return False, "线索阶段不能倒退"

def validate_tutoring_sessions(completed_sessions):
    """
    验证课时数
    
    Args:
        completed_sessions (int): 已完成课时数
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if completed_sessions < 0:
        return False, "已完成课时数不能为负数"
    
    if completed_sessions > 6:
        return False, "已完成课时数不能超过6节"
    
    return True, ""

def validate_competition_name(competition_name):
    """
    验证竞赛名称是否存在于配置中
    
    Args:
        competition_name (str): 竞赛名称
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not competition_name:
        return True, ""  # 允许为空
    
    competition = CompetitionConfig.query.filter_by(competition_name=competition_name).first()
    if not competition:
        return False, "竞赛名称不在配置列表中，请先在基础配置中添加"
    
    return True, ""

def validate_competition_delivery_status_transition(current_status, new_status):
    """
    验证竞赛交付状态转换是否合法
    
    Args:
        current_status (str): 当前状态
        new_status (str): 新状态
    
    Returns:
        tuple: (is_valid, error_message)
    """
    statuses = ['未报名', '已报名待竞赛', '竞赛进行中', '等待竞赛结果', '奖项已获取', '服务完结']
    
    if new_status not in statuses:
        return False, "无效的交付状态"
    
    if not current_status:
        return True, ""  # 新建记录，任何状态都可以
    
    current_index = statuses.index(current_status) if current_status in statuses else -1
    new_index = statuses.index(new_status)
    
    # 允许向前推进或保持当前状态
    if new_index >= current_index:
        return True, ""
    else:
        return False, "交付状态不能倒退"

def validate_business_rules(data_type, data, **kwargs):
    """
    综合业务规则验证
    
    Args:
        data_type (str): 数据类型 ('user', 'lead', 'customer', 'tutoring', 'competition')
        data (dict): 要验证的数据
        **kwargs: 额外参数
    
    Returns:
        tuple: (is_valid, errors_dict)
    """
    errors = {}
    
    if data_type == 'user':
        # 用户数据验证
        username = data.get('username', '')
        phone = data.get('phone', '')
        exclude_user_id = kwargs.get('exclude_user_id')
        
        is_valid, error = validate_username(username, exclude_user_id)
        if not is_valid:
            errors['username'] = error
        
        is_valid, error = validate_phone(phone)
        if not is_valid:
            errors['phone'] = error
        else:
            is_valid, error = validate_phone_unique(phone, exclude_user_id)
            if not is_valid:
                errors['phone'] = error
    
    elif data_type == 'customer':
        # 客户数据验证
        payment_amount = data.get('payment_amount', '')
        tutoring_expire_date = data.get('tutoring_expire_date', '')
        award_expire_date = data.get('award_expire_date', '')
        
        is_valid, _, error = validate_decimal(payment_amount, "支付金额", min_value=0)
        if not is_valid:
            errors['payment_amount'] = error
        
        if tutoring_expire_date:
            is_valid, _, error = validate_date(tutoring_expire_date, "课题到期日期")
            if not is_valid:
                errors['tutoring_expire_date'] = error
        
        if award_expire_date:
            is_valid, _, error = validate_date(award_expire_date, "获奖到期日期")
            if not is_valid:
                errors['award_expire_date'] = error
    
    elif data_type == 'tutoring':
        # 课题辅导验证
        completed_sessions = data.get('completed_sessions', 0)
        last_class_date = data.get('last_class_date', '')
        next_class_date = data.get('next_class_date', '')
        
        is_valid, error = validate_tutoring_sessions(completed_sessions)
        if not is_valid:
            errors['completed_sessions'] = error
        
        if last_class_date:
            is_valid, _, error = validate_date(last_class_date, "最近上课日期")
            if not is_valid:
                errors['last_class_date'] = error
        
        if next_class_date:
            is_valid, _, error = validate_date(next_class_date, "下次上课日期")
            if not is_valid:
                errors['next_class_date'] = error
    
    elif data_type == 'competition':
        # 竞赛交付验证
        competition_name = data.get('competition_name', '')
        registration_date = data.get('registration_date', '')
        competition_date = data.get('competition_date', '')
        current_status = kwargs.get('current_status')
        new_status = data.get('delivery_status', '')
        
        is_valid, error = validate_competition_name(competition_name)
        if not is_valid:
            errors['competition_name'] = error
        
        if registration_date:
            is_valid, _, error = validate_date(registration_date, "报名日期")
            if not is_valid:
                errors['registration_date'] = error
        
        if competition_date:
            is_valid, _, error = validate_date(competition_date, "竞赛日期")
            if not is_valid:
                errors['competition_date'] = error
        
        if new_status:
            is_valid, error = validate_competition_delivery_status_transition(current_status, new_status)
            if not is_valid:
                errors['delivery_status'] = error
    
    return len(errors) == 0, errors
