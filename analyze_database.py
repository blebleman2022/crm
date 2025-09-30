#!/usr/bin/env python3
"""分析数据库结构"""
import sqlite3

conn = sqlite3.connect('instance/edu_crm.db')
cursor = conn.cursor()

# 获取所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = cursor.fetchall()

print('=' * 80)
print('数据库表结构分析报告')
print('=' * 80)

print('\n【1】数据库表列表')
print('-' * 80)
for table in tables:
    print(f'  ✓ {table[0]}')

print('\n【2】各表记录数统计')
print('-' * 80)
total_records = 0
for table in tables:
    table_name = table[0]
    cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
    count = cursor.fetchone()[0]
    total_records += count
    print(f'  {table_name:30s} : {count:6d} 条记录')
print(f'  {"总计":30s} : {total_records:6d} 条记录')

print('\n【3】各表字段详情')
print('-' * 80)
for table in tables:
    table_name = table[0]
    cursor.execute(f'PRAGMA table_info({table_name})')
    columns = cursor.fetchall()
    
    print(f'\n表名: {table_name}')
    print(f'  字段数: {len(columns)}')
    print('  字段列表:')
    for col in columns:
        col_id, name, col_type, not_null, default, pk = col
        pk_mark = ' [PK]' if pk else ''
        null_mark = ' NOT NULL' if not_null else ''
        default_mark = f' DEFAULT {default}' if default else ''
        print(f'    - {name:30s} {col_type:15s}{pk_mark}{null_mark}{default_mark}')

print('\n【4】索引信息')
print('-' * 80)
has_index = False
for table in tables:
    table_name = table[0]
    cursor.execute(f'PRAGMA index_list({table_name})')
    indexes = cursor.fetchall()
    
    if indexes:
        has_index = True
        print(f'\n表名: {table_name}')
        for idx in indexes:
            idx_name = idx[1]
            is_unique = '唯一索引' if idx[2] else '普通索引'
            
            # 获取索引字段
            cursor.execute(f'PRAGMA index_info({idx_name})')
            idx_cols = cursor.fetchall()
            col_names = [col[2] for col in idx_cols]
            
            print(f'  - {idx_name:40s} ({is_unique}) on {", ".join(col_names)}')

if not has_index:
    print('  ⚠️  未发现任何索引')

print('\n【5】外键关系')
print('-' * 80)
has_fk = False
for table in tables:
    table_name = table[0]
    cursor.execute(f'PRAGMA foreign_key_list({table_name})')
    fks = cursor.fetchall()
    
    if fks:
        has_fk = True
        print(f'\n表名: {table_name}')
        for fk in fks:
            from_col = fk[3]
            to_table = fk[2]
            to_col = fk[4]
            print(f'  - {from_col} → {to_table}.{to_col}')

if not has_fk:
    print('  ⚠️  未发现任何外键约束')

print('\n【6】数据库文件信息')
print('-' * 80)
import os
db_path = 'instance/edu_crm.db'
file_size = os.path.getsize(db_path)
print(f'  文件路径: {db_path}')
print(f'  文件大小: {file_size:,} bytes ({file_size/1024:.2f} KB)')

# 获取数据库页面信息
cursor.execute('PRAGMA page_count')
page_count = cursor.fetchone()[0]
cursor.execute('PRAGMA page_size')
page_size = cursor.fetchone()[0]
print(f'  页面数量: {page_count:,}')
print(f'  页面大小: {page_size:,} bytes')
print(f'  理论大小: {page_count * page_size:,} bytes')

conn.close()

print('\n' + '=' * 80)
print('分析完成')
print('=' * 80)

