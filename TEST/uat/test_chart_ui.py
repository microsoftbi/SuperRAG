"""问数图表 UI 测试。"""
from conftest import do_login, BASE_URL


class TestChartUI:
    def test_ask_number_tab(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/chat")
        page.click("button:has-text('问数')")
        page.wait_for_timeout(300)

    def test_chart_button(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/chat")
        page.click("button:has-text('问数')")
        page.wait_for_timeout(300)
        btn = page.locator("button:has-text('图表')").first
        if btn.is_visible(): btn.click(); page.wait_for_timeout(300)

    def test_chart_type_switch(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/chat")
        page.click("button:has-text('问数')")
        page.wait_for_timeout(300)
        sel = page.locator("select.type-select, .type-select")
        if sel.is_visible(): sel.select_option("line"); page.wait_for_timeout(200)
