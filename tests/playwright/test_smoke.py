import os

def test_login_page_loads(page):
    base_url = os.getenv("BASE_URL", "http://localhost:5002")
    page.goto(f"{base_url}/auth/login", wait_until="domcontentloaded")

    # 页面基础元素校验
    page.locator("input#phone").wait_for(timeout=5000)
    page.locator("form button[type='submit']").wait_for(timeout=5000)
    assert "EduConnect" in page.title()
