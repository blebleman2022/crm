#!/usr/bin/env python3
"""
统一线索阶段定义
将数据库中的阶段值统一为代码定义的标准阶段
"""
import sqlite3
import shutil
from datetime import datetime

DB_PATH = 'instance/edu_crm.db'

# 标准阶段定义
STANDARD_STAGES = [
    '获取联系方式',
    '线下见面',
    '首笔支付',
    '次笔支付',
    '全款支付'
]

# 阶段映射关系（旧值 -> 新值）
STAGE_MAPPING = {
    '初步接触': '获取联系方式',
    '合同签订': '全款支付',
    '定金支付': '首笔支付',
    '次笔款项支付': '次笔支付',
    '第二笔款项支付': '次笔支付',
}

def backup_database():
    """备份数据库"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f'instance/edu_crm_backup_stage_fix_{timestamp}.db'
    shutil.copy2(DB_PATH, backup_path)
    print(f"✅ 备份完成: {backup_path}")
    return backup_path

def analyze_current_stages():
    """分析当前数据库中的阶段值"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("当前数据库中的线索阶段分析")
    print("="*80)
    
    # 查询所有不同的阶段值及其数量
    cursor.execute("""
        SELECT stage, COUNT(*) as count 
        FROM leads 
        WHERE stage IS NOT NULL 
        GROUP BY stage 
        ORDER BY count DESC
    """)
    
    stages = cursor.fetchall()
    
    if not stages:
        print("  ℹ️  数据库中没有线索数据")
        conn.close()
        return []
    
    print(f"\n发现 {len(stages)} 种不同的阶段值:\n")
    
    total_leads = 0
    needs_update = []
    
    for stage, count in stages:
        total_leads += count
        is_standard = stage in STANDARD_STAGES
        status = "✅ 标准" if is_standard else "⚠️  需要更新"
        
        print(f"  {status} | {stage:20s} | {count:3d} 条记录", end="")
        
        if not is_standard:
            if stage in STAGE_MAPPING:
                new_stage = STAGE_MAPPING[stage]
                print(f" → 将更新为: {new_stage}")
                needs_update.append((stage, new_stage, count))
            else:
                print(f" → ⚠️  未定义映射关系")
                needs_update.append((stage, None, count))
        else:
            print()
    
    print(f"\n总计: {total_leads} 条线索记录")
    
    conn.close()
    return needs_update

def fix_stages():
    """修复阶段值"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("执行阶段值修复")
    print("="*80)
    
    total_updated = 0
    
    for old_stage, new_stage, count in analyze_current_stages():
        if new_stage is None:
            print(f"\n⚠️  跳过未定义映射的阶段: {old_stage}")
            continue
        
        print(f"\n正在更新: {old_stage} → {new_stage}")
        
        try:
            cursor.execute(
                "UPDATE leads SET stage = ? WHERE stage = ?",
                (new_stage, old_stage)
            )
            updated = cursor.rowcount
            total_updated += updated
            print(f"  ✅ 成功更新 {updated} 条记录")
        except Exception as e:
            print(f"  ❌ 更新失败: {str(e)}")
            conn.rollback()
            conn.close()
            return False
    
    conn.commit()
    
    print(f"\n{'='*80}")
    print(f"修复完成: 共更新 {total_updated} 条记录")
    print(f"{'='*80}")
    
    conn.close()
    return True

def verify_stages():
    """验证修复结果"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("验证修复结果")
    print("="*80)
    
    # 查询所有阶段值
    cursor.execute("""
        SELECT stage, COUNT(*) as count 
        FROM leads 
        WHERE stage IS NOT NULL 
        GROUP BY stage 
        ORDER BY stage
    """)
    
    stages = cursor.fetchall()
    
    print(f"\n修复后的阶段值:\n")
    
    all_valid = True
    for stage, count in stages:
        is_valid = stage in STANDARD_STAGES
        status = "✅" if is_valid else "❌"
        print(f"  {status} {stage:20s} | {count:3d} 条记录")
        
        if not is_valid:
            all_valid = False
    
    # 检查是否有无效阶段
    cursor.execute("""
        SELECT COUNT(*) FROM leads 
        WHERE stage IS NOT NULL 
        AND stage NOT IN (?, ?, ?, ?, ?)
    """, STANDARD_STAGES)
    
    invalid_count = cursor.fetchone()[0]
    
    print(f"\n{'='*80}")
    if invalid_count == 0:
        print("✅ 验证通过: 所有阶段值都符合标准定义")
    else:
        print(f"❌ 验证失败: 仍有 {invalid_count} 条记录使用非标准阶段值")
    print(f"{'='*80}")
    
    conn.close()
    return all_valid

def show_standard_stages():
    """显示标准阶段定义"""
    print("\n" + "="*80)
    print("标准线索阶段定义")
    print("="*80)
    
    print("\n阶段列表（按业务流程顺序）:\n")
    
    stage_info = [
        ('获取联系方式', 'contact', '默认初始阶段', '蓝色'),
        ('线下见面', 'meeting', '设置了见面时间', '黄色'),
        ('首笔支付', 'first_payment', '有1笔付款记录', '橙色'),
        ('次笔支付', 'second_payment', '有2笔或以上付款记录', '绿色'),
        ('全款支付', 'full_payment', '已付款 ≥ 合同金额', '紫色'),
    ]
    
    for i, (name, code, condition, color) in enumerate(stage_info, 1):
        print(f"  {i}. {name:15s} ({code:15s}) - {condition:30s} [{color}]")
    
    print(f"\n{'='*80}")

if __name__ == '__main__':
    print("="*80)
    print("EduConnect CRM 线索阶段统一工具")
    print("="*80)
    
    # 显示标准阶段定义
    show_standard_stages()
    
    # 分析当前阶段
    needs_update = analyze_current_stages()
    
    if not needs_update:
        print("\n✅ 所有阶段值都符合标准定义，无需修复")
        exit(0)
    
    # 确认是否执行修复
    print("\n" + "="*80)
    response = input("⚠️  是否执行阶段值修复？(yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ 已取消修复操作")
        exit(0)
    
    # 备份数据库
    print("\n📦 正在备份数据库...")
    backup_path = backup_database()
    
    # 执行修复
    if fix_stages():
        # 验证结果
        if verify_stages():
            print("\n🎉 线索阶段统一完成！")
            print(f"   备份文件: {backup_path}")
        else:
            print("\n⚠️  修复完成但验证未通过，请检查数据")
            print(f"   备份文件: {backup_path}")
    else:
        print("\n❌ 修复失败，数据库未修改")
        print(f"   备份文件: {backup_path}")

