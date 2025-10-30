#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据迁移脚本：从单赛事管理迁移到多赛事管理
- 创建 customer_competitions 表
- 迁移 competition_deliveries 数据到 customer_competitions
- 保留 competition_deliveries 表（暂不删除，待确认后手动删除）
"""

import sqlite3
import sys
from datetime import datetime

def check_table_exists(conn, table_name):
    """检查表是否存在"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

def get_table_columns(conn, table_name):
    """获取表的所有列名"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]

def create_customer_competitions_table(conn):
    """创建 customer_competitions 表"""
    cursor = conn.cursor()
    
    print("\n步骤 1/3: 创建 customer_competitions 表...")
    
    # 检查表是否已存在
    if check_table_exists(conn, 'customer_competitions'):
        print("! customer_competitions 表已存在")
        columns = get_table_columns(conn, 'customer_competitions')
        
        # 检查是否有所有必需的列
        required_columns = ['id', 'customer_id', 'competition_name_id', 'status', 
                          'custom_award', 'created_by_user_id', 'created_at', 'updated_at']
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            print(f"! 表结构不完整，缺少列: {missing_columns}")
            print("! 删除旧表并重建...")
            cursor.execute("DROP TABLE customer_competitions")
        else:
            print("✓ 表结构正确，跳过创建")
            return
    
    # 创建新表
    cursor.execute("""
        CREATE TABLE customer_competitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            competition_name_id INTEGER NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT '未报名',
            custom_award VARCHAR(100),
            created_by_user_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE,
            FOREIGN KEY (competition_name_id) REFERENCES competition_names (id),
            FOREIGN KEY (created_by_user_id) REFERENCES users (id)
        )
    """)
    
    print("✓ customer_competitions 表创建成功")

def migrate_competition_deliveries(conn):
    """迁移 competition_deliveries 数据到 customer_competitions"""
    cursor = conn.cursor()
    
    print("\n步骤 2/3: 迁移数据...")
    
    # 检查旧表是否存在
    if not check_table_exists(conn, 'competition_deliveries'):
        print("! competition_deliveries 表不存在，跳过数据迁移")
        return
    
    # 获取所有需要迁移的数据
    cursor.execute("""
        SELECT 
            cd.id,
            cd.customer_id,
            cd.competition_name_id,
            cd.delivery_status,
            c.teacher_user_id,
            cd.created_at
        FROM competition_deliveries cd
        JOIN customers c ON cd.customer_id = c.id
        WHERE cd.competition_name_id IS NOT NULL
    """)
    
    deliveries = cursor.fetchall()
    
    if not deliveries:
        print("! 没有需要迁移的数据")
        return
    
    print(f"! 发现 {len(deliveries)} 条数据需要迁移")
    
    # 状态映射
    status_mapping = {
        '未报名': '未报名',
        '已报名待竞赛': '已报名',
        '竞赛进行中': '已报名',
        '等待竞赛结果': '已报名',
        '奖项已获取': '国家一等奖',  # 默认映射为国家一等奖，需要后续人工调整
        '服务完结': '国家一等奖'     # 默认映射为国家一等奖，需要后续人工调整
    }
    
    migrated_count = 0
    skipped_count = 0
    
    for delivery in deliveries:
        delivery_id, customer_id, competition_name_id, delivery_status, teacher_user_id, created_at = delivery
        
        # 检查是否已经迁移过
        cursor.execute("""
            SELECT id FROM customer_competitions 
            WHERE customer_id = ? AND competition_name_id = ?
        """, (customer_id, competition_name_id))
        
        if cursor.fetchone():
            skipped_count += 1
            continue
        
        # 映射状态
        new_status = status_mapping.get(delivery_status, '未报名')
        
        # 如果没有班主任，使用管理员ID（假设ID=1）
        if not teacher_user_id:
            teacher_user_id = 1
        
        # 插入新记录
        cursor.execute("""
            INSERT INTO customer_competitions 
            (customer_id, competition_name_id, status, created_by_user_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (customer_id, competition_name_id, new_status, teacher_user_id, created_at, created_at))
        
        migrated_count += 1
    
    print(f"✓ 成功迁移 {migrated_count} 条数据")
    if skipped_count > 0:
        print(f"! 跳过 {skipped_count} 条已存在的数据")
    
    # 提示需要人工调整的数据
    cursor.execute("""
        SELECT COUNT(*) FROM customer_competitions 
        WHERE status IN ('国家一等奖') 
        AND id IN (
            SELECT cc.id FROM customer_competitions cc
            JOIN competition_deliveries cd ON cc.customer_id = cd.customer_id 
                AND cc.competition_name_id = cd.competition_name_id
            WHERE cd.delivery_status IN ('奖项已获取', '服务完结')
        )
    """)
    need_adjustment = cursor.fetchone()[0]
    
    if need_adjustment > 0:
        print(f"\n⚠️  注意：有 {need_adjustment} 条记录的状态被默认设置为'国家一等奖'")
        print("   这些记录原本的状态是'奖项已获取'或'服务完结'")
        print("   请在系统中手动调整为正确的奖项等级")

def create_indexes(conn):
    """创建索引以提高查询性能"""
    cursor = conn.cursor()
    
    print("\n步骤 3/3: 创建索引...")
    
    try:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_competitions_customer_id 
            ON customer_competitions(customer_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_competitions_status 
            ON customer_competitions(status)
        """)
        
        print("✓ 索引创建成功")
    except Exception as e:
        print(f"! 创建索引时出错: {e}")

def main():
    """主函数"""
    db_path = 'instance/edu_crm.db'
    
    print("=" * 60)
    print("数据迁移：单赛事管理 → 多赛事管理")
    print("=" * 60)
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        
        # 执行迁移步骤
        create_customer_competitions_table(conn)
        migrate_competition_deliveries(conn)
        create_indexes(conn)
        
        # 提交更改
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ 数据迁移完成！")
        print("=" * 60)
        print("\n后续步骤：")
        print("1. 在系统中检查迁移的数据是否正确")
        print("2. 手动调整被默认设置为'国家一等奖'的记录")
        print("3. 确认无误后，可以删除 competition_deliveries 表")
        print("   （执行：DROP TABLE competition_deliveries;）")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    main()

