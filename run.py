#!/usr/bin/env python3
"""
EduConnect CRM 启动脚本
支持不同环境的配置和启动
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

def create_app(config_name=None):
    """应用工厂函数"""

    # 确定配置环境
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    # 创建Flask应用
    app = Flask(__name__)

    # 加载配置 - 使用统一的config.py
    from config import config
    config_class = config.get(config_name, config['default'])
    app.config.from_object(config_class)
    config_class.init_app(app)
    
    # 初始化扩展
    from models import db
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录以访问此页面。'
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # 注册蓝图
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.leads import leads_bp
    from routes.customers import customers_bp
    from routes.delivery import delivery_bp
    from routes.config import config_bp
    from routes.query import query_bp
    from routes.consultations import consultations_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(leads_bp, url_prefix='/leads')
    app.register_blueprint(customers_bp, url_prefix='/customers')
    app.register_blueprint(delivery_bp, url_prefix='/delivery')
    app.register_blueprint(config_bp, url_prefix='/config')
    app.register_blueprint(query_bp, url_prefix='/query')
    app.register_blueprint(consultations_bp, url_prefix='/consultations')

    # 添加全局模板函数
    @app.context_processor
    def inject_logo():
        """注入logo路径到所有模板"""
        import os

        def get_logo_url():
            """获取当前logo的URL"""
            allowed_extensions = ['png', 'jpg', 'jpeg', 'gif']
            logo_filename = 'custom-logo'

            for ext in allowed_extensions:
                logo_path = f"static/images/{logo_filename}.{ext}"
                if os.path.exists(logo_path):
                    return f"images/{logo_filename}.{ext}"
            return None

        return dict(get_logo_url=get_logo_url)

    # 健康检查端点
    @app.route('/health')
    def health_check():
        """健康检查端点"""
        from flask import jsonify
        try:
            # 检查数据库连接
            from models import db
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            db_status = 'connected'
        except Exception as e:
            # 数据库连接失败，但应用仍可运行
            db_status = f'error: {str(e)}'

        return jsonify({
            'status': 'healthy',
            'service': 'EduConnect CRM',
            'version': '1.0.0',
            'database': db_status
        }), 200

    # 主页路由
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

    # 测试数据创建路由
    @app.route('/create-test-data')
    def create_test_data():
        """创建测试数据"""
        from models import db, Lead, Customer, User
        from datetime import datetime, timedelta
        from flask import jsonify

        try:
            # 获取销售用户
            sales_user = User.query.filter_by(role='sales').first()
            if not sales_user:
                return jsonify({'error': '没有找到销售用户'}), 400

            # 创建测试线索1 - 有见面时间
            lead1 = Lead(
                student_name="张小明",
                parent_wechat_display_name="张妈妈",
                parent_wechat_name="zhangmama123",
                contact_info="13800138001",
                lead_source="朋友推荐",
                grade="初三",
                sales_user_id=sales_user.id,
                stage="已约见",
                contact_obtained_at=datetime.now() - timedelta(days=3),
                meeting_at=(datetime.now() + timedelta(days=1)).replace(hour=14, minute=30, second=0, microsecond=0),  # 明天下午2点30分
                meeting_location="浦东",
                follow_up_notes="学生数学基础较好，希望提升竞赛水平"
            )

            # 创建测试线索2 - 有见面时间
            lead2 = Lead(
                student_name="李小红",
                parent_wechat_display_name="李爸爸",
                parent_wechat_name="libaba456",
                contact_info="13800138002",
                lead_source="网络推广",
                grade="高二",
                sales_user_id=sales_user.id,
                stage="已约见",
                contact_obtained_at=datetime.now() - timedelta(days=5),
                meeting_at=(datetime.now() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0),  # 后天上午10点整
                meeting_location="浦西",
                follow_up_notes="家长对竞赛辅导很感兴趣"
            )

            # 添加到数据库
            db.session.add_all([lead1, lead2])
            db.session.commit()

            # 为有见面时间的线索创建客户记录和咨询记录
            for lead in [lead1, lead2]:
                # 创建客户记录
                customer = Customer(
                    lead_id=lead.id,
                    sales_user_id=sales_user.id,
                    service_type='tutoring',
                    payment_amount=5000.00,
                    customer_notes=f"客户{lead.student_name}的记录",
                    converted_at=datetime.now()
                )
                db.session.add(customer)
                db.session.flush()  # 获取customer.id

                # 创建沟通记录（使用新的统一表）
                from communication_utils import CommunicationManager
                if lead.follow_up_notes:
                    CommunicationManager.add_customer_communication(
                        lead_id=lead.id,
                        customer_id=customer.id,
                        content=lead.follow_up_notes,
                        created_at=lead.contact_obtained_at or datetime.now()
                    )

            db.session.commit()

            return jsonify({
                'success': True,
                'message': '测试数据创建成功',
                'data': {
                    'leads_created': 2,
                    'customers_created': 2,
                    'consultations_created': 2
                }
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'创建测试数据失败: {str(e)}'}), 500

    @app.route('/fix-meeting-times')
    def fix_meeting_times():
        """修复约见时间，确保分钟都是00或30，并添加约见地点"""
        from models import db, Lead
        from datetime import datetime
        from flask import jsonify
        import random

        try:
            # 获取所有有约见时间的线索
            leads_with_meetings = Lead.query.filter(Lead.meeting_at.isnot(None)).all()

            updated_count = 0
            for lead in leads_with_meetings:
                # 修复分钟数
                original_time = lead.meeting_at
                if original_time.minute not in [0, 30]:
                    # 将分钟调整为最接近的00或30
                    if original_time.minute < 15:
                        new_minute = 0
                    elif original_time.minute < 45:
                        new_minute = 30
                    else:
                        new_minute = 0
                        original_time = original_time.replace(hour=original_time.hour + 1)

                    lead.meeting_at = original_time.replace(minute=new_minute, second=0, microsecond=0)
                    updated_count += 1

                # 添加约见地点（如果没有的话）
                if not lead.meeting_location:
                    # 随机选择浦东或浦西，但浦西概率更高（默认）
                    lead.meeting_location = random.choice(['浦西', '浦西', '浦东'])  # 浦西概率2/3
                    updated_count += 1

            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'约见时间修复完成，共更新了 {updated_count} 条记录',
                'data': {
                    'total_leads_with_meetings': len(leads_with_meetings),
                    'updated_count': updated_count
                }
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'修复约见时间失败: {str(e)}'}), 500

    @app.route('/debug-meeting-times')
    def debug_meeting_times():
        """调试约见时间数据"""
        from models import Lead
        from flask import jsonify

        try:
            # 获取所有有约见时间的线索
            leads_with_meetings = Lead.query.filter(Lead.meeting_at.isnot(None)).all()

            debug_data = []
            for lead in leads_with_meetings:
                debug_data.append({
                    'id': lead.id,
                    'student_name': lead.student_name,
                    'meeting_at': lead.meeting_at.isoformat() if lead.meeting_at else None,
                    'meeting_at_formatted': lead.meeting_at.strftime('%Y-%m-%d %H:%M') if lead.meeting_at else None,
                    'hour': lead.meeting_at.strftime('%H') if lead.meeting_at else None,
                    'minute': lead.meeting_at.strftime('%M') if lead.meeting_at else None,
                    'meeting_location': lead.meeting_location
                })

            return jsonify({
                'success': True,
                'data': debug_data
            })

        except Exception as e:
            return jsonify({'error': f'调试失败: {str(e)}'}), 500

    @app.route('/fix-wrong-meeting-hours')
    def fix_wrong_meeting_hours():
        """修复错误的约见时间小时数"""
        from models import db, Lead
        from datetime import datetime, timedelta
        from flask import jsonify
        import random

        try:
            # 获取所有有约见时间的线索
            leads_with_meetings = Lead.query.filter(Lead.meeting_at.isnot(None)).all()

            updated_count = 0
            for lead in leads_with_meetings:
                original_time = lead.meeting_at

                # 如果小时数不在合理范围内（8-21），则修复
                if original_time.hour < 8 or original_time.hour > 21:
                    # 随机选择一个合理的小时数
                    new_hour = random.choice([9, 10, 11, 14, 15, 16, 17, 18, 19, 20])

                    # 确保分钟数是00或30
                    new_minute = 30 if original_time.minute >= 15 else 0

                    # 更新时间，保持原有的日期
                    lead.meeting_at = original_time.replace(
                        hour=new_hour,
                        minute=new_minute,
                        second=0,
                        microsecond=0
                    )
                    updated_count += 1
                    print(f"修复线索 {lead.id} ({lead.student_name}): {original_time} -> {lead.meeting_at}")

            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'约见时间小时数修复完成，共更新了 {updated_count} 条记录',
                'data': {
                    'total_leads_with_meetings': len(leads_with_meetings),
                    'updated_count': updated_count
                }
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'修复约见时间小时数失败: {str(e)}'}), 500
    
    # 错误处理
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        from flask import render_template
        return render_template('errors/403.html'), 403

    @app.route('/test-ajax')
    def test_ajax():
        """测试AJAX功能的页面"""
        try:
            with open('test_ajax_feedback.html', 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return '测试页面文件不存在', 404

    @app.route('/migrate-communication-records')
    def migrate_communication_records():
        """迁移数据到统一沟通记录表"""
        try:
            from models import CommunicationRecord, Lead, Customer
            from communication_utils import CommunicationManager

            # 创建新表
            db.create_all()

            migrated_lead_notes = 0
            migrated_consultation_records = 0

            # 1. 迁移线索备注
            leads_with_notes = Lead.query.filter(Lead.follow_up_notes.isnot(None)).all()

            for lead in leads_with_notes:
                if lead.follow_up_notes and lead.follow_up_notes.strip():
                    # 检查是否已经迁移过
                    existing = CommunicationRecord.query.filter_by(
                        lead_id=lead.id,
                        content=lead.follow_up_notes.strip()
                    ).first()

                    if not existing:
                        record = CommunicationRecord(
                            lead_id=lead.id,
                            customer_id=None,
                            content=lead.follow_up_notes.strip(),
                            created_at=lead.created_at
                        )
                        db.session.add(record)
                        migrated_lead_notes += 1

            # 2. consultation_details表已删除，无需迁移

            # 提交所有更改
            db.session.commit()

            # 验证迁移结果
            total_records = CommunicationRecord.query.count()

            return f"""
            <h2>数据迁移完成！</h2>
            <ul>
                <li>迁移线索备注: {migrated_lead_notes} 条</li>
                <li>迁移咨询记录: {migrated_consultation_records} 条</li>
                <li>总计: {migrated_lead_notes + migrated_consultation_records} 条记录</li>
                <li>当前沟通记录总数: {total_records} 条</li>
            </ul>
            <p><a href="/consultations/list">查看咨询管理</a></p>
            """

        except Exception as e:
            db.session.rollback()
            return f'迁移失败: {str(e)}', 500

    return app

def init_database(app):
    """初始化数据库"""
    with app.app_context():
        from models import db, User

        # 创建所有表
        db.create_all()

        # 强制执行数据库迁移
        try:
            from sqlalchemy import text

            # 添加meeting_location字段
            try:
                db.session.execute(text("ALTER TABLE leads ADD COLUMN meeting_location VARCHAR(20)"))
                db.session.commit()
                print("✅ meeting_location字段添加成功")
            except Exception as e:
                if "duplicate column name" in str(e):
                    print("✅ meeting_location字段已存在")
                else:
                    print(f"⚠️ meeting_location字段添加失败: {e}")

            # 创建consultation_details表
            try:
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
                db.session.execute(text("CREATE INDEX idx_consultation_details_customer_id ON consultation_details (customer_id)"))
                db.session.execute(text("CREATE INDEX idx_consultation_details_consultation_time ON consultation_details (consultation_time)"))

                db.session.commit()
                print("✅ consultation_details表创建成功")
            except Exception as e:
                if "already exists" in str(e):
                    print("✅ consultation_details表已存在")
                else:
                    print(f"⚠️ consultation_details表创建失败: {e}")

        except Exception as e:
            print(f"❌ 数据库迁移失败: {e}")
            db.session.rollback()

        # 创建测试账号列表
        test_users = [
            {
                'username': 'admin',
                'phone': '13800138000',
                'role': 'admin',
                'description': '系统管理员'
            },
            {
                'username': '张三',
                'phone': '13900139001',
                'role': 'sales_manager',
                'description': '销售经理'
            },
            {
                'username': '李四',
                'phone': '13900139002',
                'role': 'salesperson',
                'description': '销售专员'
            },
            {
                'username': '王五',
                'phone': '13900139003',
                'role': 'teacher',
                'description': '数学班主任'
            },
            {
                'username': '赵六',
                'phone': '13900139004',
                'role': 'teacher',
                'description': '英语班主任'
            },
            {
                'username': '钱七',
                'phone': '13900139005',
                'role': 'sales_manager',
                'description': '高级销售经理'
            },
            {
                'username': '小王',
                'phone': '13900139006',
                'role': 'salesperson',
                'description': '销售代表'
            }
        ]

        print("正在初始化测试账号...")

        for user_data in test_users:
            # 检查用户是否已存在
            existing_user = User.query.filter_by(phone=user_data['phone']).first()
            if not existing_user:
                user = User(
                    username=user_data['username'],
                    phone=user_data['phone'],
                    role=user_data['role'],
                    status=True
                )
                db.session.add(user)
                print(f"创建用户: {user_data['username']} ({user_data['description']}) - {user_data['phone']}")

        db.session.commit()
        print("测试账号初始化完成!")

def main():
    """主函数"""
    # 获取命令行参数
    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        command = 'run'
    
    # 获取环境配置
    config_name = os.environ.get('FLASK_ENV', 'development')
    
    # 创建应用
    app = create_app(config_name)
    
    if command == 'init-db':
        # 初始化数据库
        print(f"正在初始化数据库 (环境: {config_name})...")
        init_database(app)
        print("数据库初始化完成!")
        
    elif command == 'run':
        # 运行应用
        print(f"正在启动 EduConnect CRM (环境: {config_name})...")
        
        # 自动初始化数据库（仅创建表和基本用户）
        init_database(app)
        
        # 启动应用
        if config_name == 'production':
            # 生产环境使用gunicorn启动
            print("生产环境请使用: gunicorn -w 4 -b 0.0.0.0:8000 run:app")
        else:
            # 开发环境直接启动
            app.run(
                host='0.0.0.0',
                port=int(os.environ.get('PORT', 5000)),
                debug=(config_name == 'development')
            )
    
    elif command == 'test':
        # 运行测试
        print("运行测试...")
        import unittest
        tests = unittest.TestLoader().discover('tests')
        unittest.TextTestRunner(verbosity=2).run(tests)
    
    else:
        print("可用命令:")
        print("  run      - 运行应用 (默认)")
        print("  init-db  - 初始化数据库")
        print("  test     - 运行测试")
        print("")
        print("环境变量:")
        print("  FLASK_ENV - 设置环境 (development/production/testing)")
        print("  PORT      - 设置端口 (默认: 5000)")

# 创建应用实例供Gunicorn使用
print("正在创建Flask应用实例...")
app = create_app()
print(f"Flask应用创建成功: {app}")
print(f"应用名称: {app.name}")
print(f"应用配置: {app.config.get('ENV', 'unknown')}")

if __name__ == '__main__':
    main()
