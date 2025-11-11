"""
数据脱敏工具
用于展示账号的敏感信息脱敏处理
"""

def mask_name(name):
    """
    脱敏姓名：保留姓，名用**表示
    
    Args:
        name: 姓名字符串
        
    Returns:
        脱敏后的姓名
        
    Examples:
        张三 -> 张**
        李四 -> 李**
        王小明 -> 王**
    """
    if not name or len(name) == 0:
        return name
    
    if len(name) == 1:
        return name
    
    # 保留第一个字（姓），其余用**表示
    return name[0] + '**'


def mask_wechat_name(wechat_name):
    """
    脱敏微信名：全部用**表示
    
    Args:
        wechat_name: 微信名字符串
        
    Returns:
        脱敏后的微信名（**）
    """
    if not wechat_name:
        return wechat_name
    
    return '**'


def mask_english_name(english_name):
    """
    脱敏英文名：全部用**表示
    
    Args:
        english_name: 英文名字符串
        
    Returns:
        脱敏后的英文名（**）
    """
    if not english_name:
        return english_name
    
    return '**'


def mask_number(number):
    """
    脱敏数字：用**表示
    
    Args:
        number: 数字
        
    Returns:
        脱敏后的数字（**）
    """
    if number is None:
        return number
    
    return '**'


def mask_teacher_name(teacher_name):
    """
    脱敏班主任姓名：全部用**表示
    
    Args:
        teacher_name: 班主任姓名
        
    Returns:
        脱敏后的班主任姓名（**）
    """
    if not teacher_name:
        return teacher_name
    
    return '**'


def should_mask_data(user):
    """
    判断是否需要对数据进行脱敏
    
    Args:
        user: 当前用户对象
        
    Returns:
        bool: 是否需要脱敏
    """
    if not user or not user.is_authenticated:
        return False
    
    # 只有demo角色需要脱敏
    return user.role == 'demo'

