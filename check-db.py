#!/usr/bin/env python3
"""
数据库路径检查脚本
"""

import os
import sys

# 获取项目根目录
basedir = os.path.abspath(os.path.dirname(__file__))

print("=" * 60)
print("数据库路径检查")
print("=" * 60)
print()

# 1. 检查basedir
print(f"1. 项目根目录 (basedir):")
print(f"   {basedir}")
print()

# 2. 检查instance目录
instance_dir = os.path.join(basedir, 'instance')
print(f"2. Instance目录:")
print(f"   {instance_dir}")
print(f"   存在: {os.path.exists(instance_dir)}")
print()

# 3. 检查数据库文件
db_path = os.path.join(basedir, 'instance', 'edu_crm.db')
print(f"3. 数据库文件路径:")
print(f"   {db_path}")
print(f"   存在: {os.path.exists(db_path)}")
if os.path.exists(db_path):
    print(f"   大小: {os.path.getsize(db_path)} bytes")
    print(f"   可读: {os.access(db_path, os.R_OK)}")
    print(f"   可写: {os.access(db_path, os.W_OK)}")
print()

# 4. 检查配置
print(f"4. 环境变量:")
print(f"   FLASK_ENV: {os.environ.get('FLASK_ENV', 'not set')}")
print(f"   DATABASE_URL: {os.environ.get('DATABASE_URL', 'not set')}")
print()

# 5. 加载配置并检查
sys.path.insert(0, basedir)
from config import config

config_name = os.environ.get('FLASK_ENV', 'development')
config_class = config.get(config_name, config['default'])

print(f"5. 配置类:")
print(f"   配置名称: {config_name}")
print(f"   配置类: {config_class.__name__}")
print(f"   数据库URI: {config_class.SQLALCHEMY_DATABASE_URI}")
print()

# 6. 检查数据库表
if os.path.exists(db_path):
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"6. 数据库表:")
        if tables:
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print(f"   ⚠️  数据库中没有表！")
        conn.close()
    except Exception as e:
        print(f"   ✗ 错误: {e}")
else:
    print(f"6. 数据库表:")
    print(f"   ✗ 数据库文件不存在，无法检查表")

print()
print("=" * 60)

