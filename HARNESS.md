# SuperRAG 开发工作指南

> 开发者日常工作流、代码规范、调试技巧

---

## 1. 项目总览

| 属性 | 内容 |
|------|------|
| 项目名 | SuperRAG — Smart Product RAG |
| 后端框架 | Python FastAPI + SQLAlchemy 2.0 |
| 前端框架 | Vue 3 (Composition API) + Vite 5 |
| LLM | 火山引擎 API（OpenAI 兼容） |
| 向量库 | Milvus Lite（稠密+稀疏双向量） |
| 图谱库 | Neo4j |
| 数据库 | SQLite |
| Agent 框架 | deepagents v0.5+（三 Agent：RAG/KG/NL2SQL） |

---

## 2. 启动与运行

### 2.1 首次启动

```bash
# 后端
cd backend
pip install -r requirements.txt
cp .env.example .env              # 编辑 .env 填入密钥
python run.py                      # http://localhost:8000

# 前端
cd frontend
npm install
npm run dev                        # http://localhost:5173

# Neo4j（图谱引擎，可选）
brew services start neo4j          # http://localhost:7474
```

### 2.2 日常启动（开发）

```bash
# 终端 1
cd backend && python run.py        # 自动 reload

# 终端 2
cd frontend && npm run dev

# 终端 3（需要图谱功能时）
brew services start neo4j
```

### 2.3 默认管理员

```
用户名: admin
密码:   admin123
```

---

## 3. 项目目录结构

```
backend/
├── app/
│   ├── main.py                 # FastAPI 入口 + lifespan + 三 Agent 初始化
│   ├── config.py               # Pydantic Settings（.env, Milvus Lite）
│   ├── database.py             # SQLAlchemy engine + 自动迁移
│   ├── models/                 # ORM 模型（含 conversation_log 扩展字段）
│   ├── schemas/                # Pydantic 响应模型
│   ├── api/                    # API 路由（13 个文件）
│   │   ├── chat.py             # SSE 流式问答（三模式分发 RAG/KG/NL2SQL）
│   │   ├── documents.py        # 文档上传/列表/删除 + KG 处理
│   │   ├── knowledge_graph.py  # 图谱管理 API（含 Node/Edge CRUD）
│   │   ├── knowledge_bases.py  # 知识库 CRUD
│   │   ├── nl2sql.py           # NL2SQL 配置 API
│   │   └── ...
│   ├── agents/                 # deepagents 集成
│   │   ├── agent_factory.py    # 三 Agent 工厂（RAG/KG/NL2SQL，独立 checkpointer）
│   │   └── tools.py            # 工具函数（RAG/KG/NL2SQL 三组独立 tools）
│   ├── rag/                    # RAG 引擎（与 kg 完全独立）
│   │   ├── retriever.py        # 检索编排
│   │   ├── generator.py        # RAG 系统 Prompt + 流式
│   │   ├── query_rewriter.py   # LLM 代词改写
│   │   ├── hybrid_retriever.py # RRF 融合
│   │   ├── reranker.py         # LLM 批量重排序
│   │   ├── bm25_retriever.py   # BM25EmbeddingFunction(language="zh")
│   │   └── document_processor.py # 文本提取 + 分块
│   ├── kg/                     # 知识图谱引擎（与 rag 完全独立）
│   │   ├── entity_extractor.py # LLM 实体提取
│   │   └── graph_retriever.py  # 图遍历检索（仅返回关系文本）
│   └── services/               # 基础设施
│       ├── llm_service.py      # 火山引擎 API 封装
│       ├── neo4j_service.py    # Neo4j 连接/Cypher（含节点维护方法）
│       ├── vector_store.py     # Milvus Lite 封装（稠密+稀疏双向量）
│       ├── auth_service.py     # JWT + bcrypt
│       ├── runtime_config.py   # 运行时参数持久化（含 nl2sql_max_rows）
│       └── nl2sql_config.py    # NL2SQL 连接和提示词配置
├── uploads/                    # 上传文档原件
├── milvus_lite.db              # Milvus Lite 数据文件
├── sprag.db                    # SQLite 数据库
└── runtime_config.json         # 运行时配置

frontend/
├── src/
│   ├── main.js                 # Vue 入口
│   ├── router/index.js         # 路由（/ /admin /login /register）
│   ├── api/index.js            # Axios API 客户端
│   ├── views/                  # 4 个页面
│   │   ├── ChatView.vue        # 三 Tab 对话页
│   │   ├── AdminView.vue       # 管理后台（9 个 Tab）
│   │   ├── LoginView.vue
│   │   └── RegisterView.vue
│   └── components/
│       ├── admin/              # 管理后台组件
│       │   ├── KnowledgeGraphViewer.vue  # vis-network 全景图（3 子 Tab）
│       │   ├── KgNodeTable.vue           # 节点维护
│       │   ├── KgEdgeTable.vue           # 关系维护
│       │   ├── SettingsPanel.vue         # 参数配置（含 nl2sql_max_rows）
│       │   └── ...
│       └── chat/               # 对话组件
│           ├── ChatWindow.vue            # RAG/KG 聊天窗
│           ├── Nl2SqlChat.vue            # 问数聊天窗（含 ECharts）
│           ├── MessageBubble.vue         # 消息气泡（含结果表格 + 图表）
│           ├── SessionSidebar.vue        # 会话侧边栏
│           └── MiniGraphModal.vue        # vis-network 弹窗
```

