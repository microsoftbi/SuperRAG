# SPRAG UI 自动化测试用例 (Playwright)

## 基本信息

| 项目 | 值 |
|---|---|
| 框架 | Playwright 1.58 + pytest-playwright |
| 目标 | 端到端 UI 验收,覆盖核心交互流程 |
| 范围 | 不依赖 LLM/NL2SQL/Neo4j 的外部服务 |
| Mock 策略 | 用 Playwright route() 拦截 API 返回固定数据 |
| 报告 | pytest-html 或 allure |

---

## 一、测试文件结构

```
TEST/uat/
├── conftest.py              # browser fixture + 登录 fixture
├── pytest.ini               # 配置
├── test_login.py            # 登录/登出/未登录重定向
├── test_documents.py        # 文档上传/查看/删除
├── test_chat_ui.py          # 聊天 Tab/会话管理
├── test_kg_ui.py            # 知识图谱三 Tab/节点关系表格
├── test_chart_ui.py         # 问数 Tab/表格/图表配置面板
└── test_admin.py            # 管理后台 Tab 切换/权限
```

---

## 二、Fixture 设计

```python
# conftest.py

@pytest.fixture
def browser_context(browser):
    """登录后的浏览器上下文,所有测试共享。"""
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        locale="zh-CN",
    )
    page = context.new_page()
    page.goto("http://localhost:5173/login")
    page.fill("[placeholder*='用户名']", "admin")
    page.fill("[placeholder*='密码']", "admin123")
    page.click("button:has-text('登录')")
    page.wait_for_url("**/chat")
    yield context
    context.close()


@pytest.fixture
def admin_page(browser_context):
    """已登录的管理后台页面。"""
    page = browser_context.new_page()
    page.goto("http://localhost:5173/admin")
    page.wait_for_selector("text=仪表盘")
    yield page
    page.close()


@pytest.fixture
def chat_page(browser_context):
    """已登录的聊天页面。"""
    page = browser_context.new_page()
    page.goto("http://localhost:5173/chat")
    page.wait_for_selector("text=RAG")
    yield page
    page.close()
```

---

## 三、测试用例

### 3.1 `test_login.py` — 登录/权限 (4 个用例)

#### TC-LOGIN-01: 正常登录

| 字段 | 值 |
|---|---|
| 步骤 | ①打开登录页 → ②输入 admin/admin123 → ③点登录 |
| 断言 | URL 变为 `/chat`,页面显示"RAG + 图谱"Tab |

#### TC-LOGIN-02: 登录失败

| 字段 | 值 |
|---|---|
| 步骤 | ①打开登录页 → ②输入 admin/错误密码 → ③点登录 |
| 断言 | 页面显示错误提示,URL 仍为 `/login` |

#### TC-LOGIN-03: 未登录重定向

| 字段 | 值 |
|---|---|
| 步骤 | ①清除 localStorage → ②直接访问 `/admin` |
| 断言 | 自动跳转到 `/login` |

#### TC-LOGIN-04: 登出

| 字段 | 值 |
|---|---|
| 步骤 | ①登录 → ②点右上角登出链接 |
| 断言 | 跳转到 `/login`,localStorage 中 token 被清除 |

---

### 3.2 `test_documents.py` — 文档管理 (5 个用例)

#### TC-DOC-01: 上传 .txt 文件

| 字段 | 值 |
|---|---|
| 前置 | 已登录管理员 |
| Mock | 拦截 `/api/v1/documents/upload` → 返回 200 + `{status:"ready"}` |
| 步骤 | ①进入管理后台 → ②切换到文档管理 Tab → ③点文件选择 → ④选择测试 .txt → ⑤点上传 |
| 断言 | 页面显示"上传成功!",文档列表出现新行,状态为"就绪" |

#### TC-DOC-02: 上传不支持的文件类型

| 字段 | 值 |
|---|---|
| 步骤 | ①在文档管理 → ②选择 .exe 文件 → ③点上传 |
| 断言 | 页面显示错误提示"Unsupported file type" |

