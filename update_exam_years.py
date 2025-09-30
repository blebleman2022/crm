"""
批量更新现有客户的中高考年份
根据线索的年级自动计算并更新客户的 exam_year、tutoring_expire_date 和 award_expire_date
"""
from run import app
from models import db, Customer
from utils.exam_calculator import calculate_exam_year
from datetime import date


def update_all_customers_exam_years():
    """批量更新所有客户的中高考年份"""
    with app.app_context():
        # 获取所有客户
        customers = Customer.query.all()
        
        print(f'开始更新客户中高考年份...')
        print(f'共有 {len(customers)} 个客户需要处理\n')
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for customer in customers:
            try:
                # 获取线索的年级
                grade = customer.lead.grade
                
                if not grade:
                    print(f'❌ 客户 {customer.id} ({customer.lead.get_display_name()}) 的年级信息缺失，跳过')
                    skipped_count += 1
                    continue
                
                # 计算中高考年份
                exam_year = calculate_exam_year(grade)
                
                if not exam_year:
                    print(f'❌ 客户 {customer.id} ({customer.lead.get_display_name()}) 的年级 "{grade}" 无法计算考试年份，跳过')
                    error_count += 1
                    continue
                
                # 计算到期时间
                expire_date = date(exam_year, 5, 31)
                
                # 更新客户信息
                old_exam_year = customer.exam_year
                customer.exam_year = exam_year
                customer.tutoring_expire_date = expire_date
                customer.award_expire_date = expire_date
                
                updated_count += 1
                
                if old_exam_year != exam_year:
                    print(f'✅ 客户 {customer.id} ({customer.lead.get_display_name()}):')
                    print(f'   年级: {grade}')
                    print(f'   中高考年份: {old_exam_year or "未设置"} → {exam_year}')
                    print(f'   到期时间: {expire_date}')
                else:
                    print(f'✓  客户 {customer.id} ({customer.lead.get_display_name()}): 年级 {grade}, 考试年份 {exam_year} (无变化)')
                
            except Exception as e:
                print(f'❌ 处理客户 {customer.id} 时出错: {str(e)}')
                error_count += 1
                continue
        
        # 提交更改
        try:
            db.session.commit()
            print(f'\n✅ 批量更新完成！')
            print(f'   成功更新: {updated_count} 个客户')
            print(f'   跳过: {skipped_count} 个客户（年级信息缺失）')
            print(f'   错误: {error_count} 个客户')
        except Exception as e:
            db.session.rollback()
            print(f'\n❌ 提交更改时出错: {str(e)}')
            print('所有更改已回滚')


if __name__ == '__main__':
    update_all_customers_exam_years()

