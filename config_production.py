import os
from datetime import timedelta

class ProductionConfig:
    """生产环境配置"""
    
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-production-secret-key-change-this'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///instance/edu_crm.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_COOKIE_SECURE = True  # 生产环境使用HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # 安全配置
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/crm.log'
    
    # 应用配置
    DEBUG = False
    TESTING = False
    
    # 邮件配置（如果需要）
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # Redis配置（如果使用Redis作为会话存储）
    REDIS_URL = os.environ.get('REDIS_URL')
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 创建日志目录
        import os
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

class DevelopmentConfig:
    """开发环境配置"""
    
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///crm_dev.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_COOKIE_SECURE = False  # 开发环境可以使用HTTP
    SESSION_COOKIE_HTTPONLY = True
    
    # 安全配置
    WTF_CSRF_ENABLED = True
    
    # 应用配置
    DEBUG = True
    TESTING = False
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        pass

class TestingConfig:
    """测试环境配置"""
    
    # 基础配置
    SECRET_KEY = 'test-secret-key'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    
    # 安全配置
    WTF_CSRF_ENABLED = False  # 测试时禁用CSRF
    
    # 应用配置
    DEBUG = False
    TESTING = True
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        pass

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
