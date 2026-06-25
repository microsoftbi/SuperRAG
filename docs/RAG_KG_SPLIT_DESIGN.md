# RAG / 图谱 拆分方案

## 一、现状

当前 `RAG + 图谱` 是一个 Tab,背后只有一个 deepagent 实例,同时拥有 `search_knowledge_base` 和 `search_knowledge_graph` 两个工具。

```
ChatView
├── RAG + 图谱  (agent: 两个工具都有)
├── 问数        (nl2sql_agent)
└── 会话侧边栏  (按 mode 过滤)
```

## 二、目标

拆成三个 Tab,各走独立 agent:

```
ChatView
├── RAG         (rag_agent: 只有 search_knowledge_base)
├── 图谱        (kg_agent: 只有 search_knowledge_graph)
├── 问数        (nl2sql_agent)
└── 会话侧边栏  (按 mode 过滤)
```

## 三、改动点

### 3.1 后端

#### agent_factory.py

新增 `init_kg_agent()` + `_kg_agent`:

```python
# 新增
_rag_agent = None
_kg_agent = None

# 改：原有 init_agent 拆为 init_rag_agent / init_kg_agent
# RAG agent: 只带 search_knowledge_base
# KG agent: 只带 search_knowledge_graph
```

各自独立 `AsyncSqliteSaver` checkpointer,thread_id 前缀区分:
- RAG: `u{user.id}_{session_id}`
- KG: `kg_u{user.id}_{session_id}`
- NL2SQL: `nl2sql_u{user.id}_{session_id}`

#### tools.py

`build_tools()` 改为可分别构建:

```python
def build_rag_tools(rag_retriever):
    """只包含 search_knowledge_base"""

def build_kg_tools(graph_retriever):
    """只包含 search_knowledge_graph"""
```

#### chat.py

`ChatRequest.mode` 支持三种值:

```python
if mode == "rag":
    # 用 rag_agent
elif mode == "kg":
    # 用 kg_agent
elif mode == "nl2sql":
    # 用 nl2sql_agent
```

流结束后 sources 生成:
- RAG: 只跑向量检索
- KG: 只跑图检索

#### main.py

```python
# 初始化 RAG agent
await init_rag_agent(rag_retriever)

# 初始化 KG agent（需要 Neo4j）
if neo4j_ok:
    await init_kg_agent(graph_retriever)
```

### 3.2 前端

#### ChatView.vue

```html
<nav class="mode-tabs">
  <button @click="chatMode = 'rag'">RAG</button>
  <button @click="chatMode = 'kg'">图谱</button>
  <button @click="chatMode = 'nl2sql'">问数</button>
</nav>
<div class="chat-body">
  <SessionSidebar ... />
  <ChatWindow v-if="chatMode === 'rag'" mode="rag" ... />
  <ChatWindow v-if="chatMode === 'kg'" mode="kg" ... />
  <Nl2SqlChat v-if="chatMode === 'nl2sql'" ... />
</div>
```

每个 mode 独立 session ID:
- RAG: `chat_session_id`
- KG: `kg_session_id`
- NL2SQL: `nl2sql_session_id`

#### ChatWindow.vue

接受 `mode` prop,传给 API:

```js
sendChatMessage(props.sessionKey, query, props.mode)
getChatHistory(props.sessionKey, props.mode)
```

#### api/index.js

`sendChatMessage` / `getChatHistory` 已支持 mode 参数,无需改动。

## 四、改动文件清单

| 文件 | 改动 |
|---|---|
| `backend/app/agents/agent_factory.py` | 拆分 RAG/KG agent 初始化 |
| `backend/app/agents/tools.py` | `build_rag_tools` / `build_kg_tools` |
| `backend/app/api/chat.py` | 三路 mode 分发 |
| `backend/app/main.py` | 分别初始化 RAG/KG agent |
| `frontend/src/views/ChatView.vue` | 三 Tab + 三个 session ID |
| `frontend/src/components/chat/ChatWindow.vue` | 接受 mode prop |

## 五、待确认

1. **Tab 名称**: 是否用 `RAG` / `图谱` / `问数`？还是 `知识库` / `知识图谱` / `问数`？
2. **会话侧边栏**: 按 mode 过滤(RAG 只显示 RAG 会话),你之前已经做了这个逻辑,确认保持即可
3. **KG 不可用时**: 如果 Neo4j 没启动,图谱 Tab 是否隐藏还是显示"未配置"提示？
