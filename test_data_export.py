#!/usr/bin/env python3
"""
数据下载功能 Playwright 自动化测试
测试销售管理角色是否能看到并使用数据下载功能
"""

from playwright.sync_api import sync_playwright, expect
import time

def test_data_export_feature():
    """测试数据下载功能"""
    
    with sync_playwright() as p:
        # 启动浏览器（无头模式）
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        print("=" * 60)
        print("开始测试数据下载功能")
        print("=" * 60)
        
        try:
            # 1. 访问登录页面
            print("\n[步骤 1] 访问登录页面...")
            page.goto("http://127.0.0.1:5001/auth/login")
            page.wait_for_load_state("networkidle")
            print("✅ 登录页面加载成功")
            
            # 2. 使用销售管理账号登录
            print("\n[步骤 2] 使用 Kingble (销售管理) 账号登录...")
            page.fill('input[name="phone"]', "13909999451")
            page.fill('input[name="password"]', "123456")
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            print("✅ 登录成功")
            
            # 3. 检查是否跳转到仪表板
            print("\n[步骤 3] 检查是否跳转到仪表板...")
            current_url = page.url
            assert "/dashboard" in current_url or "/leads" in current_url, f"未跳转到仪表板，当前URL: {current_url}"
            print(f"✅ 已跳转到仪表板: {current_url}")
            
            # 4. 检查侧边栏是否有"数据下载"菜单
            print("\n[步骤 4] 检查侧边栏是否有'数据下载'菜单...")
            
            # 等待侧边栏加载
            page.wait_for_selector("nav", timeout=5000)
            
            # 查找"数据下载"链接
            data_export_link = page.locator('a:has-text("数据下载")')
            
            # 检查是否存在
            count = data_export_link.count()
            assert count > 0, "侧边栏中未找到'数据下载'菜单项"
            print(f"✅ 找到'数据下载'菜单项（共{count}个）")
            
            # 5. 点击"数据下载"菜单
            print("\n[步骤 5] 点击'数据下载'菜单...")
            data_export_link.first.click()
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            print("✅ 已点击'数据下载'菜单")
            
            # 6. 检查是否跳转到数据下载页面
            print("\n[步骤 6] 检查是否跳转到数据下载页面...")
            current_url = page.url
            assert "/data_export/export" in current_url, f"未跳转到数据下载页面，当前URL: {current_url}"
            print(f"✅ 已跳转到数据下载页面: {current_url}")
            
            # 7. 检查页面标题
            print("\n[步骤 7] 检查页面标题...")
            page_title = page.locator("h1").first.text_content()
            assert "数据下载" in page_title, f"页面标题不正确: {page_title}"
            print(f"✅ 页面标题正确: {page_title}")
            
            # 8. 检查是否有表格卡片
            print("\n[步骤 8] 检查是否有数据表卡片...")
            table_cards = page.locator(".table-card")
            card_count = table_cards.count()
            assert card_count > 0, "未找到任何数据表卡片"
            print(f"✅ 找到 {card_count} 个数据表卡片")
            
            # 9. 检查是否有复选框
            print("\n[步骤 9] 检查是否有复选框...")
            checkboxes = page.locator('input[type="checkbox"].table-checkbox')
            checkbox_count = checkboxes.count()
            assert checkbox_count > 0, "未找到任何复选框"
            print(f"✅ 找到 {checkbox_count} 个复选框")
            
            # 10. 测试全选功能
            print("\n[步骤 10] 测试全选功能...")
            select_all_btn = page.locator("#selectAllBtn")
            select_all_btn.click()
            time.sleep(1)
            
            # 检查所有复选框是否被选中
            checked_count = page.locator('input[type="checkbox"].table-checkbox:checked').count()
            assert checked_count == checkbox_count, f"全选失败，只选中了 {checked_count}/{checkbox_count} 个"
            print(f"✅ 全选成功，已选中 {checked_count} 个表")
            
            # 11. 检查已选择提示是否显示
            print("\n[步骤 11] 检查已选择提示...")
            selected_info = page.locator("#selectedInfo")
            assert selected_info.is_visible(), "已选择提示未显示"
            selected_count_text = page.locator("#selectedCount").text_content()
            print(f"✅ 已选择提示显示正确: 已选择 {selected_count_text} 个表")
            
            # 12. 测试取消全选功能
            print("\n[步骤 12] 测试取消全选功能...")
            deselect_all_btn = page.locator("#deselectAllBtn")
            deselect_all_btn.click()
            time.sleep(1)
            
            checked_count = page.locator('input[type="checkbox"].table-checkbox:checked').count()
            assert checked_count == 0, f"取消全选失败，还有 {checked_count} 个被选中"
            print("✅ 取消全选成功")
            
            # 13. 测试单选功能
            print("\n[步骤 13] 测试单选功能...")
            first_checkbox = checkboxes.first
            first_checkbox.check()
            time.sleep(1)
            
            checked_count = page.locator('input[type="checkbox"].table-checkbox:checked').count()
            assert checked_count == 1, f"单选失败，选中了 {checked_count} 个"
            print("✅ 单选功能正常")
            
            # 14. 测试预览功能
            print("\n[步骤 14] 测试预览功能...")
            preview_btn = page.locator(".preview-btn").first
            preview_btn.click()
            time.sleep(2)
            
            # 检查预览模态框是否显示
            preview_modal = page.locator("#previewModal")
            assert preview_modal.is_visible(), "预览模态框未显示"
            print("✅ 预览模态框显示成功")
            
            # 检查预览内容
            preview_content = page.locator("#previewContent")
            assert preview_content.is_visible(), "预览内容未显示"
            print("✅ 预览内容加载成功")
            
            # 关闭预览模态框
            close_btn = page.locator("#closePreviewBtn")
            close_btn.click()
            time.sleep(1)
            print("✅ 预览模态框关闭成功")
            
            # 15. 测试下载功能（不实际下载，只检查按钮状态）
            print("\n[步骤 15] 测试下载按钮状态...")
            download_btn = page.locator("#downloadBtn")
            
            # 未选择时应该禁用
            deselect_all_btn.click()
            time.sleep(0.5)
            assert download_btn.is_disabled(), "未选择表时下载按钮应该被禁用"
            print("✅ 未选择时下载按钮正确禁用")
            
            # 选择后应该启用
            first_checkbox.check()
            time.sleep(0.5)
            assert not download_btn.is_disabled(), "选择表后下载按钮应该启用"
            print("✅ 选择后下载按钮正确启用")
            
            # 16. 截图保存
            print("\n[步骤 16] 保存测试截图...")
            page.screenshot(path="test_data_export_screenshot.png", full_page=True)
            print("✅ 截图已保存到: test_data_export_screenshot.png")
            
            print("\n" + "=" * 60)
            print("✅ 所有测试通过！数据下载功能正常工作")
            print("=" * 60)
            
            return True
            
        except AssertionError as e:
            print(f"\n❌ 测试失败: {e}")
            # 保存失败时的截图
            page.screenshot(path="test_data_export_failed.png", full_page=True)
            print("失败截图已保存到: test_data_export_failed.png")
            return False
            
        except Exception as e:
            print(f"\n❌ 测试出错: {e}")
            # 保存错误时的截图
            page.screenshot(path="test_data_export_error.png", full_page=True)
            print("错误截图已保存到: test_data_export_error.png")
            return False
            
        finally:
            # 关闭浏览器
            browser.close()


if __name__ == "__main__":
    success = test_data_export_feature()
    exit(0 if success else 1)

