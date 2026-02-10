import re

from playwright.sync_api import expect


def _login(page, base_url, phone):
    page.goto(f"{base_url}/auth/login", wait_until="domcontentloaded")
    page.fill("input#phone", phone)
    page.click("form button[type='submit']")
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(re.compile(r"^(?!.*?/auth/login).*$"))
    expect(page.locator("a[href='/auth/logout']")).to_be_visible()


def _body_text(page):
    return page.locator("body").inner_text(timeout=5000)


def test_private_manager_can_only_see_private_scope(page, e2e_env):
    base_url = e2e_env["base_url"]
    phones = e2e_env["phones"]
    students = e2e_env["students"]

    _login(page, base_url, phones["private_manager"])

    expect(page.get_by_role("link", name="私域客户")).to_have_count(0)
    expect(page.get_by_role("link", name="头脑风暴")).to_be_visible()

    page.goto(f"{base_url}/customers/list?search=PWTEST", wait_until="networkidle")
    body = _body_text(page)
    assert page.locator('select[name="scope"]').count() == 0
    assert "当前为私域视图" not in body
    assert students["private"] in body
    assert students["public"] not in body

    page.goto(f"{base_url}/leads/brainstorm?search=PWTEST", wait_until="networkidle")
    body = _body_text(page)
    assert students["private"] in body
    assert students["public"] not in body

    page.goto(f"{base_url}/payments/reconciliation", wait_until="networkidle")
    body = _body_text(page)
    assert "私域对账" in body
    assert "公域对账" not in body


def test_public_manager_cannot_view_private_scope(page, e2e_env):
    base_url = e2e_env["base_url"]
    phones = e2e_env["phones"]
    students = e2e_env["students"]
    customers = e2e_env["customers"]

    _login(page, base_url, phones["public_manager"])

    expect(page.get_by_role("link", name="私域客户")).to_have_count(0)

    page.goto(f"{base_url}/customers/list?scope=private&search=PWTEST", wait_until="networkidle")
    body = _body_text(page)
    assert page.locator('select[name="scope"]').count() == 0
    assert "当前为公域视图" not in body
    assert students["public"] in body
    assert students["private"] not in body

    private_customer_id = customers["private_customer_id"]
    page.goto(f"{base_url}/customers/{private_customer_id}/detail", wait_until="networkidle")
    body = _body_text(page)
    assert "您没有权限查看此客户" in body
    assert students["private"] not in body

    page.goto(f"{base_url}/payments/reconciliation?search=PWTEST", wait_until="networkidle")
    body = _body_text(page)
    assert "公域对账" in body
    assert "私域对账" not in body
    assert students["public"] in body
    assert students["private"] not in body


def test_teacher_supervisor_can_switch_public_and_private_scope(page, e2e_env):
    base_url = e2e_env["base_url"]
    phones = e2e_env["phones"]
    students = e2e_env["students"]

    _login(page, base_url, phones["teacher_supervisor"])

    expect(page.get_by_role("link", name="私域客户")).to_be_visible()

    page.goto(f"{base_url}/customers/list?scope=private&search=PWTEST", wait_until="networkidle")
    body = _body_text(page)
    assert students["private"] in body
    assert students["public"] not in body

    page.goto(f"{base_url}/customers/list?scope=public&search=PWTEST", wait_until="networkidle")
    body = _body_text(page)
    assert students["public"] in body
    assert students["private"] not in body

    page.goto(f"{base_url}/payments/reconciliation", wait_until="networkidle")
    expect(page.get_by_role("link", name="公域对账")).to_be_visible()
    expect(page.get_by_role("link", name="私域对账")).to_be_visible()
