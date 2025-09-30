#!/usr/bin/env python3
"""测试Flask应用数据库连接"""
import os

# 设置环境
os.environ['FLASK_ENV'] = 'development'

print("=== 测试Flask应用数据库连接 ===\n")

# 测试1: 直接创建Flask应用
print("测试1: 创建Flask应用")
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/edu_crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print(f"数据库URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

db = SQLAlchemy(app)

# 定义一个简单的模型
class TestUser(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))

# 测试查询
with app.app_context():
    try:
        count = TestUser.query.count()
        print(f"✅ 成功！用户数量: {count}\n")
    except Exception as e:
        print(f"❌ 失败: {e}\n")

# 测试2: 使用run.py的create_app
print("测试2: 使用run.py的create_app")
try:
    from run import create_app
    
    app2 = create_app('development')
    print(f"数据库URI: {app2.config.get('SQLALCHEMY_DATABASE_URI')}")
    
    with app2.app_context():
        from models import User
        count = User.query.count()
        print(f"✅ 成功！用户数量: {count}")
        
except Exception as e:
    print(f"❌ 失败: {e}")
    import traceback
    traceback.print_exc()

