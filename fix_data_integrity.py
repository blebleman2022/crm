#!/usr/bin/env python3
"""
数据完整性修复脚本
用于检查和修复数据库中的孤儿记录和完整性问题
"""

import os
import sys
import sqlite3
from datetime import datetime

def check_foreign_keys_enabled(db_path):
    """检查外键约束是否启用"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys")
    result = cursor.fetchone()[0]
    conn.close()
    return result == 1

def enable_foreign_keys(db_path):
    """启用外键约束"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()
    print("✅ 外键约束已启用")

def check_orphaned_customers(db_path):
    """检查孤儿Customer记录（lead_id不存在）"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = """
    SELECT c.id, c.lead_id 
    FROM customers c 
    LEFT JOIN leads l ON c.lead_id = l.id 
    WHERE l.id IS NULL
    """
    cursor.execute(query)
    orphaned = cursor.fetchall()
    conn.close()
    
    return orphaned

def check_orphaned_payments(db_path):
    """检查孤儿Payment记录（lead_id不存在）"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = """
    SELECT p.id, p.lead_id, p.amount 
    FROM payments p 
    LEFT JOIN leads l ON p.lead_id = l.id 
    WHERE l.id IS NULL
    """
    cursor.execute(query)
    orphaned = cursor.fetchall()
    conn.close()
    
    return orphaned

def check_orphaned_communications(db_path):
    """检查孤儿CommunicationRecord记录（lead_id不存在）"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = """
    SELECT cr.id, cr.lead_id 
    FROM communication_records cr 
    LEFT JOIN leads l ON cr.lead_id = l.id 
    WHERE l.id IS NULL
    """
    cursor.execute(query)
    orphaned = cursor.fetchall()
    conn.close()
    
    return orphaned

def check_orphaned_deliveries(db_path):
    """检查孤儿Delivery记录（customer_id不存在）"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查TutoringDelivery
    query1 = """
    SELECT td.id, td.customer_id 
    FROM tutoring_deliveries td 
    LEFT JOIN customers c ON td.customer_id = c.id 
    WHERE c.id IS NULL
    """
    cursor.execute(query1)
    orphaned_tutoring = cursor.fetchall()
    
    # 检查CompetitionDelivery
    query2 = """
    SELECT cd.id, cd.customer_id 
    FROM competition_deliveries cd 
    LEFT JOIN customers c ON cd.customer_id = c.id 
    WHERE c.id IS NULL
    """
    cursor.execute(query2)
    orphaned_competition = cursor.fetchall()
    
    conn.close()
    
    return orphaned_tutoring, orphaned_competition

def check_invalid_foreign_keys(db_path):
    """检查所有无效的外键引用"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    issues = []
    
    # 检查customers表的外键
    cursor.execute("""
        SELECT c.id, c.lead_id, c.teacher_user_id, c.teacher_id
        FROM customers c
        WHERE (c.lead_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM leads WHERE id = c.lead_id))
           OR (c.teacher_user_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users WHERE id = c.teacher_user_id))
           OR (c.teacher_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM teachers WHERE id = c.teacher_id))
    """)
    invalid_customers = cursor.fetchall()
    if invalid_customers:
        issues.append(f"customers表: {len(invalid_customers)} 条记录有无效外键")
    
    # 检查leads表的外键
    cursor.execute("""
        SELECT l.id, l.sales_user_id
        FROM leads l
        WHERE l.sales_user_id IS NOT NULL 
          AND NOT EXISTS (SELECT 1 FROM users WHERE id = l.sales_user_id)
    """)
    invalid_leads = cursor.fetchall()
    if invalid_leads:
        issues.append(f"leads表: {len(invalid_leads)} 条记录有无效外键")
    
    conn.close()
    return issues

def backup_database(db_path):
    """备份数据库"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"
    
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"✅ 数据库已备份到: {backup_path}")
    return backup_path

