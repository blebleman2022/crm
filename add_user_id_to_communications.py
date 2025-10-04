#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为 communication_records 表添加 user_id 字段
"""

from run import create_app
from models import db
from sqlalchemy import text

app = create_app('development')

with app.app_context():
    print('=== 开始数据库迁移：添加 user_id 字段到 communication_records 表 ===\n')
    
    try:
        # 检查字段是否已存在
        result = db.session.execute(text("PRAGMA table_info(communication_records)"))
        columns = [row[1] for row in result]
        
        if 'user_id' in columns:
            print('✅ user_id 字段已存在，无需添加')
        else:
            print('正在添加 user_id 字段...')
            
            # 添加 user_id 字段
            db.session.execute(text('''
                ALTER TABLE communication_records 
                ADD COLUMN user_id INTEGER
            '''))
            
            db.session.commit()
            print('✅ user_id 字段添加成功')
        
        print('\n=== 迁移完成 ===')
        
    except Exception as e:
        db.session.rollback()
        print(f'❌ 迁移失败: {str(e)}')
        raise