---

## 4. 核心开发规范

### 4.1 代码分离原则

```
rag/  ←→  kg/   ←→  services/
  │         │            │
  │         │            └─ 基础设施（不归任一方）
  │         │
  │         └──────── 完全独立，不引用 rag/ 的任何代码
  │
  └─ 完全独立，不引用 kg/ 的任何代码

交汇点只有 api/ 层的调度函数：
  api/chat.py       → 调用 graph_retriever + agents
  api/documents.py  → 调用 entity_extractor + neo4j_service
  api/knowledge_graph.py → 调用 neo4j_service + entity_extractor
```

### 4.2 三 Agent 架构原则

```
┌──────────────────────────────────────────────┐
│            api/chat.py (三路分发)              │
│  mode=rag  → get_rag_agent()  → thread: rag_  │
│  mode=kg   → get_kg_agent()   → thread: kg_   │
│  mode=nl2sql→ get_nl2sql_agent()→ thread:nl2sql│
└──────────────────────────────────────────────┘

每个 Agent 有独立的：
- tools（只有自己需要的工具）
- system prompt
- checkpointer（SQLite checkpoints）
- 会话 ID 前缀（session_ / kg_ / nl2sql_）
```

### 4.3 新增一个 API 路由的步骤

1. 在 `api/` 下创建 `.py` 文件，定义 `router = APIRouter(prefix=...)`
2. 在 `main.py` 添加 `app.include_router(router, prefix="/api/v1")`
3. 前端 `api/index.js` 添加对应的 Axios 函数
4. 前端组件调用 API 函数

### 4.4 新增一个模型字段的步骤

1. 修改 `models/` 中对应的 ORM 类
2. 修改 `schemas/` 中对应的 Pydantic 模型
3. 在 `database.py` 的 `_run_migrations()` 添加 ALTER TABLE 语句
4. 重启后端触发迁移

### 4.5 SSE 流式协议

```python
# 后端写法
def stream():
    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
    yield f"data: {json.dumps({'type': 'sources', 'sources': [...]})}\n\n"
    yield "data: [DONE]\n\n"
return StreamingResponse(stream(), media_type="text/event-stream")
```

```javascript
// 前端消费
const response = await sendChatMessage(sessionId, query, mode)
const reader = response.body.getReader()
// 逐行解析 SSE
```

### 4.6 API mode 参数约定

所有对话相关 API 接受 `mode` 参数，取值范围：

| mode | 含义 | route 日志值 | 会话 ID 前缀 |
|------|------|-------------|-------------|
| `rag` | 文档问答 | AGENT | `session_` |
| `kg` | 知识图谱 | KG | `kg_` |
| `nl2sql` | 问数 | NL2SQL | `nl2sql_` |

---

## 5. 知识图谱（KG）开发说明

### 5.1 Neo4j 环境

```bash
# 安装
brew install neo4j

# 启动/停止/状态
brew services start neo4j
brew services stop neo4j
brew services list | grep neo4j

# Web 管理界面
open http://localhost:7474

# 默认连接
bolt://localhost:7687 | neo4j / neo4j
```

### 5.2 实体提取链路

```
上传 (store=graph) → documents.py → entity_extractor.py
                                     ↓
                               LLM 提取实体/关系
                                     ↓
                               neo4j_service.import_extraction()
                                     ↓
                               MERGE Entity {name, type, chunk_ids}
                               MERGE (a)-[:REL]->(b)
```

### 5.3 图谱检索链路

