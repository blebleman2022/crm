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
    role = db.Column(db.String(20), nullable=False, comment='角色：admin/sales/teacher')
    group_name = db.Column(db.String(50), comment='所属组别')
    status = db.Column(db.Boolean, default=True, comment='账号状态：True启用/False禁用')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    leads_as_sales = db.relationship('Lead', foreign_keys='Lead.sales_user_id', backref='sales_user', lazy='dynamic')
    customers_as_sales = db.relationship('Customer', foreign_keys='Customer.sales_user_id', backref='sales_user', lazy='dynamic')
    customers_as_teacher = db.relationship('Customer', foreign_keys='Customer.teacher_user_id', backref='teacher_user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_sales(self):
        return self.role == 'sales'
    
    def is_teacher(self):
        return self.role == 'teacher'

class Lead(db.Model):
    """学员线索表"""
    __tablename__ = 'leads'

    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(50), comment='学员姓名')  # 改为可选
    parent_wechat_display_name = db.Column(db.String(50), nullable=False, comment='家长微信名')  # 新增必填字段
    parent_wechat_name = db.Column(db.String(50), nullable=False, unique=True, comment='家长微信号')  # 新增必填字段
    contact_info = db.Column(db.String(100), comment='联系方式')  # 改为可选
    contact_locked = db.Column(db.Boolean, default=True, comment='联系方式是否锁定')
    lead_source = db.Column(db.String(50), comment='线索来源')
    grade = db.Column(db.String(10), comment='年级：1-9年级、高一、高二、高三')
    sales_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='责任销售ID')
    stage = db.Column(db.String(50), nullable=False, comment='线索阶段')
    contract_amount = db.Column(Numeric(10, 2), comment='合同金额')

    # 各阶段时间
    contact_obtained_at = db.Column(db.DateTime, comment='获取联系方式时间')
    meeting_at = db.Column(db.DateTime, comment='线下见面时间')
    meeting_location = db.Column(db.String(20), comment='见面地点：浦东/浦西')
    first_payment_at = db.Column(db.DateTime, comment='首笔支付时间')
    second_payment_at = db.Column(db.DateTime, comment='次笔支付时间')

    # 保留旧字段以兼容现有代码
    deposit_paid_at = db.Column(db.DateTime, comment='定金支付时间')
    full_payment_at = db.Column(db.DateTime, comment='第二笔款项支付时间')

    # 服务内容（新的多选格式）
    service_types = db.Column(db.Text, comment='服务类型JSON：["tutoring", "competition", "upgrade_guidance"]')
    competition_award_level = db.Column(db.String(20), comment='竞赛奖项等级：市奖/国奖')
    additional_requirements = db.Column(db.Text, comment='额外要求')

    # 保留旧字段以兼容现有代码
    service_type = db.Column(db.String(30), comment='服务类型：tutoring/competition/tutoring_competition')
    award_requirement = db.Column(db.String(20), comment='竞赛奖项要求：市奖/国奖')

    follow_up_notes = db.Column(db.Text, comment='跟进备注')
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
                return json.loads(self.service_types)
            except:
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
    sales_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='责任销售ID')
    teacher_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='责任班主任ID')
    
    service_type = db.Column(db.String(30), nullable=False, default='tutoring', comment='服务类型：tutoring/competition/tutoring_competition')
    payment_amount = db.Column(Numeric(10, 2), nullable=False, comment='支付金额')
    award_requirement = db.Column(db.String(20), comment='竞赛奖项要求：市奖/国奖')
    exam_year = db.Column(db.Integer, comment='中考或高考年份')
    tutoring_expire_date = db.Column(db.Date, comment='课题服务到期时间')
    award_expire_date = db.Column(db.Date, comment='获奖服务到期时间')
    customer_notes = db.Column(db.Text, comment='客户备注')
    converted_at = db.Column(db.DateTime, comment='线索转客户时间')
    is_priority = db.Column(db.Boolean, default=False, comment='是否重点关注客户')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    tutoring_delivery = db.relationship('TutoringDelivery', backref='customer', uselist=False)
    competition_delivery = db.relationship('CompetitionDelivery', backref='customer', uselist=False)
    
    def __repr__(self):
        return f'<Customer {self.lead.student_name}>'

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

    # 核心字段
    content = db.Column(db.Text, nullable=False, comment='沟通内容')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, comment='创建时间')

    # 关联关系
    lead = db.relationship('Lead', backref='communication_records')
    customer = db.relationship('Customer', backref='communication_records')

    def __repr__(self):
        stage = 'customer' if self.customer_id else 'lead'
        return f'<CommunicationRecord {stage} at {self.created_at}>'

# ConsultationDetail表已删除，现在统一使用CommunicationRecord表
