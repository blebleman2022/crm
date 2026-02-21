def test_login_page_loads(page, e2e_env):
    base_url = e2e_env["base_url"]
    page.goto(f"{base_url}/auth/login", wait_until="domcontentloaded")

    page.locator("input#phone").wait_for(timeout=5000)
    page.locator("input#password").wait_for(timeout=5000)
    page.locator("form button[type='submit']").wait_for(timeout=5000)
    assert "EduConnect" in page.title()
