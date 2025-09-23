from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
import os

# 创建Flask应用实例
app = Flask(__name__)
app.config.from_object(Config)

# 初始化扩展
from models import db
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录以访问此页面。'

# 导入模型
from models import User, Lead, Customer, TutoringDelivery, CompetitionDelivery, CompetitionName, Payment, LoginLog, CommunicationRecord

# 导入蓝图
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.leads import leads_bp
from routes.customers import customers_bp
from routes.delivery import delivery_bp
from routes.config import config_bp
from routes.query import query_bp
from routes.consultations import consultations_bp

# 注册蓝图
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(leads_bp, url_prefix='/leads')
app.register_blueprint(customers_bp, url_prefix='/customers')
app.register_blueprint(delivery_bp, url_prefix='/delivery')
app.register_blueprint(config_bp, url_prefix='/config')
app.register_blueprint(query_bp, url_prefix='/query')
app.register_blueprint(consultations_bp, url_prefix='/consultations')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 添加模板函数
@app.template_global()
def is_basic_info_locked(lead):
    """判断基本信息是否应该被锁定"""
    # 检查是否有非空的基本信息
    has_student_name = lead.student_name and lead.student_name.strip()
    has_lead_source = lead.lead_source and lead.lead_source.strip()
    has_sales_user = lead.sales_user_id

    return bool(has_student_name or has_lead_source or has_sales_user)

@app.route('/')
def index():
    """根据用户角色重定向到对应页面"""
    from flask_login import current_user
    from flask import redirect, url_for
    
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    if current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif current_user.role == 'sales':
        return redirect(url_for('leads.dashboard'))
    elif current_user.role == 'teacher':
        return redirect(url_for('delivery.dashboard'))
    
    return redirect(url_for('auth.login'))

def auto_migrate():
    """自动执行数据库迁移"""
    with app.app_context():
        try:
            from sqlalchemy import text

            # 检查meeting_location字段是否存在
            result = db.session.execute(text("PRAGMA table_info(leads)"))
            columns = [row[1] for row in result.fetchall()]

            if 'meeting_location' not in columns:
                print("📝 添加meeting_location字段...")
                db.session.execute(text("""
                    ALTER TABLE leads
                    ADD COLUMN meeting_location VARCHAR(20)
                """))
                db.session.commit()
                print("✅ meeting_location字段添加成功")

            # 检查consultation_details表是否存在
            result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='consultation_details'"))
            if not result.fetchone():
                print("📝 创建consultation_details表...")
                db.session.execute(text("""
                    CREATE TABLE consultation_details (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_id INTEGER NOT NULL,
                        consultation_content TEXT,
                        consultation_time DATETIME,
                        consultation_type VARCHAR(50) DEFAULT 'initial',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (customer_id) REFERENCES customers (id)
                    )
                """))

                # 创建索引
                db.session.execute(text("""
                    CREATE INDEX idx_consultation_details_customer_id ON consultation_details (customer_id)
                """))

                db.session.execute(text("""
                    CREATE INDEX idx_consultation_details_consultation_time ON consultation_details (consultation_time)
                """))

                db.session.commit()
                print("✅ consultation_details表创建成功")

        except Exception as e:
            print(f"❌ 自动迁移失败: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        auto_migrate()
    app.run(debug=True, port=5001)