def main():
    """主函数"""
    db_path = os.path.join('instance', 'edu_crm.db')
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    print("=" * 60)
    print("数据完整性检查工具")
    print("=" * 60)
    print()
    
    # 1. 检查外键约束
    print("1. 检查外键约束状态...")
    fk_enabled = check_foreign_keys_enabled(db_path)
    if fk_enabled:
        print("   ✅ 外键约束已启用")
    else:
        print("   ⚠️  外键约束未启用（这是主要风险！）")
        print("   建议：在config.py中添加外键约束启用代码")
    print()
    
    # 2. 检查孤儿记录
    print("2. 检查孤儿记录...")
    
    orphaned_customers = check_orphaned_customers(db_path)
    if orphaned_customers:
        print(f"   ⚠️  发现 {len(orphaned_customers)} 个孤儿Customer记录:")
        for cust_id, lead_id in orphaned_customers[:5]:  # 只显示前5个
            print(f"      - Customer ID: {cust_id}, 引用不存在的 Lead ID: {lead_id}")
        if len(orphaned_customers) > 5:
            print(f"      ... 还有 {len(orphaned_customers) - 5} 个")
    else:
        print("   ✅ 没有孤儿Customer记录")
    
    orphaned_payments = check_orphaned_payments(db_path)
    if orphaned_payments:
        print(f"   ⚠️  发现 {len(orphaned_payments)} 个孤儿Payment记录:")
        for pay_id, lead_id, amount in orphaned_payments[:5]:
            print(f"      - Payment ID: {pay_id}, 引用不存在的 Lead ID: {lead_id}, 金额: {amount}")
        if len(orphaned_payments) > 5:
            print(f"      ... 还有 {len(orphaned_payments) - 5} 个")
    else:
        print("   ✅ 没有孤儿Payment记录")
    
    orphaned_communications = check_orphaned_communications(db_path)
    if orphaned_communications:
        print(f"   ⚠️  发现 {len(orphaned_communications)} 个孤儿CommunicationRecord记录:")
        for comm_id, lead_id in orphaned_communications[:5]:
            print(f"      - CommunicationRecord ID: {comm_id}, 引用不存在的 Lead ID: {lead_id}")
        if len(orphaned_communications) > 5:
            print(f"      ... 还有 {len(orphaned_communications) - 5} 个")
    else:
        print("   ✅ 没有孤儿CommunicationRecord记录")
    
    orphaned_tutoring, orphaned_competition = check_orphaned_deliveries(db_path)
    if orphaned_tutoring:
        print(f"   ⚠️  发现 {len(orphaned_tutoring)} 个孤儿TutoringDelivery记录")
    else:
        print("   ✅ 没有孤儿TutoringDelivery记录")
    
    if orphaned_competition:
        print(f"   ⚠️  发现 {len(orphaned_competition)} 个孤儿CompetitionDelivery记录")
    else:
        print("   ✅ 没有孤儿CompetitionDelivery记录")
    
    print()
    
    # 3. 检查无效外键
    print("3. 检查无效外键引用...")
    invalid_fk_issues = check_invalid_foreign_keys(db_path)
    if invalid_fk_issues:
        print("   ⚠️  发现无效外键引用:")
        for issue in invalid_fk_issues:
            print(f"      - {issue}")
    else:
        print("   ✅ 所有外键引用有效")
    print()
    
    # 4. 总结
    print("=" * 60)
    print("检查总结")
    print("=" * 60)
    
    total_issues = (
        len(orphaned_customers) + 
        len(orphaned_payments) + 
        len(orphaned_communications) + 
        len(orphaned_tutoring) + 
        len(orphaned_competition) +
        len(invalid_fk_issues)
    )
    
    if total_issues == 0 and fk_enabled:
        print("✅ 数据完整性检查通过，没有发现问题")
    else:
        print(f"⚠️  发现 {total_issues} 个数据完整性问题")
        print()
        print("建议操作：")
        print("1. 立即备份数据库")
        print("2. 查看《数据丢失隐患分析报告.md》了解详细信息")
        print("3. 按照报告中的修复方案进行修复")
        print("4. 启用外键约束（最重要）")
        print()
        
        # 询问是否备份
        response = input("是否立即备份数据库？(y/n): ")
        if response.lower() == 'y':
            backup_database(db_path)
    
    print()

if __name__ == '__main__':
    main()

