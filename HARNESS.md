# SPRAG 开发工作指南

> 开发者日常工作流、代码规范、调试技巧

---

## 1. 项目总览

| 属性 | 内容 |
|------|------|
| 项目名 | SPRAG — Smart Product RAG |
| 后端框架 | Python FastAPI + SQLAlchemy 2.0 |
| 前端框架 | Vue 3 (Composition API) + Vite 5 |
| LLM | 火山引擎 API（OpenAI 兼容） |
| 向量库 | ChromaDB |
| 图谱库 | Neo4j |
| 数据库 | SQLite |

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
│   ├── main.py                 # FastAPI 入口 + lifespan + 路由注册
│   ├── config.py               # Pydantic Settings（.env）
│   ├── database.py             # SQLAlchemy engine + 自动迁移
│   ├── models/                 # ORM 模型（6 个文件）
│   ├── schemas/                # Pydantic 响应模型
│   ├── api/                    # API 路由（12 个文件）
│   │   ├── chat.py             # SSE 流式问答（路由分发 RAG/KG）
│   │   ├── documents.py        # 文档上传/列表/删除 + KG 处理
│   │   ├── knowledge_graph.py  # 图谱管理 API
│   │   ├── knowledge_bases.py  # 知识库 CRUD
│   │   └── ...
│   ├── rag/                    # RAG 引擎（与 kg 完全独立）
│   │   ├── retriever.py        # 检索编排
│   │   ├── generator.py        # RAG 系统 Prompt + 流式
│   │   ├── query_rewriter.py   # LLM 代词改写
│   │   ├── hybrid_retriever.py # RRF 融合
│   │   ├── reranker.py         # LLM 重排序
│   │   ├── bm25_retriever.py   # 关键词检索
│   │   └── document_processor.py # 文本提取 + 分块
│   ├── kg/                     # 知识图谱引擎（与 rag 完全独立）
│   │   ├── query_router.py     # RAG/KG 路由判断
│   │   ├── entity_extractor.py # LLM 实体提取
│   │   ├── graph_retriever.py  # 图遍历检索
│   │   └── graph_generator.py  # KG 专用 Prompt
│   └── services/               # 基础设施
│       ├── llm_service.py      # 火山引擎 API 封装
│       ├── neo4j_service.py    # Neo4j 连接/Cypher
│       ├── vector_store.py     # ChromaDB 封装
│       ├── auth_service.py     # JWT + bcrypt
│       └── runtime_config.py   # 运行时参数持久化
├── uploads/                    # 上传文档原件
├── chroma_db/                  # ChromaDB 持久化
├── sprag.db                    # SQLite 数据库
└── runtime_config.json         # 运行时配置

frontend/
├── src/
│   ├── main.js                 # Vue 入口
│   ├── router/index.js         # 路由（/ /admin /login /register）
│   ├── api/index.js            # Axios API 客户端
│   ├── views/                  # 4 个页面
│   │   ├── ChatView.vue
│   │   ├── AdminView.vue       # 8 个 Tab 的容器
│   │   ├── LoginView.vue
│   │   └── RegisterView.vue
│   └── components/
│       ├── admin/              # 管理后台组件（8 个）
│       │   ├── KnowledgeGraphViewer.vue  # vis-network 全景图
│       │   └── ...
│       └── chat/               # 对话组件（4 个）
│           ├── ChatWindow.vue
│           ├── MessageBubble.vue
│           ├── SourceReference.vue
│           └── MiniGraphModal.vue         # vis-network 弹窗
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
  api/chat.py       → 调用 query_router + graph_retriever
  api/documents.py  → 调用 entity_extractor + neo4j_service
  api/knowledge_graph.py → 调用 neo4j_service + entity_extractor
