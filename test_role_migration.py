"""
测试角色迁移功能
验证teacher_supervisor角色的功能是否正常
"""

from playwright.sync_api import sync_playwright
import time

def test_role_migration():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("=" * 60)
        print("开始测试角色迁移功能")
        print("=" * 60)
        
        # 1. 测试班主任登录（原teacher角色，现在是teacher_supervisor）
        print("\n📝 测试1: 班主任登录（赵六 - 13900139004）")
        page.goto('http://127.0.0.1:5002/auth/login')
        page.fill('input[name="phone"]', '13900139004')
        page.fill('input[name="password"]', '123456')
        page.click('button[type="submit"]')
        time.sleep(2)
        
        # 验证是否跳转到交付管理仪表板
        if 'delivery/dashboard' in page.url:
            print("✅ 班主任登录成功，正确跳转到交付管理仪表板")
        else:
            print(f"❌ 班主任登录后跳转错误，当前URL: {page.url}")
        
        # 2. 验证班主任可以访问老师管理
        print("\n📝 测试2: 班主任访问老师管理")
        page.goto('http://127.0.0.1:5002/teachers/list')
        time.sleep(2)
        
        if page.url.endswith('/teachers/list'):
            print("✅ 班主任可以访问老师管理页面")
            # 检查页面内容
            if '老师列表' in page.content():
                print("✅ 老师列表页面加载正常")
        else:
            print(f"❌ 班主任无法访问老师管理，跳转到: {page.url}")
        
        # 3. 验证班主任可以访问交付管理
        print("\n📝 测试3: 班主任访问交付管理")
        page.goto('http://127.0.0.1:5002/delivery/dashboard')
        time.sleep(2)
        
        if 'delivery/dashboard' in page.url:
            print("✅ 班主任可以访问交付管理仪表板")
        else:
            print(f"❌ 班主任无法访问交付管理，跳转到: {page.url}")
        
        # 4. 验证班主任可以访问客户列表
        print("\n📝 测试4: 班主任访问客户列表")
        page.goto('http://127.0.0.1:5002/customers/list')
        time.sleep(2)
        
        if 'customers/list' in page.url:
            print("✅ 班主任可以访问客户列表")
        else:
            print(f"❌ 班主任无法访问客户列表，跳转到: {page.url}")
        
        page.context.clear_cookies()
        
        # 5. 测试销售管理登录
        print("\n📝 测试5: 销售管理登录（李四 - 13900139002）")
        page.goto('http://127.0.0.1:5002/auth/login')
        page.fill('input[name="phone"]', '13900139002')
        page.fill('input[name="password"]', '123456')
        page.click('button[type="submit"]')
        time.sleep(2)
        
        # 验证销售管理不能访问老师管理
        print("\n📝 测试6: 销售管理不能访问老师管理")
        page.goto('http://127.0.0.1:5002/teachers/list')
        time.sleep(2)
        
        if 'teachers/list' not in page.url:
            print("✅ 销售管理正确被拒绝访问老师管理")
        else:
            print(f"❌ 销售管理不应该能访问老师管理，当前URL: {page.url}")
        
        # 7. 验证销售管理可以访问线索列表
        print("\n📝 测试7: 销售管理访问线索列表")
        page.goto('http://127.0.0.1:5002/leads/list')
        time.sleep(2)
        
        if 'leads/list' in page.url:
            print("✅ 销售管理可以访问线索列表")
        else:
            print(f"❌ 销售管理无法访问线索列表，跳转到: {page.url}")
        
        page.context.clear_cookies()
        
        # 8. 测试管理员登录
        print("\n📝 测试8: 管理员登录（admin - 13900139000）")
        page.goto('http://127.0.0.1:5002/auth/login')
        page.fill('input[name="phone"]', '13900139000')
        page.fill('input[name="password"]', 'admin123')
        page.click('button[type="submit"]')
        time.sleep(2)
        
        # 9. 验证管理员可以看到用户角色显示
        print("\n📝 测试9: 管理员查看用户列表，验证角色显示")
        page.goto('http://127.0.0.1:5002/admin/users')
        time.sleep(2)
        
        content = page.content()
        if '班主任' in content:
            print("✅ 用户列表中正确显示'班主任'角色")
        else:
            print("❌ 用户列表中未找到'班主任'角色显示")
        
        # 10. 验证添加用户页面的角色选项
        print("\n📝 测试10: 验证添加用户页面的角色选项")
        page.goto('http://127.0.0.1:5002/admin/add_user')
        time.sleep(2)
        
        content = page.content()
        if 'teacher_supervisor' in content:
            print("✅ 添加用户页面包含teacher_supervisor角色选项")
        else:
            print("❌ 添加用户页面缺少teacher_supervisor角色选项")
        
        browser.close()
        
        print("\n" + "=" * 60)
        print("✅ 角色迁移测试完成！")
        print("=" * 60)

if __name__ == '__main__':
    test_role_migration()

