#!/usr/bin/env python3
"""
本地开发环境启动脚本
"""
import os
import sys

# 设置环境变量
os.environ['FLASK_ENV'] = 'development'
os.environ['DATABASE_URL'] = 'sqlite:///instance/edu_crm.db'

print("🚀 启动本地CRM服务...")
print(f"当前目录: {os.getcwd()}")
print(f"数据库路径: {os.environ.get('DATABASE_URL')}")

# 检查数据库文件
db_path = 'instance/edu_crm.db'
if os.path.exists(db_path):
    print(f"✅ 数据库文件存在: {os.path.getsize(db_path)} bytes")
else:
    print(f"❌ 数据库文件不存在: {db_path}")
    sys.exit(1)

try:
    # 导入应用
    from run import create_app
    
    app = create_app('development')
    print("✅ Flask应用创建成功")
    print(f"数据库URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    
    # 测试数据库连接
    with app.app_context():
        from models import db, User
        
        # 简单测试查询
        user_count = User.query.count()
        print(f"✅ 数据库连接成功，用户数量: {user_count}")
    
    # 启动服务器
    print("\n🌐 启动Web服务器...")
    print("访问地址: http://127.0.0.1:5000")
    print("按 Ctrl+C 停止服务\n")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=True
    )
    
except Exception as e:
    print(f"\n❌ 启动失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