#### TC-DOC-03: 查看文档分块

| 字段 | 值 |
|---|---|
| 前置 | 已有一个就绪的文档 |
| Mock | 拦截 `/api/v1/documents/{id}/chunks` → 返回 `{chunks:[...]}` |
| 步骤 | ①文档列表 → ②点「查看分块」按钮 |
| 断言 | 弹出分块查看器,显示至少 1 个分块 |

#### TC-DOC-04: 删除文档

| 字段 | 值 |
|---|---|
| 前置 | 已有一个文档 |
| Mock | 拦截 DELETE → 200 |
| 步骤 | ①文档列表 → ②点「删除」→ ③确认对话框点确定 |
| 断言 | 文档从列表中消失 |

#### TC-DOC-05: 按 store 过滤

| 字段 | 值 |
|---|---|
| Mock | 拦截 `/api/v1/documents?store=vector` → 返回 5 条 |
| 步骤 | ①文档列表 → ②点「向量」子 Tab |
| 断言 | 列表仅显示 vector 类型的文档 |

---

### 3.3 `test_chat_ui.py` — 聊天 UI (5 个用例)

#### TC-CHAT-01: RAG / 问数 Tab 切换

| 字段 | 值 |
|---|---|
| 步骤 | ①登录后进入聊天页 → ②默认显示 RAG Tab → ③点「问数」Tab |
| 断言 | RAG Tab: 输入框 placeholder 为"请输入您的问题..." |
| | 问数 Tab: 输入框 placeholder 为"请输入业务数据查询问题..." |

#### TC-CHAT-02: 会话侧边栏显示

| 字段 | 值 |
|---|---|
| Mock | 拦截 `/api/v1/chat/sessions?mode=rag` → 返回 3 条会话 |
| 步骤 | ①进入聊天页 |
| 断言 | 左侧边栏显示 3 条会话,第一条查询文本可见 |

#### TC-CHAT-03: 会话侧边栏删除

| 字段 | 值 |
|---|---|
| 前置 | 侧边栏有至少 1 条会话 |
| Mock | 拦截 DELETE → 200 |
| 步骤 | ①hover 到会话项 → ②点 🗑️ 按钮 → ③确认对话框点确定 |
| 断言 | 该会话从侧边栏消失 |

#### TC-CHAT-04: 会话重命名

| 字段 | 值 |
|---|---|
| 前置 | 侧边栏有至少 1 条会话 |
| Mock | 拦截 PUT → 200 |
| 步骤 | ①hover 到会话项 → ②点 ✏️ 按钮 → ③输入"新名称"→ ④按 Enter |
| 断言 | 侧边栏该会话显示"新名称" |

#### TC-CHAT-05: 新对话按钮

| 字段 | 值 |
|---|---|
| 步骤 | ①侧边栏 → ②点「＋ 新对话」 |
| 断言 | 聊天区域清空,显示空状态提示 |

---

### 3.4 `test_kg_ui.py` — 知识图谱 UI (4 个用例)

#### TC-KG-01: 三 Tab 切换

| 字段 | 值 |
|---|---|
| Mock | 拦截 `/api/v1/knowledge-graph/graph` → `{nodes:[], edges:[]}` |
| 步骤 | ①管理后台 → ②知识图谱 |
| 断言 | 显示三个 Tab:「图谱视图」「节点管理」「关系管理」,默认选中「图谱视图」 |

#### TC-KG-02: 节点管理表格

| 字段 | 值 |
|---|---|
| Mock | 拦截 graph → 返回 5 个节点 + 3 条关系 |
| 步骤 | ①知识图谱 → ②点「节点管理」Tab |
| 断言 | 表格显示 5 行数据,每行有名称/类型/关系数/操作按钮 |

#### TC-KG-03: 节点表格搜索过滤

| 字段 | 值 |
|---|---|
| Mock | 同上(5 个节点) |
| 步骤 | ①节点管理 Tab → ②搜索框输入已有节点名 |
| 断言 | 表格行数减少,仅显示匹配的节点 |

#### TC-KG-04: 关系管理表格

