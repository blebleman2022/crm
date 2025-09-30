#!/usr/bin/env python3
"""测试数据库连接"""
import os
import sqlite3
from sqlalchemy import create_engine, text

# 获取绝对路径
current_dir = os.getcwd()
db_file = os.path.join(current_dir, 'instance', 'edu_crm.db')

print(f"当前目录: {current_dir}")
print(f"数据库文件: {db_file}")
print(f"文件存在: {os.path.exists(db_file)}")
print(f"文件大小: {os.path.getsize(db_file)} bytes")
print()

# 测试1: SQLite原生连接
print("=== 测试1: SQLite原生连接 ===")
try:
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    print(f"✅ 成功！用户数量: {count}")
    conn.close()
except Exception as e:
    print(f"❌ 失败: {e}")

print()

# 测试2: SQLAlchemy相对路径
print("=== 测试2: SQLAlchemy相对路径 ===")
uri = 'sqlite:///instance/edu_crm.db'
print(f"URI: {uri}")
try:
    engine = create_engine(uri)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM users')).scalar()
        print(f"✅ 成功！用户数量: {result}")
except Exception as e:
    print(f"❌ 失败: {e}")

print()

# 测试3: SQLAlchemy绝对路径 (Windows格式)
print("=== 测试3: SQLAlchemy绝对路径 (Windows) ===")
uri = f'sqlite:///{db_file}'
print(f"URI: {uri}")
try:
    engine = create_engine(uri)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM users')).scalar()
        print(f"✅ 成功！用户数量: {result}")
except Exception as e:
    print(f"❌ 失败: {e}")

print()

# 测试4: SQLAlchemy绝对路径 (Unix格式)
print("=== 测试4: SQLAlchemy绝对路径 (Unix格式) ===")
uri = f'sqlite:////{db_file}'
print(f"URI: {uri}")
try:
    engine = create_engine(uri)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM users')).scalar()
        print(f"✅ 成功！用户数量: {result}")
except Exception as e:
    print(f"❌ 失败: {e}")

