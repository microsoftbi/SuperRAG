"""管理后台 UI 测试。"""
from conftest import do_login, BASE_URL


class TestAdmin:
    def test_admin_tabs(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/admin")
        page.wait_for_selector("text=仪表盘")
        for tab in ["文档管理", "知识库", "用户管理", "问答日志", "参数配置"]:
            btn = page.locator(f"button:has-text('{tab}')")
            if btn.is_visible(): btn.click(); page.wait_for_timeout(200)

    def test_settings_save(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/admin")
        page.click("button:has-text('参数配置')")
        page.wait_for_timeout(400)
        inp = page.locator("input[type='number']").last
        if inp.is_visible():
            inp.fill("200")
            page.click("button:has-text('保存配置')")
            page.wait_for_selector("text=配置已保存", timeout=3000)