| 字段 | 值 |
|---|---|
| Mock | 拦截 graph → 返回 5 节点 + 3 关系 |
| 步骤 | ①知识图谱 → ②点「关系管理」Tab |
| 断言 | 表格显示 3 行数据,每行有源实体/关系类型/目标实体/操作按钮 |

---

### 3.5 `test_chart_ui.py` — 问数图表 UI (4 个用例)

#### TC-CHART-01: 问数结果表格渲染

| 字段 | 值 |
|---|---|
| Mock | SSE 返回表格数据 + `_meta`(含 total_rows/columns) |
| 步骤 | ①问数 Tab → ②输入查询 → ③发送 |
| 断言 | 消息气泡中渲染表格,表头显示列名,右侧有"共 N 行"计数 |

#### TC-CHART-02: 📊 生成图表按钮

| 字段 | 值 |
|---|---|
| 前置 | 表格已渲染 |
| 步骤 | ①点表格右上角「📊 生成图表」 |
| 断言 | 弹出图表配置面板,显示图表类型选择(柱图/饼图/折线图/...) |

#### TC-CHART-03: 配置面板 → 应用图表

| 字段 | 值 |
|---|---|
| 前置 | 配置面板已打开 |
| 步骤 | ①选「饼图」→ ②确认 X/Y 字段 → ③点「应用」 |
| 断言 | 配置面板关闭,表格下方出现图表渲染区域 |

#### TC-CHART-04: 图表类型切换

| 字段 | 值 |
|---|---|
| 前置 | 图表已渲染 |
| 步骤 | ①图表顶部下拉切换到「折线图」 |
| 断言 | 图表更新为折线图(截图验证) |

---

### 3.6 `test_admin.py` — 管理后台 (2 个用例)

#### TC-ADMIN-01: 管理后台 Tab 切换

| 字段 | 值 |
|---|---|
| 步骤 | ①进入管理后台 → ②依次点击每个 Tab |
| 断言 | 每个 Tab 切换后页面内容相应变化,无 JS 报错 |

#### TC-ADMIN-02: 参数配置保存

| 字段 | 值 |
|---|---|
| Mock | 拦截 GET/PUT `/api/v1/config` |
| 步骤 | ①参数配置 Tab → ②修改「问数最大返回行数」为 200 → ③点「保存配置」 |
| 断言 | 显示"配置已保存"提示 |

---

## 四、Mock API 清单

| API | Mock 策略 |
|---|---|
| `POST /api/v1/auth/login` | 成功 → 返回 token; 失败 → 401 |
| `GET /api/v1/chat/sessions` | 返回预设会话列表 |
| `DELETE /api/v1/chat/sessions/{id}` | 200 |
| `PUT /api/v1/chat/sessions/{id}` | 200 |
| `POST /api/v1/documents/upload` | 200 + `{status:"ready"}` |
| `GET /api/v1/documents` | 返回预设文档列表 |
| `DELETE /api/v1/documents/{id}` | 200 |
| `GET /api/v1/documents/{id}/chunks` | `{chunks:[...]}` |
| `GET /api/v1/knowledge-graph/graph` | `{nodes:[...], edges:[...]}` |
| `POST /api/v1/chat` (SSE) | 返回 mock SSE 流 |
| `GET /api/v1/config` | 返回预设配置 |
| `PUT /api/v1/config` | 200 |

---

## 五、执行方式

```bash
# 安装 playwright 浏览器(首次)
playwright install chromium

# 运行全部 UI 测试(有头模式,可观察)
cd TEST/uat
python3.11 -m pytest --headed --slowmo 300

# 无头模式(CI)
python3.11 -m pytest

# 只跑文档相关
python3.11 -m pytest test_documents.py --headed

# 生成 HTML 报告
python3.11 -m pytest --html=report.html
```

---

## 六、验收标准

- ✅ 24 个用例全部通过
- ✅ 无头模式运行稳定(连续 3 次无 flaky)
- ✅ 每个测试独立,可单独运行
- ✅ 无需外部服务依赖(全 mock)
