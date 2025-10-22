#!/usr/bin/env python3
"""
更新数据库中的用户角色
将旧的 'teacher' 角色更新为 'teacher_supervisor'（班主任）
"""

import sqlite3
import os
from datetime import datetime

# 颜色输出
class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.NC}")

def print_warning(msg):
    print(f"{Colors.YELLOW}! {msg}{Colors.NC}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.NC}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.NC}")

def main():
    """主函数"""
    print(f"{Colors.GREEN}{'='*60}{Colors.NC}")
    print(f"{Colors.GREEN}EduConnect CRM 用户角色更新工具{Colors.NC}")
    print(f"{Colors.GREEN}{'='*60}{Colors.NC}\n")
    
    # 数据库路径
    db_path = "instance/edu_crm_1022.db"
    
    # 检查数据库文件是否存在
    if not os.path.exists(db_path):
        print_error(f"数据库文件不存在: {db_path}")
        return 1
    
    # 连接数据库
    print_info(f"连接数据库: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. 查看当前所有角色
    print(f"\n{Colors.YELLOW}步骤 1/4: 查看当前角色分布...{Colors.NC}")
    cursor.execute("SELECT role, COUNT(*) as count FROM users GROUP BY role")
    roles = cursor.fetchall()
    
    print("\n当前角色统计：")
    print("-" * 40)
    role_map = {
        'admin': '管理员',
        'sales_manager': '销售管理',
        'salesperson': '销售专员',
        'teacher_supervisor': '班主任',
        'teacher': '辅导老师（旧）'
    }
    
    for role, count in roles:
        role_name = role_map.get(role, role)
        print(f"  {role:<20} ({role_name:<15}) : {count} 个用户")
    
    # 2. 查找需要更新的用户
    print(f"\n{Colors.YELLOW}步骤 2/4: 查找需要更新的用户...{Colors.NC}")
    cursor.execute("SELECT id, username, phone, role FROM users WHERE role='teacher'")
    old_teachers = cursor.fetchall()
    
    if not old_teachers:
        print_success("没有需要更新的用户（所有用户角色已是最新）")
        conn.close()
        return 0
    
    print(f"\n找到 {len(old_teachers)} 个使用旧角色 'teacher' 的用户：")
    print("-" * 60)
    print(f"{'ID':<5} {'用户名':<15} {'手机号':<15} {'当前角色':<15}")
    print("-" * 60)
    for user in old_teachers:
        print(f"{user[0]:<5} {user[1]:<15} {user[2]:<15} {user[3]:<15}")
    
    # 3. 确认更新
    print(f"\n{Colors.YELLOW}步骤 3/4: 执行角色更新...{Colors.NC}")
    print_warning("将把以上用户的角色从 'teacher' 更新为 'teacher_supervisor'（班主任）")
    
    # 执行更新
    try:
        cursor.execute("""
            UPDATE users 
            SET role = 'teacher_supervisor', 
                updated_at = CURRENT_TIMESTAMP 
            WHERE role = 'teacher'
        """)
        
        affected_rows = cursor.rowcount
        conn.commit()
        
        print_success(f"成功更新 {affected_rows} 个用户的角色")
        
    except Exception as e:
        print_error(f"更新失败: {str(e)}")
        conn.rollback()
        conn.close()
        return 1
    
    # 4. 验证更新结果
    print(f"\n{Colors.YELLOW}步骤 4/4: 验证更新结果...{Colors.NC}")
    
    # 检查是否还有旧角色
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='teacher'")
    old_count = cursor.fetchone()[0]
    
    if old_count > 0:
        print_error(f"警告：仍有 {old_count} 个用户使用旧角色 'teacher'")
    else:
        print_success("所有用户角色已更新完成，没有旧角色残留")
    
    # 显示更新后的角色分布
    cursor.execute("SELECT role, COUNT(*) as count FROM users GROUP BY role")
    roles = cursor.fetchall()
    
    print("\n更新后的角色统计：")
    print("-" * 40)
    for role, count in roles:
        role_name = role_map.get(role, role)
        print(f"  {role:<20} ({role_name:<15}) : {count} 个用户")
    
    # 显示更新的用户详情
    print("\n更新的用户详情：")
    print("-" * 60)
    print(f"{'ID':<5} {'用户名':<15} {'手机号':<15} {'新角色':<20}")
    print("-" * 60)
    
    for user in old_teachers:
        cursor.execute("SELECT id, username, phone, role FROM users WHERE id=?", (user[0],))
        updated_user = cursor.fetchone()
        role_name = role_map.get(updated_user[3], updated_user[3])
        print(f"{updated_user[0]:<5} {updated_user[1]:<15} {updated_user[2]:<15} {updated_user[3]} ({role_name})")
    
    conn.close()
    
    # 完成
    print(f"\n{Colors.GREEN}{'='*60}{Colors.NC}")
    print(f"{Colors.GREEN}角色更新完成！{Colors.NC}")
    print(f"{Colors.GREEN}{'='*60}{Colors.NC}\n")
    
    print_info("角色说明：")
    print("  • admin              - 管理员（系统全权限）")
    print("  • sales_manager      - 销售管理（线索、客户、付款管理）")
    print("  • salesperson        - 销售专员（仅管理自己的线索）")
    print("  • teacher_supervisor - 班主任（服务交付、辅导老师管理）")
    print("")
    
    return 0

if __name__ == "__main__":
    exit(main())

