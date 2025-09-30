#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学员详情弹窗表格布局测试
使用 Playwright 进行无头浏览器测试
"""

import asyncio
from playwright.async_api import async_playwright
import sys

async def test_modal_table_layout():
    """测试学员详情弹窗的表格布局"""
    
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("\n" + "=" * 80)
            print("学员详情弹窗表格布局测试")
            print("=" * 80)
            
            # 1. 访问登录页面
            print("\n步骤1: 访问登录页面...")
            await page.goto('http://localhost:5001/auth/login')
            await page.wait_for_load_state('networkidle')
            print("✅ 登录页面加载成功")
            
            # 2. 登录
            print("\n步骤2: 登录系统...")
            await page.fill('input[name="phone"]', '13909999451')
            await page.click('button[type="submit"]')
            await page.wait_for_url('http://localhost:5001/')
            print("✅ 登录成功")
            
            # 3. 进入线索列表
            print("\n步骤3: 进入线索列表...")
            await page.goto('http://localhost:5001/leads/list')
            await page.wait_for_load_state('networkidle')
            print("✅ 线索列表加载成功")
            
            # 4. 点击第一个学员姓名打开弹窗
            print("\n步骤4: 点击学员姓名打开详情弹窗...")
            student_link = page.locator('a.text-blue-600.hover\\:text-blue-800').first
            await student_link.click()
            
            # 等待弹窗出现
            await page.wait_for_selector('#studentDetailModal:not(.hidden)', timeout=5000)
            print("✅ 学员详情弹窗已打开")
            
            # 5. 检查基本信息表格
            print("\n步骤5: 检查基本信息表格...")
            
            # 检查表格是否存在
            basic_info_table = page.locator('#studentDetailContent table').first
            is_visible = await basic_info_table.is_visible()
            
            if is_visible:
                print("✅ 基本信息表格存在")
                
                # 检查表格行数
                rows = basic_info_table.locator('tbody tr')
                row_count = await rows.count()
                print(f"✅ 基本信息表格有 {row_count} 行")
                
                # 检查每一行的内容
                for i in range(row_count):
                    row = rows.nth(i)
                    label = await row.locator('td').first.inner_text()
                    value = await row.locator('td').last.inner_text()
                    print(f"   - {label}: {value}")
                
            else:
                print("❌ 基本信息表格不可见")
                return False
            
            # 6. 检查服务内容表格
            print("\n步骤6: 检查服务内容表格...")
            
            # 检查服务内容区域是否显示
            service_content = page.locator('#serviceContent')
            is_service_visible = await service_content.is_visible()
            
            if is_service_visible:
                print("✅ 服务内容区域显示")
                
                # 检查服务内容表格
                service_table = service_content.locator('table')
                is_table_visible = await service_table.is_visible()
                
                if is_table_visible:
                    print("✅ 服务内容表格存在")
                    
                    # 检查表格行数
                    service_rows = service_table.locator('tbody tr')
                    service_row_count = await service_rows.count()
                    print(f"✅ 服务内容表格有 {service_row_count} 行")
                    
                    # 检查每一行的内容
                    for i in range(service_row_count):
                        row = service_rows.nth(i)
                        label_cell = row.locator('td').first
                        value_cell = row.locator('td').last
                        
                        # 获取图标和文本
                        icon = await label_cell.locator('span.material-symbols-outlined').inner_text()
                        label = await label_cell.locator('span').last.inner_text()
                        value = await value_cell.inner_text()
                        
                        print(f"   - {label}: {value}")
                else:
                    print("❌ 服务内容表格不可见")
                    return False
            else:
                print("⚠️  服务内容区域未显示（可能该学员没有服务内容）")
            
            # 7. 截图
            print("\n步骤7: 截图保存...")
            await page.screenshot(path='modal_table_layout.png', full_page=True)
            print("✅ 截图已保存: modal_table_layout.png")
            
            # 8. 关闭弹窗
            print("\n步骤8: 关闭弹窗...")
            close_button = page.locator('button[onclick="closeStudentDetailModal()"]')
            await close_button.click()
            await page.wait_for_selector('#studentDetailModal.hidden', timeout=2000)
            print("✅ 弹窗已关闭")
            
            print("\n" + "=" * 80)
            print("🎉 所有测试通过！")
            print("=" * 80)
            
            return True
            
        except Exception as e:
            print(f"\n❌ 测试失败: {str(e)}")
            
            # 错误时截图
            try:
                await page.screenshot(path='modal_error.png', full_page=True)
                print("错误截图已保存: modal_error.png")
            except:
                pass
            
            return False
            
        finally:
            await browser.close()

async def test_customer_modal():
    """测试客户详情弹窗的表格布局"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("\n" + "=" * 80)
            print("客户详情弹窗表格布局测试")
            print("=" * 80)
            
            # 1. 登录
            print("\n步骤1: 登录系统...")
            await page.goto('http://localhost:5001/auth/login')
            await page.wait_for_load_state('networkidle')
            await page.fill('input[name="phone"]', '13909999451')
            await page.click('button[type="submit"]')
            await page.wait_for_url('http://localhost:5001/')
            print("✅ 登录成功")
            
            # 2. 进入客户列表
            print("\n步骤2: 进入客户列表...")
            await page.goto('http://localhost:5001/customers/list')
            await page.wait_for_load_state('networkidle')
            print("✅ 客户列表加载成功")
            
            # 3. 点击第一个学员姓名打开弹窗
            print("\n步骤3: 点击学员姓名打开详情弹窗...")
            student_link = page.locator('a.text-blue-600.hover\\:text-blue-800').first
            await student_link.click()
            
            # 等待弹窗出现
            await page.wait_for_selector('#studentDetailModal:not(.hidden)', timeout=5000)
            print("✅ 客户详情弹窗已打开")
            
            # 4. 检查服务内容表格（客户应该有更多信息）
            print("\n步骤4: 检查服务内容表格...")
            
            service_content = page.locator('#serviceContent')
            is_service_visible = await service_content.is_visible()
            
            if is_service_visible:
                print("✅ 服务内容区域显示")
                
                service_table = service_content.locator('table')
                service_rows = service_table.locator('tbody tr')
                service_row_count = await service_rows.count()
                print(f"✅ 服务内容表格有 {service_row_count} 行")
                
                # 检查每一行的内容
                for i in range(service_row_count):
                    row = service_rows.nth(i)
                    label = await row.locator('td').first.locator('span').last.inner_text()
                    value = await row.locator('td').last.inner_text()
                    print(f"   - {label}: {value}")
            
            # 5. 截图
            print("\n步骤5: 截图保存...")
            await page.screenshot(path='customer_modal_table_layout.png', full_page=True)
            print("✅ 截图已保存: customer_modal_table_layout.png")
            
            print("\n" + "=" * 80)
            print("🎉 客户弹窗测试通过！")
            print("=" * 80)
            
            return True
            
        except Exception as e:
            print(f"\n❌ 测试失败: {str(e)}")
            return False
            
        finally:
            await browser.close()

async def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("开始测试学员详情弹窗表格布局")
    print("=" * 80)
    
    # 测试线索弹窗
    result1 = await test_modal_table_layout()
    
    # 测试客户弹窗
    result2 = await test_customer_modal()
    
    if result1 and result2:
        print("\n" + "=" * 80)
        print("🎉 所有测试通过！")
        print("=" * 80)
        return 0
    else:
        print("\n" + "=" * 80)
        print("❌ 部分测试失败")
        print("=" * 80)
        return 1

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