```
用户问题
    ↓
graph_retriever.retrieve(query)
    ├─ neo4j.find_seed_entities(query)    ← $query CONTAINS e.name
    ├─ neo4j.bfs_traverse_1hop(names)    ← (e)-[r]-(neighbor)
    ├─ neo4j.bfs_traverse(names, depth)   ← (e)-[*1..depth]-(connected)
    ├─ 构建关系文本
    └─ 返回 (empty_list, formatted_kg_text, cypher_text)
                                  ↑
                          contexts 已移除（不再查 SQLite chunk 原文）
    ↓
Agent 基于关系文本生成回答
```

### 5.4 Cypher 查询模式

```cypher
// 种子匹配（无标签限制）
MATCH (e) WHERE $search_text CONTAINS e.name RETURN e

// 1跳遍历（无向）
MATCH (e) WHERE e.name IN $names OPTIONAL MATCH (e)-[r]-(n) RETURN e, r, n

// 多跳遍历
MATCH (e) WHERE e.name IN $names OPTIONAL MATCH (e)-[*1..d]-(n) RETURN DISTINCT n

// 写实体（MERGE 避免重复）
MERGE (e:Entity {name: $name})
ON CREATE SET e.type = $type, e.chunk_ids = $ids
ON MATCH SET e.chunk_ids = $merged_ids

// 删除全部
MATCH (e:Entity) DETACH DELETE e
```

**注意**：Neo4j Python 驱动的 `session.run()` 第一个参数是 Cypher 字符串，**Cypher 参数名不能叫 `query`**（与 `session.run()` 的第一个参数名冲突）。改用 `$search_text` 等名称。

---

## 6. 调试技巧

### 6.1 后端调试

```bash
# 查看后端实时日志
tail -f /tmp/backend.log

# 测试 API 是否存活
curl http://localhost:8000/health

# 获取 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"username":"admin","password":"admin123"}' \
  -H 'Content-Type: application/json' | python -c "import sys,json; print(json.load(sys.stdin)['token'])")

# 测试图谱 API
curl -s http://localhost:8000/api/v1/knowledge-graph/graph \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 测试 chat（RAG 模式）
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"session_id":"session_test","query":"你好","history":[],"mode":"rag"}'

# 测试 chat（KG 模式）
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"session_id":"kg_test","query":"张三跟谁有关","history":[],"mode":"kg"}'

# 测试 chat（NL2SQL 模式）
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"session_id":"nl2sql_test","query":"销售额前10的客户","history":[],"mode":"nl2sql"}'
```

### 6.2 数据库调试

```bash
# 查看 SQLite 表结构
sqlite3 backend/sprag.db ".schema"

# 查看文档
sqlite3 backend/sprag.db "SELECT id, title, status, store FROM documents;"

# 查看对话日志路由
sqlite3 backend/sprag.db "SELECT query, route FROM conversation_logs ORDER BY id DESC LIMIT 10;"

# 直接查 Neo4j
cd backend && python -c "
from app.services.neo4j_service import Neo4jService
from app.config import settings
n = Neo4jService(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
graph = n.get_full_graph()
print(f'{len(graph[\"nodes\"])} nodes, {len(graph[\"edges\"])} edges')
n.close()
"
```

### 6.3 实体提取调试

```bash
cd backend && python -c "
from app.services.llm_service import LLMService
from app.kg.entity_extractor import EntityExtractor
llm = LLMService()
extractor = EntityExtractor(llm)
result = extractor.extract('张三任A项目负责人，A项目属于创新事业部')
print(f'Entities: {len(result[\"entities\"])}')
for e in result['entities']:
    print(f'  {e[\"name\"]} ({e[\"type\"]})')
for r in result['relationships']:
    print(f'  {r[\"source\"]} --{r[\"type\"]}--> {r[\"target\"]}')
"
```

### 6.4 常见错误排查

| 症状 | 原因 | 检查 |
|------|------|------|
| `Session.run() got multiple values for argument 'query'` | Cypher 参数名 `$query` 跟驱动参数 `query` 冲突 | 改参数名为 `$search_text` |
| `KeyError: '"entities"'` | Prompt 中 `{}` 被 `str.format()` 解析 | 用 `{{` 和 `}}` 转义 |
| 图谱 API 返回 503 | Neo4j 未初始化 | 检查 `brew services list` |
| 图谱无数据 | 实体提取没跑 | 检查文档 store 是否为 graph/both |
| KG Agent 未初始化 | Neo4j 连接失败 | 检查 `.env` 中的 Neo4j 配置 |
| 上传后状态 stuck | Chunk 表为空（DocumentProcessor 不写 SQLite） | 确认向量数据库写入日志 |
| Milvus 连接失败 | milvus_lite.db 文件锁定 | 检查是否有其他进程占用 |