```

### 4.2 新增一个 API 路由的步骤

1. 在 `api/` 下创建 `.py` 文件，定义 `router = APIRouter(prefix=...)`
2. 在 `main.py` 添加 `app.include_router(router, prefix="/api/v1")`
3. 前端 `api/index.js` 添加对应的 Axios 函数
4. 前端组件调用 API 函数

### 4.3 新增一个模型字段的步骤

1. 修改 `models/` 中对应的 ORM 类
2. 修改 `schemas/` 中对应的 Pydantic 模型
3. 在 `database.py` 的 `_run_migrations()` 添加 ALTER TABLE 语句
4. 重启后端触发迁移

### 4.4 SSE 流式协议

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
const response = await sendChatMessage(sessionId, query, history)
const reader = response.body.getReader()
// 逐行解析 SSE
```

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
query_router.py（LLM 判断 RAG/KG）
    ↓ KG
graph_retriever.retrieve(query)
    ├─ neo4j.find_seed_entities(query)   ← $query CONTAINS e.name
    ├─ neo4j.bfs_traverse_1hop(names)    ← (e)-[r]-(neighbor)
    ├─ neo4j.bfs_traverse_2hop(names)    ← (e)-[*1..2]-(connected)
    ├─ 收集 chunk_ids + 打分
    └─ SQLite 取 chunk 原文
    ↓
graph_generator.generate(query, contexts, kg_text)
    └─ KG_SYSTEM_PROMPT + 关系路径 + LLM 生成 → SSE
```

### 5.4 Cypher 查询模式

```cypher
// 种子匹配
MATCH (e:Entity) WHERE $query CONTAINS e.name RETURN e

// 1跳遍历（无向）
MATCH (e:Entity {name: $name}) OPTIONAL MATCH (e)-[r]-(n) RETURN e, r, n

// 2跳遍历
MATCH (e:Entity {name: $name}) OPTIONAL MATCH (e)-[*1..2]-(n) RETURN n

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

# 测试 chat
curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"session_id":"test","query":"你好","history":[]}'
```

### 6.2 数据库调试

```bash
# 查看 SQLite 表结构
sqlite3 backend/sprag.db ".schema"

# 查看文档
sqlite3 backend/sprag.db "SELECT id, title, status, store FROM documents;"

# 查看对话日志路由
sqlite3 backend/sprag.db "SELECT query, route FROM conversation_logs ORDER BY id DESC LIMIT 5;"

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
| 图谱无数据 | 实体提取没跑 / chunk_ids 为空 | 检查 `_process_document_kg` 日志 |
| 上传后状态 stuck | Chunk 表为空（DocumentProcessor 不写 SQLite） | 确认 `_process_document_kg` 写入 chunks 表 |

---

## 7. 文件变更速查

### 7.1 后端文件变更记录

| 文件 | 职责 | 变更频率 |
|------|------|---------|
| `main.py` | 入口 + 路由注册 | 低频（加新路由时） |
| `config.py` | 环境配置 | 低频（加新配置时） |
| `database.py` | 引擎 + 迁移 | 低频（模型变更时） |
| `models/*.py` | ORM 定义 | 中频 |
| `schemas/*.py` | 响应模型 | 中频 |
| `api/chat.py` | 问答调度 | 中频 |
| `api/documents.py` | 文档管理 | 中频 |
| `api/knowledge_graph.py` | 图谱管理 | 低频 |
| `rag/*.py` | RAG 引擎 | 低频（一般不修改） |
| `kg/*.py` | KG 引擎 | 高频（新功能开发期） |
| `services/neo4j_service.py` | Neo4j 操作 | 中频 |

### 7.2 前端文件变更记录

| 文件 | 职责 | 变更频率 |
|------|------|---------|
| `views/AdminView.vue` | 管理后台 Tab 容器 | 低频 |
| `components/admin/KnowledgeGraphViewer.vue` | 全景图谱 | 中频 |
| `components/chat/MiniGraphModal.vue` | 图谱弹窗 | 中频 |
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

---

## 9. 部署检查清单

- [ ] Neo4j 已启动：`brew services list | grep neo4j`
- [ ] 火山引擎 API Key 有效
- [ ] `.env` 中 LLM_MODEL_NAME 和 EMBEDDING_MODEL_NAME 正确
- [ ] 后端启动日志显示 `✅ Neo4j connected and initialized`
- [ ] 后端启动日志显示 `✅ KG routes initialized`
- [ ] `/health` 返回 `{"status": "ok"}`
- [ ] 前端 `npm run dev` 无报错