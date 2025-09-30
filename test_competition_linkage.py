#!/usr/bin/env python3
"""测试竞赛辅导和奖项等级的联动功能"""

from playwright.sync_api import sync_playwright
import time

def test_competition_linkage():
    """测试竞赛辅导和奖项等级联动"""
    
    with sync_playwright() as p:
        print("=" * 60)
        print("测试竞赛辅导和奖项等级联动功能")
        print("=" * 60)
        
        # 启动浏览器
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # 1. 登录
            print("\n1. 登录系统...")
            page.goto('http://localhost:5001/auth/login')
            page.wait_for_load_state('networkidle')
            page.fill('input[name="phone"]', '13909999451')
            page.click('button[type="submit"]')
            page.wait_for_url('http://localhost:5001/', timeout=10000)
            print("✅ 登录成功")
            
            # 2. 进入线索列表
            print("\n2. 进入线索列表...")
            page.goto('http://localhost:5001/leads')
            page.wait_for_load_state('networkidle')
            print("✅ 进入线索列表")
            
            # 3. 点击编辑测试学员A
            print("\n3. 点击编辑测试学员A...")
            edit_buttons = page.locator('a:has-text("编辑")')
            if edit_buttons.count() > 0:
                edit_buttons.first.click()
                page.wait_for_load_state('networkidle')
                print("✅ 进入编辑页面")
            else:
                print("❌ 未找到编辑按钮")
                return
            
            # 4. 测试联动效果
            print("\n4. 测试联动效果...")
            
            # 4.1 检查初始状态
            print("\n4.1 检查初始状态...")
            competition_checkbox = page.locator('#service_competition')
            award_section = page.locator('#competition_award_level_section')
            
            is_checked = competition_checkbox.is_checked()
            is_visible = award_section.is_visible()
            
            print(f"  竞赛辅导复选框状态: {'选中' if is_checked else '未选中'}")
            print(f"  奖项等级区域可见性: {'可见' if is_visible else '隐藏'}")
            
            if is_checked and is_visible:
                print("  ✅ 初始状态正确：选中竞赛辅导，奖项等级区域可见")
            elif not is_checked and not is_visible:
                print("  ✅ 初始状态正确：未选中竞赛辅导，奖项等级区域隐藏")
            else:
                print("  ⚠️ 初始状态异常")
            
            # 4.2 取消竞赛辅导
            if is_checked:
                print("\n4.2 取消竞赛辅导...")
                competition_checkbox.click()
                time.sleep(0.5)
                
                is_visible_after = award_section.is_visible()
                print(f"  奖项等级区域可见性: {'可见' if is_visible_after else '隐藏'}")
                
                if not is_visible_after:
                    print("  ✅ 联动正确：取消竞赛辅导后，奖项等级区域隐藏")
                else:
                    print("  ❌ 联动失败：取消竞赛辅导后，奖项等级区域仍然可见")
            
            # 4.3 重新选中竞赛辅导
            print("\n4.3 重新选中竞赛辅导...")
            if not competition_checkbox.is_checked():
                competition_checkbox.click()
                time.sleep(0.5)
            
            is_visible_after = award_section.is_visible()
            print(f"  奖项等级区域可见性: {'可见' if is_visible_after else '隐藏'}")
            
            if is_visible_after:
                print("  ✅ 联动正确：选中竞赛辅导后，奖项等级区域显示")
            else:
                print("  ❌ 联动失败：选中竞赛辅导后，奖项等级区域仍然隐藏")
            
            # 4.4 测试表单验证：选中竞赛辅导但不选奖项等级
            print("\n4.4 测试表单验证...")
            
            # 确保竞赛辅导被选中
            if not competition_checkbox.is_checked():
                competition_checkbox.click()
                time.sleep(0.5)
            
            # 清空奖项等级
            award_select = page.locator('#competition_award_level')
            award_select.select_option('')
            
            print("  选中竞赛辅导，但不选择奖项等级")
            
            # 监听弹窗
            page.on('dialog', lambda dialog: dialog.accept())
            
            # 尝试提交表单
            submit_button = page.locator('button[type="submit"]:has-text("保存")')
            submit_button.click()
            time.sleep(1)
            
            # 检查是否还在编辑页面（表单验证失败）
            current_url = page.url
            if '/edit' in current_url:
                print("  ✅ 表单验证正确：阻止了提交")
            else:
                print("  ❌ 表单验证失败：允许了提交")
            
            # 4.5 正确填写并提交
            print("\n4.5 正确填写并提交...")
            
            # 选择奖项等级
            award_select.select_option('国奖')
            print("  已选择奖项等级：国奖")
            
            # 提交表单
            submit_button.click()
            page.wait_for_load_state('networkidle')
            time.sleep(1)
            
            # 检查是否跳转到列表页
            current_url = page.url
            if '/leads' in current_url and '/edit' not in current_url:
                print("  ✅ 提交成功：已跳转到列表页")
            else:
                print("  ❌ 提交失败：仍在编辑页面")
            
            print("\n" + "=" * 60)
            print("✅ 所有测试完成！")
            print("=" * 60)
            
            # 保持浏览器打开5秒
            time.sleep(5)
            
        except Exception as e:
            print(f"\n❌ 测试出错: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            browser.close()

if __name__ == '__main__':
    test_competition_linkage()

