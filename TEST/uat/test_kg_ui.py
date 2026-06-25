"""知识图谱 UI 测试。"""
from conftest import do_login, BASE_URL


class TestKgUI:
    def test_three_tabs(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/admin")
        page.click("button:has-text('知识图谱')")
        page.wait_for_selector("text=全局知识图谱", timeout=3000)
        assert page.locator("button:has-text('图谱视图')").is_visible()
        assert page.locator("button:has-text('节点管理')").is_visible()
        assert page.locator("button:has-text('关系管理')").is_visible()

    def test_node_table(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/admin")
        page.click("button:has-text('知识图谱')")
        page.wait_for_selector("text=全局知识图谱")
        page.click("button:has-text('节点管理')")
        page.wait_for_timeout(500)
        page.wait_for_selector("text=张三")
        page.wait_for_selector("text=公司A")

    def test_node_search(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/admin")
        page.click("button:has-text('知识图谱')")
        page.wait_for_selector("text=全局知识图谱")
        page.click("button:has-text('节点管理')")
        page.wait_for_timeout(300)
        page.locator("input[placeholder*='按名称']").first.fill("张")
        page.wait_for_timeout(500)
        assert page.locator("text=张三").is_visible()

    def test_edge_table(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/admin")
        page.click("button:has-text('知识图谱')")
        page.wait_for_selector("text=全局知识图谱")
        page.click("button:has-text('关系管理')")
        page.wait_for_timeout(500)
        page.wait_for_selector("text=任职于")
