"""聊天 UI / 会话管理测试。"""
from conftest import do_login, BASE_URL


class TestChatUI:
    def test_tab_switch(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/chat")
        page.wait_for_selector("text=RAG")
        page.click("button:has-text('问数')")
        page.wait_for_timeout(300)
        ta = page.locator("textarea")
        p = ta.get_attribute("placeholder")
        assert p and "数据" in p

    def test_sidebar_sessions(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/chat")
        page.wait_for_selector("text=历史会话", timeout=3000)
        page.wait_for_selector("text=数据中心建设方案")

    def test_sidebar_delete(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/chat")
        page.wait_for_selector("text=历史会话")
        s = page.locator("text=数据中心建设方案").first
        s.hover(); page.wait_for_timeout(200)
        d = page.locator("button:has-text('🗑')").first
        if d.is_visible():
            page.once("dialog", lambda dlg: dlg.accept())
            d.click(); page.wait_for_timeout(300)

    def test_sidebar_rename(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/chat")
        page.wait_for_selector("text=历史会话")
        s = page.locator("text=数据中心建设方案").first
        s.hover(); page.wait_for_timeout(200)
        r = page.locator("button:has-text('✏')").first
        if r.is_visible():
            r.click(); page.wait_for_timeout(300)
            inp = page.locator(".rename-bar input")
            if inp.is_visible():
                inp.fill("新名称"); inp.press("Enter"); page.wait_for_timeout(300)

    def test_new_chat(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/chat")
        page.wait_for_selector("text=历史会话")
        n = page.locator("button:has-text('新对话')")
        if n.is_visible(): n.click(); page.wait_for_timeout(300)
