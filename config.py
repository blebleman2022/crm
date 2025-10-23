import os
from datetime import timedelta

# 获取项目根目录的绝对路径
basedir = os.path.abspath(os.path.dirname(__file__))

class BaseConfig:
    """基础配置类"""

    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'edu-crm-secret-key-2024'

    # 数据库配置 - 使用绝对路径
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'edu_crm.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # 安全配置
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    # 分页配置
    ITEMS_PER_PAGE = 20

    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'

    # 文件上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    # 应用信息
    APP_NAME = 'EduConnect CRM'
    APP_VERSION = '1.0.0'

    # 邮件配置
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    # Redis配置
    REDIS_URL = os.environ.get('REDIS_URL')

    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 启用 SQLite 外键约束
        from sqlalchemy import event
        from sqlalchemy.engine import Engine

        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

class DevelopmentConfig(BaseConfig):
    """开发环境配置"""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False

    @staticmethod
    def init_app(app):
        """初始化开发环境配置"""
        BaseConfig.init_app(app)

class ProductionConfig(BaseConfig):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

    # 生产环境数据库优化
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # 日志文件
    LOG_FILE = 'logs/crm.log'

    @staticmethod
    def init_app(app):
        """初始化生产环境配置"""
        BaseConfig.init_app(app)

        # 创建日志目录
        log_dir = os.path.dirname(ProductionConfig.LOG_FILE)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 配置日志
        import logging
        from logging.handlers import RotatingFileHandler

        if not app.debug:
            file_handler = RotatingFileHandler(
                ProductionConfig.LOG_FILE,
                maxBytes=10240000,
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)

            app.logger.setLevel(logging.INFO)
            app.logger.info('EduConnect CRM startup')

class TestingConfig(BaseConfig):
    """测试环境配置"""
    DEBUG = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False

    @staticmethod
    def init_app(app):
        """初始化测试环境配置"""
        BaseConfig.init_app(app)

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# 向后兼容
Config = DevelopmentConfig
