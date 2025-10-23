from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Numeric

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """用户账号表"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, comment='用户名')
    phone = db.Column(db.String(11), unique=True, nullable=False, comment='手机号')
    role = db.Column(db.String(20), nullable=False, comment='角色：admin/sales_manager/salesperson/teacher_supervisor/teacher')
    group_name = db.Column(db.String(50), comment='所属组别')
    status = db.Column(db.Boolean, default=True, comment='账号状态：True启用/False禁用')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    leads_as_sales = db.relationship('Lead', foreign_keys='Lead.sales_user_id', backref='sales_user', lazy='dynamic')
    customers_as_teacher_user = db.relationship('Customer', foreign_keys='Customer.teacher_user_id', backref='teacher_user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def is_admin(self):
        return self.role == 'admin'

    def is_sales_manager(self):
        """是否为销售管理角色"""
        return self.role == 'sales_manager'

    def is_salesperson(self):
        """是否为销售角色"""
        return self.role == 'salesperson'

    def is_sales(self):
        """是否为销售相关角色（包括销售管理和销售）"""
        return self.role in ['sales_manager', 'salesperson']

    def is_teacher_supervisor(self):
        """是否为班主任角色（管理客户交付和辅导老师）"""
        return self.role == 'teacher_supervisor'

    def is_teacher(self):
        """是否为辅导老师角色（实际授课，未来可能废弃此User角色）"""
        return self.role == 'teacher'

class Lead(db.Model):
    """学员线索表"""
    __tablename__ = 'leads'

    # 线索阶段常量定义
    STAGE_CONTACT = '获取联系方式'
    STAGE_MEETING = '线下见面'
    STAGE_FIRST_PAYMENT = '首笔支付'
    STAGE_SECOND_PAYMENT = '次笔支付'
    STAGE_FULL_PAYMENT = '全款支付'

    # 所有允许的阶段值
    ALLOWED_STAGES = [
        STAGE_CONTACT,
        STAGE_MEETING,
        STAGE_FIRST_PAYMENT,
        STAGE_SECOND_PAYMENT,
        STAGE_FULL_PAYMENT
    ]

    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(50), comment='学员姓名')  # 改为可选
    parent_wechat_display_name = db.Column(db.String(50), nullable=False, comment='家长微信名')  # 新增必填字段
    parent_wechat_name = db.Column(db.String(50), nullable=False, unique=True, comment='家长微信号')  # 新增必填字段
    contact_info = db.Column(db.String(100), comment='联系方式')  # 改为可选
    contact_locked = db.Column(db.Boolean, default=True, comment='联系方式是否锁定')
    lead_source = db.Column(db.String(50), comment='线索来源')
    grade = db.Column(db.String(10), comment='年级：1-9年级、高一、高二、高三')
    district = db.Column(db.String(20), comment='行政区')
    school = db.Column(db.String(100), comment='学校')
    sales_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='责任销售ID')
    stage = db.Column(db.String(50), nullable=False, comment='线索阶段')
    contract_amount = db.Column(Numeric(10, 2), comment='合同金额')

    # 各阶段时间
    contact_obtained_at = db.Column(db.DateTime, comment='获取联系方式时间')
    meeting_at = db.Column(db.DateTime, comment='线下见面时间')
    meeting_location = db.Column(db.String(20), comment='见面地点：浦东/浦西')
    first_payment_at = db.Column(db.DateTime, comment='首笔支付时间')
    second_payment_at = db.Column(db.DateTime, comment='次笔支付时间')

    # 服务内容
    service_types = db.Column(db.Text, comment='服务类型JSON：["tutoring", "competition", "upgrade_guidance"]')
    competition_award_level = db.Column(db.String(20), comment='竞赛奖项等级：市奖/国奖')
    additional_requirements = db.Column(db.Text, comment='额外要求')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    customer = db.relationship('Customer', backref='lead', uselist=False)
    payments = db.relationship('Payment', backref='lead', lazy='dynamic')

    def get_service_types_list(self):
        """获取服务类型列表"""
        import json
        if self.service_types:
            try:
                # 尝试解析 JSON 格式
                return json.loads(self.service_types)
            except:
                # 如果不是 JSON，尝试按逗号分隔
                if ',' in self.service_types or self.service_types:
                    return [s.strip() for s in self.service_types.split(',') if s.strip()]
                return []
        return []

    def set_service_types_list(self, service_list):
        """设置服务类型列表"""
        import json
        self.service_types = json.dumps(service_list) if service_list else None

    def has_service_type(self, service_type):
        """检查是否包含指定服务类型"""
        return service_type in self.get_service_types_list()

    def get_display_name(self):
        """获取显示名称（优先显示学员姓名，否则显示家长微信号）"""
        return self.student_name if self.student_name else self.parent_wechat_name

    def __repr__(self):
        return f'<Lead {self.get_display_name()}>'

class Customer(db.Model):
    """成交客户表"""
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, comment='关联线索ID')
    teacher_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='责任班主任ID（User表，role=teacher_supervisor）')
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), comment='辅导老师ID（Teacher表）')

    payment_amount = db.Column(Numeric(10, 2), nullable=False, comment='支付金额')

    # ⚠️ 以下字段保留用于向后兼容，但不再使用
    # 实际数据通过 @property 从线索表读取，保证单一数据源
    _competition_award_level = db.Column('competition_award_level', db.String(20), comment='[已废弃] 竞赛奖项等级：市奖/国奖')
    _additional_requirements = db.Column('additional_requirements', db.Text, comment='[已废弃] 额外要求')

    exam_year = db.Column(db.Integer, comment='中考或高考年份')
    customer_notes = db.Column(db.Text, comment='客户备注')
    converted_at = db.Column(db.DateTime, comment='线索转客户时间')
    is_priority = db.Column(db.Boolean, default=False, comment='是否重点关注客户')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    tutoring_delivery = db.relationship('TutoringDelivery', backref='customer', uselist=False)
    competition_delivery = db.relationship('CompetitionDelivery', backref='customer', uselist=False)

    # ✨ 通过 @property 从线索表读取合同内容（单一数据源）
    @property
    def competition_award_level(self):
        """从线索表读取竞赛奖项等级"""
        return self.lead.competition_award_level if self.lead else None

    @property
    def additional_requirements(self):
        """从线索表读取额外要求"""
        return self.lead.additional_requirements if self.lead else None

    # 辅助方法
    def get_sales_user(self):
        """获取责任销售"""
        return self.lead.sales_user if self.lead else None

    def get_service_types(self):
        """获取服务类型列表"""
        return self.lead.get_service_types_list() if self.lead else []

    def get_second_payment_date(self):
        """获取次笔付款时间"""
        if not self.lead:
            return None

        # 获取该线索的所有付款记录，按付款日期升序排列
        payments = Payment.query.filter_by(lead_id=self.lead_id).order_by(Payment.payment_date.asc()).all()

        # 如果有至少2笔付款，返回第二笔的付款日期
        if len(payments) >= 2:
            return payments[1].payment_date

        return None

    def get_expire_date(self):
        """获取服务到期时间"""
        if self.exam_year:
            from datetime import date
            return date(self.exam_year, 5, 31)
        return None

    def __repr__(self):
        return f'<Customer {self.lead.student_name if self.lead else self.id}>'

class TutoringDelivery(db.Model):
    """课题辅导服务交付表"""
    __tablename__ = 'tutoring_deliveries'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, comment='关联客户ID')

    total_sessions = db.Column(db.Integer, default=6, comment='总课时数')
    completed_sessions = db.Column(db.Integer, default=0, comment='已上节数')
    remaining_sessions = db.Column(db.Integer, default=6, comment='剩余节数')

    thesis_status = db.Column(db.String(20), default='未开始', comment='课题论文完成状态')
    thesis_completed_at = db.Column(db.DateTime, comment='课题完成时间')
    last_class_at = db.Column(db.DateTime, comment='最近上课时间')
    next_class_at = db.Column(db.DateTime, comment='下次上课时间')

    delivery_notes = db.Column(db.Text, comment='交付备注')
    notes_history = db.Column(db.JSON, comment='备注历史版本')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def update_remaining_sessions(self):
        """自动计算剩余节数"""
        self.remaining_sessions = self.total_sessions - self.completed_sessions

    def __repr__(self):
        return f'<TutoringDelivery {self.customer.lead.student_name}>'

class CompetitionDelivery(db.Model):
    """竞赛奖项获取交付表"""
    __tablename__ = 'competition_deliveries'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, comment='关联客户ID')
    competition_name_id = db.Column(db.Integer, db.ForeignKey('competition_names.id'), comment='竞赛名称ID')

    delivery_status = db.Column(db.String(30), default='未报名', comment='交付状态')
    award_obtained_at = db.Column(db.DateTime, comment='奖项获取时间')

    delivery_notes = db.Column(db.Text, comment='交付备注')
    notes_history = db.Column(db.JSON, comment='备注历史版本')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<CompetitionDelivery {self.customer.lead.student_name}>'

class CompetitionName(db.Model):
    """竞赛名称配置表"""
    __tablename__ = 'competition_names'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, comment='竞赛名称')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联关系
    competition_deliveries = db.relationship('CompetitionDelivery', backref='competition_name', lazy='dynamic')

    def __repr__(self):
        return f'<CompetitionName {self.name}>'

class Payment(db.Model):
    """付款记录表"""
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, comment='关联线索ID')
    amount = db.Column(Numeric(10, 2), nullable=False, comment='付款金额')
    payment_date = db.Column(db.Date, nullable=False, comment='付款日期')
    payment_notes = db.Column(db.Text, comment='付款备注')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Payment {self.lead.student_name} ¥{self.amount}>'

class Teacher(db.Model):
    """老师信息表"""
    __tablename__ = 'teachers'

    id = db.Column(db.Integer, primary_key=True)
    chinese_name = db.Column(db.String(50), nullable=False, comment='中文名')
    english_name = db.Column(db.String(100), comment='英文名')
    current_institution = db.Column(db.String(200), comment='现单位')
    major_direction = db.Column(db.String(200), comment='专业方向')
    highest_degree = db.Column(db.String(50), comment='最高学历')
    degree_description = db.Column(db.Text, comment='学历说明')
    research_achievements = db.Column(db.Text, comment='科研成果')
    innovation_coaching_achievements = db.Column(db.Text, comment='科创辅导成果')
    social_roles = db.Column(db.Text, comment='社会角色')
    status = db.Column(db.Boolean, default=True, comment='状态：True启用/False禁用')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    customers = db.relationship('Customer', foreign_keys='Customer.teacher_id', backref='teacher', lazy='dynamic')

    def __repr__(self):
        return f'<Teacher {self.chinese_name}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'chinese_name': self.chinese_name,
            'english_name': self.english_name,
            'current_institution': self.current_institution,
            'major_direction': self.major_direction,
            'highest_degree': self.highest_degree,
            'degree_description': self.degree_description,
            'research_achievements': self.research_achievements,
            'innovation_coaching_achievements': self.innovation_coaching_achievements,
            'social_roles': self.social_roles,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

class LoginLog(db.Model):
    """登录日志表"""
    __tablename__ = 'login_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, comment='用户ID')
    phone = db.Column(db.String(11), nullable=False, comment='登录手机号')
    login_time = db.Column(db.DateTime, default=datetime.utcnow, comment='登录时间')
    ip_address = db.Column(db.String(45), comment='IP地址')
    user_agent = db.Column(db.String(500), comment='用户代理')
    login_result = db.Column(db.String(20), default='success', comment='登录结果：success/failed')

    # 关联关系
    user = db.relationship('User', backref='login_logs')

    def __repr__(self):
        return f'<LoginLog {self.phone} at {self.login_time}>'


class CommunicationRecord(db.Model):
    """统一沟通记录表 - 记录线索和客户阶段的所有沟通"""
    __tablename__ = 'communication_records'

    id = db.Column(db.Integer, primary_key=True)

    # 始终保持线索关联，客户关联可选
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, comment='线索ID')
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True, comment='客户ID（转化后）')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, comment='填写人ID')

    # 核心字段
    content = db.Column(db.Text, nullable=False, comment='沟通内容')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, comment='创建时间')

    # 关联关系
    lead = db.relationship('Lead', backref='communication_records')
    customer = db.relationship('Customer', backref='communication_records')
    user = db.relationship('User', backref='communication_records')

    def __repr__(self):
        stage = 'customer' if self.customer_id else 'lead'
        return f'<CommunicationRecord {stage} at {self.created_at}>'

class TeacherImage(db.Model):
    """老师相关图片表"""
    __tablename__ = 'teacher_images'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False, comment='老师ID')
    image_path = db.Column(db.String(500), nullable=False, comment='图片路径')
    description = db.Column(db.String(200), comment='图片描述')
    file_size = db.Column(db.Integer, comment='文件大小(字节)')
    file_name = db.Column(db.String(200), comment='原始文件名')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='上传时间')

    # 关联关系
    teacher = db.relationship('Teacher', backref=db.backref('images', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<TeacherImage {self.teacher_id} - {self.file_name}>'

    def get_file_size_display(self):
        """返回格式化的文件大小"""
        if not self.file_size:
            return '-'
        size_kb = self.file_size / 1024
        if size_kb < 1024:
            return f'{size_kb:.1f} KB'
        else:
            size_mb = size_kb / 1024
            return f'{size_mb:.1f} MB'

# ConsultationDetail表已删除，现在统一使用CommunicationRecord表
