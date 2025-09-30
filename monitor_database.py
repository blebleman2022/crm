#!/usr/bin/env python3
"""
数据库健康监控脚本
用于评估是否需要从SQLite迁移到MySQL
"""
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = 'instance/edu_crm.db'

# 告警阈值
THRESHOLDS = {
    'db_size_warning': 1 * 1024 * 1024 * 1024,  # 1GB
    'db_size_critical': 5 * 1024 * 1024 * 1024,  # 5GB
    'table_rows_warning': 100000,  # 10万条
    'table_rows_critical': 1000000,  # 100万条
    'query_time_warning': 0.5,  # 500ms
    'query_time_critical': 1.0,  # 1秒
}

def get_db_size():
    """获取数据库文件大小"""
    return os.path.getsize(DB_PATH)

def format_size(bytes_size):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def get_table_stats(conn):
    """获取各表统计信息"""
    cursor = conn.cursor()
    
    # 获取所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    stats = []
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        stats.append({
            'table': table,
            'rows': count
        })
    
    return sorted(stats, key=lambda x: x['rows'], reverse=True)

def estimate_growth_rate(conn):
    """估算数据增长率"""
    cursor = conn.cursor()
    
    # 获取最近30天的线索增长
    cursor.execute("""
        SELECT COUNT(*) 
        FROM leads 
        WHERE created_at >= date('now', '-30 days')
    """)
    leads_30d = cursor.fetchone()[0]
    
    # 获取最近30天的客户增长
    cursor.execute("""
        SELECT COUNT(*) 
        FROM customers 
        WHERE created_at >= date('now', '-30 days')
    """)
    customers_30d = cursor.fetchone()[0]
    
    return {
        'leads_per_month': leads_30d,
        'customers_per_month': customers_30d,
        'total_per_month': leads_30d + customers_30d
    }

def predict_future_size(current_size, growth_rate, months):
    """预测未来数据库大小"""
    # 假设每条记录平均2KB
    avg_record_size = 2 * 1024
    monthly_growth = growth_rate['total_per_month'] * avg_record_size
    future_size = current_size + (monthly_growth * months)
    return future_size

def check_query_performance(conn):
    """检查查询性能"""
    import time
    cursor = conn.cursor()
    
    # 测试几个常见查询
    queries = [
        ("SELECT COUNT(*) FROM leads", "线索总数查询"),
        ("SELECT * FROM leads ORDER BY created_at DESC LIMIT 20", "最新线索查询"),
        ("SELECT l.*, u.username FROM leads l JOIN users u ON l.sales_user_id = u.id LIMIT 20", "线索关联查询"),
    ]
    
    results = []
    for sql, desc in queries:
        start = time.time()
        cursor.execute(sql)
        cursor.fetchall()
        elapsed = time.time() - start
        
        results.append({
            'query': desc,
            'time': elapsed,
            'status': 'OK' if elapsed < THRESHOLDS['query_time_warning'] else 
                     'WARNING' if elapsed < THRESHOLDS['query_time_critical'] else 'CRITICAL'
        })
    
    return results

