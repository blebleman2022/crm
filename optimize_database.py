#!/usr/bin/env python3
"""
数据库优化脚本
执行前会自动备份数据库
"""
import sqlite3
import os
import shutil
from datetime import datetime

# 数据库路径
DB_PATH = 'instance/edu_crm.db'

def backup_database():
    """备份数据库"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f'instance/edu_crm_backup_{timestamp}.db'
    
    print(f"📦 正在备份数据库...")
    shutil.copy2(DB_PATH, backup_path)
    print(f"✅ 备份完成: {backup_path}")
    return backup_path

def execute_sql(cursor, sql, description):
    """执行SQL并处理错误"""
    try:
        cursor.execute(sql)
        print(f"  ✅ {description}")
        return True
    except sqlite3.Error as e:
        if "already exists" in str(e) or "duplicate" in str(e).lower():
            print(f"  ⏭️  {description} (已存在，跳过)")
            return True
        else:
            print(f"  ❌ {description} - 错误: {e}")
            return False

def optimize_database(phase='all'):
    """
    优化数据库
    phase: 'all', 'indexes', 'cleanup', 'vacuum'
    """
    
    # 备份数据库
    backup_path = backup_database()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    success_count = 0
    total_count = 0
    
    # 第一阶段：添加索引
    if phase in ['all', 'indexes']:
        print("\n" + "="*80)
        print("【阶段1】添加缺失的索引")
        print("="*80)
        
        indexes = [
            # users表索引
            ("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)", 
             "users表: role字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)", 
             "users表: status字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_users_role_status ON users(role, status)", 
             "users表: (role, status)组合索引"),
            
            # leads表索引
            ("CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at DESC)", 
             "leads表: created_at字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_leads_grade ON leads(grade)", 
             "leads表: grade字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_leads_district ON leads(district)", 
             "leads表: district字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_leads_sales_stage ON leads(sales_user_id, stage)", 
             "leads表: (sales_user_id, stage)组合索引"),
            
            # customers表索引
            ("CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_lead_id ON customers(lead_id)", 
             "customers表: lead_id唯一索引"),
            ("CREATE INDEX IF NOT EXISTS idx_customers_teacher_id ON customers(teacher_user_id)", 
             "customers表: teacher_user_id字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_customers_exam_year ON customers(exam_year)", 
             "customers表: exam_year字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_customers_priority ON customers(is_priority)", 
             "customers表: is_priority字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_customers_converted_at ON customers(converted_at DESC)", 
             "customers表: converted_at字段索引"),
            
            # tutoring_deliveries表索引
            ("CREATE UNIQUE INDEX IF NOT EXISTS idx_tutoring_customer_id ON tutoring_deliveries(customer_id)", 
             "tutoring_deliveries表: customer_id唯一索引"),
            ("CREATE INDEX IF NOT EXISTS idx_tutoring_thesis_status ON tutoring_deliveries(thesis_status)", 
             "tutoring_deliveries表: thesis_status字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_tutoring_next_class ON tutoring_deliveries(next_class_at)", 
             "tutoring_deliveries表: next_class_at字段索引"),
            
            # competition_deliveries表索引
            ("CREATE UNIQUE INDEX IF NOT EXISTS idx_competition_customer_id ON competition_deliveries(customer_id)", 
             "competition_deliveries表: customer_id唯一索引"),
            ("CREATE INDEX IF NOT EXISTS idx_competition_name_id ON competition_deliveries(competition_name_id)", 
             "competition_deliveries表: competition_name_id字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_competition_status ON competition_deliveries(delivery_status)", 
             "competition_deliveries表: delivery_status字段索引"),
            
            # payments表索引
            ("CREATE INDEX IF NOT EXISTS idx_payments_lead_id ON payments(lead_id)", 
             "payments表: lead_id字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date DESC)", 
             "payments表: payment_date字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_payments_created ON payments(created_at DESC)", 
             "payments表: created_at字段索引"),
            
            # communication_records表索引
            ("CREATE INDEX IF NOT EXISTS idx_comm_lead_id ON communication_records(lead_id)", 
             "communication_records表: lead_id字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_comm_customer_id ON communication_records(customer_id)", 
             "communication_records表: customer_id字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_comm_created ON communication_records(created_at DESC)", 
             "communication_records表: created_at字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_comm_lead_created ON communication_records(lead_id, created_at DESC)", 
             "communication_records表: (lead_id, created_at)组合索引"),
            
            # login_logs表索引
            ("CREATE INDEX IF NOT EXISTS idx_login_user_id ON login_logs(user_id)", 
             "login_logs表: user_id字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_login_phone ON login_logs(phone)", 
             "login_logs表: phone字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_login_time ON login_logs(login_time DESC)", 
             "login_logs表: login_time字段索引"),
            ("CREATE INDEX IF NOT EXISTS idx_login_result ON login_logs(login_result)", 
             "login_logs表: login_result字段索引"),
        ]
        
        for sql, desc in indexes:
            total_count += 1
            if execute_sql(cursor, sql, desc):
                success_count += 1
        
        conn.commit()
    
    # 第二阶段：清理废弃表
    if phase in ['all', 'cleanup']:
        print("\n" + "="*80)
        print("【阶段2】清理废弃表")
        print("="*80)
        
        # 检查consultation_details表是否有数据
        cursor.execute("SELECT COUNT(*) FROM consultation_details")
        count = cursor.fetchone()[0]
        
        if count == 0:
            total_count += 1
            if execute_sql(cursor, "DROP TABLE IF EXISTS consultation_details", 
                          "删除废弃表: consultation_details"):
                success_count += 1
        else:
            print(f"  ⚠️  consultation_details表有{count}条数据，跳过删除")
        
        conn.commit()
    
    # 第三阶段：优化数据库
    if phase in ['all', 'vacuum']:
        print("\n" + "="*80)
        print("【阶段3】优化数据库")
        print("="*80)
        
        print("  🔄 执行VACUUM清理碎片...")
        cursor.execute("VACUUM")
        print("  ✅ VACUUM完成")
        
        print("  🔄 执行ANALYZE更新统计信息...")
        cursor.execute("ANALYZE")
        print("  ✅ ANALYZE完成")
    
    conn.close()
    
    # 统计结果
    print("\n" + "="*80)
    print("【优化完成】")
    print("="*80)
    print(f"  成功: {success_count}/{total_count}")
    print(f"  备份: {backup_path}")
    
    # 显示数据库大小变化
    original_size = os.path.getsize(backup_path)
    new_size = os.path.getsize(DB_PATH)
    size_diff = original_size - new_size
    
    print(f"\n  原始大小: {original_size:,} bytes ({original_size/1024:.2f} KB)")
    print(f"  优化后:   {new_size:,} bytes ({new_size/1024:.2f} KB)")
    if size_diff > 0:
        print(f"  节省:     {size_diff:,} bytes ({size_diff/1024:.2f} KB)")
    elif size_diff < 0:
        print(f"  增加:     {abs(size_diff):,} bytes ({abs(size_diff)/1024:.2f} KB)")
    
    print("\n✅ 数据库优化完成！")
    print(f"💡 如需回滚，请使用备份文件: {backup_path}")

if __name__ == '__main__':
    import sys
    
    phase = sys.argv[1] if len(sys.argv) > 1 else 'all'
    
    if phase not in ['all', 'indexes', 'cleanup', 'vacuum']:
        print("用法: python optimize_database.py [all|indexes|cleanup|vacuum]")
        print("  all     - 执行所有优化（默认）")
        print("  indexes - 仅添加索引")
        print("  cleanup - 仅清理废弃表")
        print("  vacuum  - 仅执行VACUUM和ANALYZE")
        sys.exit(1)
    
    print("="*80)
    print("EduConnect CRM 数据库优化工具")
    print("="*80)
    print(f"执行阶段: {phase}")
    print()
    
    response = input("⚠️  此操作将修改数据库，是否继续？(yes/no): ")
    if response.lower() != 'yes':
        print("❌ 操作已取消")
        sys.exit(0)
    
    optimize_database(phase)

