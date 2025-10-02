"""
中高考年份计算工具
"""
from datetime import datetime


def calculate_exam_year(grade, reference_date=None):
    """
    根据年级和参考日期计算中考或高考年份
    
    Args:
        grade: 年级字符串，如 "1年级", "9年级", "高一", "高二", "高三"
        reference_date: 参考日期，默认为当前日期
    
    Returns:
        int: 考试年份，如果年级格式不正确则返回 None
    
    计算规则：
    - 学期划分：
      * 上学期：9月-次年2月（包括寒假）
      * 下学期：3月-8月（包括暑假）
    - 年级对应：
      * 1-9年级 → 中考
      * 高一、高二、高三 → 高考
    
    示例：
        当前是2025年9月（新学年开始）
        - 9年级 → 2026年中考（明年）
        - 高三 → 2026年高考（明年）
        
        当前是2025年5月（学年末）
        - 9年级 → 2025年中考（本年度）
        - 高三 → 2025年高考（本年度）
    """
    if not grade:
        return None
    
    if reference_date is None:
        reference_date = datetime.now()
    
    current_year = reference_date.year
    current_month = reference_date.month
    
    # 判断当前是上学期还是下学期
    # 上学期：9月-次年2月（新学年开始到寒假结束）
    # 下学期：3月-8月（春季学期到暑假结束）
    if current_month >= 9:
        # 9月-12月，属于新学年的上学期
        # 例如：2025年9月是2025-2026学年，学年结束是2026年
        academic_year = current_year + 1
    elif current_month <= 2:
        # 1月-2月，属于上学期（寒假）
        # 例如：2026年1月是2025-2026学年，学年结束是2026年
        academic_year = current_year
    else:
        # 3月-8月，属于下学期
        # 例如：2025年5月是2024-2025学年，学年结束是2025年
        academic_year = current_year
    
    # 年级到毕业年份的映射（距离中考/高考的年数）
    grade_to_years = {
        '1年级': 8,
        '2年级': 7,
        '3年级': 6,
        '4年级': 5,
        '5年级': 4,
        '6年级': 3,
        '7年级': 2,
        '8年级': 1,
        '9年级': 0,
        '高一': 2,
        '高二': 1,
        '高三': 0,
    }
    
    # 获取距离考试的年数
    years_to_exam = grade_to_years.get(grade)
    
    if years_to_exam is None:
        # 年级格式不正确
        return None
    
    # 计算考试年份
    exam_year = academic_year + years_to_exam
    
    return exam_year


def get_exam_type(grade):
    """
    根据年级判断是中考还是高考
    
    Args:
        grade: 年级字符串
    
    Returns:
        str: "中考" 或 "高考"，如果无法判断则返回 None
    """
    if not grade:
        return None
    
    if grade in ['1年级', '2年级', '3年级', '4年级', '5年级', '6年级', '7年级', '8年级', '9年级']:
        return '中考'
    elif grade in ['高一', '高二', '高三']:
        return '高考'
    else:
        return None