def generate_report():
    """生成监控报告"""
    conn = sqlite3.connect(DB_PATH)
    
    print("=" * 80)
    print("EduConnect CRM 数据库健康监控报告")
    print("=" * 80)
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 数据库大小
    print("【1】数据库大小")
    print("-" * 80)
    db_size = get_db_size()
    print(f"  当前大小: {format_size(db_size)}")
    
    if db_size > THRESHOLDS['db_size_critical']:
        print(f"  状态: 🔴 CRITICAL - 超过5GB，强烈建议迁移到MySQL")
    elif db_size > THRESHOLDS['db_size_warning']:
        print(f"  状态: 🟡 WARNING - 超过1GB，建议开始准备迁移方案")
    else:
        print(f"  状态: 🟢 OK - SQLite完全满足需求")
    
    # 2. 表数据统计
    print("\n【2】表数据统计")
    print("-" * 80)
    table_stats = get_table_stats(conn)
    
    total_rows = sum(stat['rows'] for stat in table_stats)
    print(f"  总记录数: {total_rows:,}")
    print(f"\n  各表记录数:")
    
    for stat in table_stats:
        status = ""
        if stat['rows'] > THRESHOLDS['table_rows_critical']:
            status = "🔴 CRITICAL"
        elif stat['rows'] > THRESHOLDS['table_rows_warning']:
            status = "🟡 WARNING"
        else:
            status = "🟢 OK"
        
        print(f"    {stat['table']:30s} : {stat['rows']:8,} 条  {status}")
    
    # 3. 增长率分析
    print("\n【3】数据增长分析")
    print("-" * 80)
    growth = estimate_growth_rate(conn)
    print(f"  最近30天新增线索: {growth['leads_per_month']} 条")
    print(f"  最近30天新增客户: {growth['customers_per_month']} 条")
    print(f"  月均增长: {growth['total_per_month']} 条记录")
    
    # 4. 未来预测
    print("\n【4】未来容量预测")
    print("-" * 80)
    for months in [6, 12, 24, 36]:
        future_size = predict_future_size(db_size, growth, months)
        print(f"  {months:2d}个月后预计: {format_size(future_size)}")
    
    # 5. 查询性能
    print("\n【5】查询性能测试")
    print("-" * 80)
    perf_results = check_query_performance(conn)
    
    for result in perf_results:
        status_icon = {
            'OK': '🟢',
            'WARNING': '🟡',
            'CRITICAL': '🔴'
        }[result['status']]
        
        print(f"  {status_icon} {result['query']:30s} : {result['time']*1000:.2f}ms")
    
    # 6. 迁移建议
    print("\n【6】迁移建议")
    print("-" * 80)
    
    # 计算迁移评分
    migration_score = 0
    reasons = []
    
    if db_size > THRESHOLDS['db_size_critical']:
        migration_score += 50
        reasons.append("数据库大小超过5GB")
    elif db_size > THRESHOLDS['db_size_warning']:
        migration_score += 20
        reasons.append("数据库大小超过1GB")
    
    for stat in table_stats:
        if stat['rows'] > THRESHOLDS['table_rows_critical']:
            migration_score += 30
            reasons.append(f"{stat['table']}表记录数超过100万")
            break
        elif stat['rows'] > THRESHOLDS['table_rows_warning']:
            migration_score += 10
            reasons.append(f"{stat['table']}表记录数超过10万")
            break
    
    for result in perf_results:
        if result['status'] == 'CRITICAL':
            migration_score += 30
            reasons.append(f"查询性能严重下降（{result['query']}）")
            break
        elif result['status'] == 'WARNING':
            migration_score += 10
            reasons.append(f"查询性能开始下降（{result['query']}）")
            break
    
    # 预测6个月后大小
    future_6m = predict_future_size(db_size, growth, 6)
    if future_6m > THRESHOLDS['db_size_warning']:
        migration_score += 15
        reasons.append("6个月后预计超过1GB")
    
    # 给出建议
    print(f"  迁移评分: {migration_score}/100")
    print()
    
    if migration_score >= 70:
        print("  🔴 建议: 立即开始迁移到MySQL")
        print("  理由:")
        for reason in reasons:
            print(f"    - {reason}")
    elif migration_score >= 40:
        print("  🟡 建议: 开始准备MySQL迁移方案")
        print("  理由:")
        for reason in reasons:
            print(f"    - {reason}")
        print("\n  行动项:")
        print("    1. 在测试环境部署MySQL")
        print("    2. 验证应用兼容性")
        print("    3. 准备数据迁移脚本")
    elif migration_score >= 20:
        print("  🟢 建议: 继续使用SQLite，但需要监控")
        print("  理由:")
        for reason in reasons:
            print(f"    - {reason}")
        print("\n  行动项:")
        print("    1. 执行SQLite索引优化")
        print("    2. 建立定期监控")
        print("    3. 准备迁移预案")
    else:
        print("  🟢 建议: 继续使用SQLite")
        print("  当前状态: SQLite完全满足需求")
        print("\n  行动项:")
        print("    1. 执行SQLite索引优化")
        print("    2. 每月运行一次监控")
    
    # 7. 优化建议
    print("\n【7】SQLite优化建议")
    print("-" * 80)
    
    # 检查是否有索引
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
    index_count = cursor.fetchone()[0]
    
    if index_count < 20:
        print("  ⚠️  检测到索引数量较少，建议执行索引优化")
        print("     运行: python optimize_database.py indexes")
    else:
        print("  ✅ 索引配置良好")
    
    # 检查VACUUM
    cursor.execute("PRAGMA page_count")
    page_count = cursor.fetchone()[0]
    cursor.execute("PRAGMA freelist_count")
    freelist_count = cursor.fetchone()[0]
    
    if freelist_count > page_count * 0.1:
        print("  ⚠️  检测到较多碎片，建议执行VACUUM")
        print("     运行: python optimize_database.py vacuum")
    else:
        print("  ✅ 数据库碎片较少")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("监控完成")
    print("=" * 80)

if __name__ == '__main__':
    generate_report()

