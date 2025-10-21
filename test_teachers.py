#!/usr/bin/env python3
"""
测试老师管理功能
"""
import time

def test_teachers():
    """测试老师的增删改查和分配功能"""
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # 1. 登录（使用teacher角色的测试账号）
            print("1. 登录系统...")
            page.goto('http://127.0.0.1:5002/auth/login')
            page.fill('input[name="phone"]', '13800000004')  # teacher角色
            page.fill('input[name="password"]', '123456')
            page.click('button[type="submit"]')
            page.wait_for_url('**/leads/dashboard', timeout=5000)
            print("   ✓ 登录成功")
            
            # 2. 访问老师列表页
            print("\n2. 访问老师列表页...")
            page.goto('http://127.0.0.1:5002/teachers/list')
            page.wait_for_selector('h2:has-text("老师列表")', timeout=5000)
            print("   ✓ 老师列表页加载成功")
            
            # 3. 添加老师
            print("\n3. 添加新老师...")
            page.click('a:has-text("添加老师")')
            page.wait_for_selector('h2:has-text("添加新老师")', timeout=5000)
            
            # 填写老师信息
            page.fill('input[name="chinese_name"]', '张三')
            page.fill('input[name="english_name"]', 'Zhang San')
            page.fill('input[name="current_institution"]', '清华大学')
            page.fill('input[name="major_direction"]', '计算机科学')
            page.select_option('select[name="highest_degree"]', '博士')
            page.fill('textarea[name="degree_description"]', '清华大学计算机系博士')
            page.fill('textarea[name="research_achievements"]', '发表SCI论文10篇')
            page.fill('textarea[name="innovation_coaching_achievements"]', '指导学生获得国家级奖项5项')
            page.fill('textarea[name="social_roles"]', 'IEEE会员')
            
            page.click('button[type="submit"]')
            page.wait_for_url('**/teachers/list', timeout=5000)
            print("   ✓ 老师添加成功")
            
            # 4. 验证老师是否在列表中
            print("\n4. 验证老师列表...")
            page.wait_for_selector('td:has-text("张三")', timeout=5000)
            print("   ✓ 老师显示在列表中")
            
            # 5. 查看老师详情
            print("\n5. 查看老师详情...")
            page.click('a:has-text("详情")')
            page.wait_for_selector('h2:has-text("张三")', timeout=5000)
            
            # 验证详情页内容
            assert page.locator('text=清华大学').is_visible()
            assert page.locator('text=计算机科学').is_visible()
            assert page.locator('text=博士').is_visible()
            print("   ✓ 老师详情页显示正确")
            
            # 6. 编辑老师
            print("\n6. 编辑老师信息...")
            page.click('a:has-text("编辑")')
            page.wait_for_selector('h2:has-text("编辑老师信息")', timeout=5000)
            
            # 修改专业方向
            page.fill('input[name="major_direction"]', '人工智能')
            page.click('button[type="submit"]')
            page.wait_for_url('**/teachers/list', timeout=5000)
            print("   ✓ 老师信息编辑成功")
            
            # 7. 验证修改是否生效
            print("\n7. 验证修改...")
            page.wait_for_selector('td:has-text("人工智能")', timeout=5000)
            print("   ✓ 修改已生效")
            
            # 8. 测试搜索功能
            print("\n8. 测试搜索功能...")
            page.fill('input[name="search"]', '张三')
            page.click('button:has-text("查询")')
            page.wait_for_selector('td:has-text("张三")', timeout=5000)
            print("   ✓ 搜索功能正常")
            
            # 9. 测试状态筛选
            print("\n9. 测试状态筛选...")
            page.select_option('select[name="status"]', 'active')
            page.click('button:has-text("查询")')
            page.wait_for_selector('td:has-text("张三")', timeout=5000)
            print("   ✓ 状态筛选功能正常")
            
            # 10. 测试禁用老师（先清除搜索）
            print("\n10. 测试禁用老师...")
            page.goto('http://127.0.0.1:5002/teachers/list')
            page.wait_for_selector('td:has-text("张三")', timeout=5000)
            
            # 点击禁用按钮并确认
            page.on('dialog', lambda dialog: dialog.accept())
            page.click('button:has-text("禁用")')
            page.wait_for_selector('span:has-text("禁用")', timeout=5000)
            print("   ✓ 老师禁用成功")
            
            # 11. 测试启用老师
            print("\n11. 测试启用老师...")
            page.click('button:has-text("启用")')
            page.wait_for_selector('span:has-text("启用")', timeout=5000)
            print("   ✓ 老师启用成功")
            
            print("\n" + "="*50)
            print("✅ 所有测试通过！")
            print("="*50)
            
        except Exception as e:
            print(f"\n❌ 测试失败: {str(e)}")
            # 截图保存错误状态
            page.screenshot(path='test_teachers_error.png')
            print("错误截图已保存到 test_teachers_error.png")
            raise
        finally:
            browser.close()

if __name__ == '__main__':
    test_teachers()

