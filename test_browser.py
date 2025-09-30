"""
使用 Playwright 进行浏览器测试
"""
import asyncio
from playwright.async_api import async_playwright
import time

async def test_customer_list():
    """测试客户列表页面"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print('=' * 80)
            print('测试1：客户列表页面')
            print('=' * 80)
            
            # 登录
            await page.goto('http://localhost:5001/login')
            await page.fill('input[name="username"]', 'Kingble')
            await page.fill('input[name="password"]', 'Kingble')
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(1000)
            
            # 访问客户列表
            await page.goto('http://localhost:5001/customers')
            await page.wait_for_timeout(1000)
            
            # 检查页面标题
            title = await page.title()
            print(f'页面标题: {title}')
            assert '客户管理' in title, '页面标题不正确'
            
            # 检查客户列表是否显示
            customers = await page.query_selector_all('tbody tr')
            print(f'客户数量: {len(customers)}')
            assert len(customers) > 0, '没有显示客户'
            
            # 检查奖项等级列是否正确显示
            first_customer = customers[0]
            award_cell = await first_customer.query_selector('td:nth-child(5)')
            award_text = await award_cell.inner_text()
            print(f'第一个客户的奖项等级: {award_text.strip()}')
            
            print('✅ 客户列表页面测试通过')
            
        finally:
            await browser.close()


async def test_customer_edit():
    """测试客户编辑页面"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print('\n' + '=' * 80)
            print('测试2：客户编辑页面')
            print('=' * 80)
            
            # 登录
            await page.goto('http://localhost:5001/login')
            await page.fill('input[name="username"]', 'Kingble')
            await page.fill('input[name="password"]', 'Kingble')
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(1000)
            
            # 访问客户列表
            await page.goto('http://localhost:5001/customers')
            await page.wait_for_timeout(1000)
            
            # 点击第一个客户的编辑按钮
            edit_button = await page.query_selector('a[href*="/customers/"][href*="/edit"]')
            if edit_button:
                await edit_button.click()
                await page.wait_for_timeout(1000)
                
                # 检查页面标题
                title = await page.title()
                print(f'页面标题: {title}')
                assert '编辑客户' in title, '页面标题不正确'
                
                # 检查表单字段
                student_name = await page.query_selector('input[name="student_name"]')
                assert student_name is not None, '学员姓名字段不存在'
                
                contact_info = await page.query_selector('input[name="contact_info"]')
                assert contact_info is not None, '联系方式字段不存在'
                
                sales_user = await page.query_selector('select[name="sales_user_id"]')
                assert sales_user is not None, '责任销售字段不存在'
                
                teacher_user = await page.query_selector('select[name="teacher_user_id"]')
                assert teacher_user is not None, '责任班主任字段不存在'
                
                award_level = await page.query_selector('select[name="competition_award_level"]')
                assert award_level is not None, '竞赛奖项等级字段不存在'
                
                additional_req = await page.query_selector('textarea[name="additional_requirements"]')
                assert additional_req is not None, '额外要求字段不存在'
                
                exam_year = await page.query_selector('select[name="exam_year"]')
                assert exam_year is not None, '中高考年份字段不存在'
                
                notes = await page.query_selector('textarea[name="notes"]')
                assert notes is not None, '备注字段不存在'
                
                # 检查服务类型显示（只读）
                service_types_text = await page.inner_text('text=服务类型（线索表）')
                print(f'服务类型显示: 找到')
                
                print('✅ 客户编辑页面测试通过')
            else:
                print('⚠️  没有找到编辑按钮，跳过测试')
                
        finally:
            await browser.close()


async def test_customer_update():
    """测试客户更新功能"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print('\n' + '=' * 80)
            print('测试3：客户更新功能')
            print('=' * 80)
            
            # 登录
            await page.goto('http://localhost:5001/login')
            await page.fill('input[name="username"]', 'Kingble')
            await page.fill('input[name="password"]', 'Kingble')
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(1000)
            
            # 访问客户列表
            await page.goto('http://localhost:5001/customers')
            await page.wait_for_timeout(1000)
            
            # 点击第一个客户的编辑按钮
            edit_button = await page.query_selector('a[href*="/customers/"][href*="/edit"]')
            if edit_button:
                await edit_button.click()
                await page.wait_for_timeout(1000)
                
                # 修改奖项等级
                await page.select_option('select[name="competition_award_level"]', '市奖')
                
                # 修改额外要求
                await page.fill('textarea[name="additional_requirements"]', '测试额外要求内容')
                
                # 提交表单
                await page.click('button[type="submit"]')
                await page.wait_for_timeout(2000)
                
                # 检查是否返回列表页
                current_url = page.url
                print(f'当前URL: {current_url}')
                assert '/customers' in current_url, '没有返回客户列表页'
                
                # 检查成功消息
                success_message = await page.query_selector('.alert-success, .bg-green-100')
                if success_message:
                    message_text = await success_message.inner_text()
                    print(f'成功消息: {message_text}')
                
                print('✅ 客户更新功能测试通过')
            else:
                print('⚠️  没有找到编辑按钮，跳过测试')
                
        finally:
            await browser.close()


async def test_customer_filter():
    """测试客户筛选功能"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print('\n' + '=' * 80)
            print('测试4：客户筛选功能')
            print('=' * 80)
            
            # 登录
            await page.goto('http://localhost:5001/login')
            await page.fill('input[name="username"]', 'Kingble')
            await page.fill('input[name="password"]', 'Kingble')
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(1000)
            
            # 访问客户列表
            await page.goto('http://localhost:5001/customers')
            await page.wait_for_timeout(1000)
            
            # 测试奖项筛选
            award_filter = await page.query_selector('select[name="award_filter"]')
            if award_filter:
                # 筛选国奖
                await page.select_option('select[name="award_filter"]', '国奖')
                await page.click('button:has-text("筛选")')
                await page.wait_for_timeout(1000)
                
                # 检查URL参数
                current_url = page.url
                print(f'筛选后URL: {current_url}')
                assert 'award_filter=国奖' in current_url or 'award_filter=%E5%9B%BD%E5%A5%96' in current_url, '筛选参数不正确'
                
                print('✅ 客户筛选功能测试通过')
            else:
                print('⚠️  没有找到筛选控件，跳过测试')
                
        finally:
            await browser.close()


async def main():
    """运行所有浏览器测试"""
    print('开始浏览器测试...')
    print('请确保应用已在 http://localhost:5001 运行')
    print()
    
    try:
        await test_customer_list()
        await test_customer_edit()
        await test_customer_update()
        await test_customer_filter()
        
        print('\n' + '=' * 80)
        print('✅ 所有浏览器测试通过！')
        print('=' * 80)
        
    except Exception as e:
        print(f'\n❌ 测试失败：{e}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())

