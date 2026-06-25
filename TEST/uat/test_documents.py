"""文档管理 UI 测试。"""
import os
import tempfile
from conftest import do_login, BASE_URL


class TestDocuments:
    def test_upload_txt(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/admin")
        page.click("button:has-text('文档管理')")
        page.wait_for_selector("text=上传文档")
        f = tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8")
        f.write("数据中心建设方案包括服务器硬件配置和网络设备。"); f.flush()
        try:
            page.locator("input[type='file']").set_input_files(f.name)
            page.click("button:has-text('上传')")
            page.wait_for_selector("text=上传成功", timeout=5000)
        finally:
            os.unlink(f.name)

    def test_upload_unsupported_type(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/admin")
        page.click("button:has-text('文档管理')")
        f = tempfile.NamedTemporaryFile(suffix=".exe", mode="w", delete=False)
        f.write("fake"); f.flush()
        try:
            page.locator("input[type='file']").set_input_files(f.name)
            page.click("button:has-text('上传')")
            page.wait_for_timeout(500)
        finally:
            os.unlink(f.name)

    def test_view_chunks(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/admin")
        page.click("button:has-text('文档管理')")
        btn = page.locator("button:has-text('查看分块')").first
        if btn.is_visible(): btn.click(); page.wait_for_timeout(300)

    def test_delete_document(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/admin")
        page.click("button:has-text('文档管理')")
        btn = page.locator("button:has-text('删除')").first
        if btn.is_visible():
            page.once("dialog", lambda d: d.accept())
            btn.click(); page.wait_for_timeout(300)

    def test_store_filter(self, page):
        do_login(page)
        page.goto(f"{BASE_URL}/admin")
        page.click("button:has-text('文档管理')")
        tab = page.locator("button:has-text('向量')")
        if tab.is_visible(): tab.click(); page.wait_for_timeout(200)