---

## 7. 文件变更速查

### 7.1 后端文件变更记录

| 文件 | 职责 | 变更频率 |
|------|------|---------|
| `main.py` | 入口 + 三 Agent 初始化 + 路由注册 | 低频（加新路由时） |
| `config.py` | 环境配置（含 Milvus Lite） | 低频（加新配置时） |
| `database.py` | 引擎 + 迁移 | 低频（模型变更时） |
| `models/*.py` | ORM 定义 | 中频 |
| `schemas/*.py` | 响应模型 | 中频 |
| `api/chat.py` | 三模式问答调度 | 中频 |
| `api/documents.py` | 文档管理 | 中频 |
| `api/knowledge_graph.py` | 图谱管理（含节点/关系维护） | 中频 |
| `agents/agent_factory.py` | 三 Agent 工厂 | 低频 |
| `agents/tools.py` | 三组工具函数 | 中频 |
| `rag/*.py` | RAG 引擎 | 低频（一般不修改） |
| `kg/*.py` | KG 引擎 | 中频 |
| `services/neo4j_service.py` | Neo4j 操作（含 CRUD） | 中频 |
| `services/vector_store.py` | Milvus Lite 封装 | 低频 |

### 7.2 前端文件变更记录

| 文件 | 职责 | 变更频率 |
|------|------|---------|
| `views/ChatView.vue` | 三 Tab 对话容器 | 中频 |
| `views/AdminView.vue` | 管理后台 Tab 容器 | 低频 |
| `components/admin/KnowledgeGraphViewer.vue` | 全景图谱（3 子 Tab） | 中频 |
| `components/admin/KgNodeTable.vue` | 节点维护表格 | 中频 |
| `components/admin/KgEdgeTable.vue` | 关系维护表格 | 中频 |
| `components/chat/ChatWindow.vue` | RAG/KG 聊天窗 | 中频 |
| `components/chat/Nl2SqlChat.vue` | 问数聊天窗（含图表） | 中频 |
| `components/chat/MessageBubble.vue` | 消息气泡（表格+图表） | 中频 |
| `components/chat/SessionSidebar.vue` | 会话侧边栏 | 中频 |
| `api/index.js` | API 客户端 | 中频（加新接口时） |

---

## 8. 关键配置项

### 8.1 .env 文件

```ini
# 必须配置
VOLC_API_KEY=xxx
LLM_MODEL_NAME=ep-xxx
EMBEDDING_MODEL_NAME=ep-xxx

# 可选（不配则图谱功能关闭）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j

# Milvus Lite（可选，默认 ./milvus_lite.db）
MILVUS_LITE_URI=./milvus_lite.db
EMBEDDING_DIM=2048
```

### 8.2 运行时配置（Settings 面板可调）

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `enable_knowledge_graph` | true | 全局 KG 开关 |
| `kg_extract_on_upload` | true | 上传时自动提取实体 |
| `enable_query_rewriting` | true | Query 改写 |
| `enable_hybrid_retrieval` | true | 混合检索 |
| `enable_reranker` | true | 重排序 |
| `retriever_top_k` | 10 | 检索数量 |
| `reranker_top_k` | 5 | 排序后保留数 |
| `chunk_size` | 500 | 分块大小 |
| `nl2sql_max_rows` | 50 | NL2SQL 查询行数上限 |

---

## 9. 部署检查清单

- [ ] Neo4j 已启动：`brew services list | grep neo4j`
- [ ] 火山引擎 API Key 有效
- [ ] `.env` 中 LLM_MODEL_NAME 和 EMBEDDING_MODEL_NAME 正确
- [ ] 后端启动日志显示 `✅ Neo4j connected and initialized`（如有）
- [ ] 后端启动日志显示 `✅ RAG agent initialized`
- [ ] 后端启动日志显示 `✅ KG agent initialized`（Neo4j 正常时）
- [ ] 后端启动日志显示 `✅ NL2SQL agent initialized`
- [ ] 后端启动日志显示 `✅ BM25 index rebuilt`（有文档时）
- [ ] `/health` 返回 `{"status": "ok"}`
- [ ] 前端 `npm run dev` 无报错
