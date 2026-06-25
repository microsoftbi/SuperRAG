"""登录/权限 UI 测试。"""
from conftest import do_login, BASE_URL


class TestLogin:
    def test_login_success(self, page):
        do_login(page)
        assert "/admin" in page.url

    def test_login_failed(self, page):
        page.goto(f"{BASE_URL}/login")
        page.fill("input[placeholder*='用户名']", "admin")
        page.fill("input[placeholder*='密码']", "wrongpass")
        page.click("button:has-text('登录')")
        page.wait_for_timeout(500)
        assert "/login" in page.url

    def test_unauthenticated_redirect(self, page):
        page.goto(f"{BASE_URL}/admin")
        page.wait_for_url("**/login*")
        assert "/login" in page.url

    def test_logout(self, page):
        do_login(page)
        logout_btn = page.locator("button:has-text('退出')").first
        if logout_btn.is_visible():
            logout_btn.click()
            page.wait_for_timeout(1500)
        assert "/login" in page.url
