# SuperRAG 系统详细设计文档

> 版本：v0.5 | 更新日期：2026-06-25

---

## 目录

1. [系统架构](#1-系统架构)
2. [数据模型](#2-数据模型)
3. [API 设计](#3-api-设计)
4. [RAG 引擎](#4-rag-引擎)
5. [知识图谱引擎](#5-知识图谱引擎)
6. [三 Agent 架构](#6-三-agent-架构)
7. [文档处理流程](#7-文档处理流程)
8. [前端设计](#8-前端设计)
9. [配置与部署](#9-配置与部署)

---

## 1. 系统架构

### 1.1 整体架构

```
┌────────────────────────────────────────────────────────────────┐
│                      前端 (Vue 3 + Vite)                        │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ ChatView    │  │ AdminView    │  │ KnowledgeGraph       │  │
│  │ 三Tab对话    │  │ 管理后台      │  │ Viewer (图谱/Nodes/Edges)│
│  └──────┬──────┘  └──────┬───────┘  └────────┬─────────────┘  │
│         │                │                    │                 │
│         ▼                ▼                    ▼                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Axios / SSE (Event Stream)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────┬─────────────────────────┘
                                       │
┌──────────────────────────────────────▼─────────────────────────┐
│                    后端 (FastAPI)                               │
│                                                                │
│  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌────────────┐ │
│  │ API 路由  │  │ RAG 引擎   │  │ KG 引擎     │  │ deepagents │ │
│  │ chat.py   │  │ retriever │  │ entity_     │  │ Agent     │ │
│  │ documents │  │ generator │  │ extractor  │  │ Factory   │ │
│  │ knowledge_│  │ document_ │  │ graph_     │  │ (RAG/KG/   │ │
│  │ graph.py  │  │ processor │  │ retriever  │  │ NL2SQL)   │ │
│  │ nl2sql.py │  │ reranker  │  │            │  │ + tools   │ │
│  └─────┬─────┘  └─────┬─────┘  └──────┬─────┘  └─────┬─────┘ │
│        │              │               │               │        │
│        ▼              ▼               ▼               ▼        │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                   服务层 (Services)                        │ │
│  │  ┌───────────┐  ┌────────────┐  ┌─────────────────────┐  │ │
│  │  │LLM Service│  │Vector      │  │Neo4j Service        │  │ │
│  │  │(火山引擎)  │  │Store       │  │(Bolt 协议, 含 CRUD)  │  │ │
│  │  └───────────┘  │(Milvus Lite)│  └─────────────────────┘  │ │
│  │                 └────────────┘                             │ │
│  └───────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
          │                  │                    │
          ▼                  ▼                    ▼
┌──────────────┐  ┌─────────────────┐  ┌──────────────────────┐
│   SQLite     │  │  Milvus Lite    │  │  Neo4j               │
│   sprag.db   │  │  milvus_lite.db │  │  bolt://localhost    │
│  文档/用户/   │  │  稠密向量+BM25   │  │  实体/关系图          │
│  日志/分块    │  │  稀疏向量       │  │                      │
└──────────────┘  └─────────────────┘  └──────────────────────┘
```

### 1.2 存储分层

| 存储 | 存储内容 | 访问方式 | 依赖 |
|------|---------|---------|------|
| SQLite | 用户、文档、知识库、分块、日志、反馈 | SQLAlchemy ORM | 无 |
| Milvus Lite | 文档分块稠密向量 + BM25 稀疏向量 | VectorStoreService | `pip install pymilvus` |
| Neo4j | 实体节点、关系边 | Neo4jService | `brew install neo4j` |
| 文件系统 | 上传文档原件（PDF/DOCX 等） | 直接文件读写 | 无 |
| JSON 文件 | 运行时配置参数 | runtime_config.py | 无 |

### 1.3 核心依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| fastapi | 0.104+ | Web 框架 |
| sqlalchemy | 2.0+ | ORM |
| neo4j | 5.20+ | Neo4j 驱动 |
| pymilvus | 2.4+ | 向量数据库（Milvus Lite） |
| milvus-model | - | BM25EmbeddingFunction(language="zh") |
| deepagents | 0.5+ | Agent 框架（三 Agent 独立 checkpointer） |
| langchain | 0.1+ | 文本分块 |
| langchain-openai | - | LLM 客户端（兼容火山引擎） |
| pyodbc + FreeTDS | - | SQL Server 连接 |
| jieba | - | 中文分词（BM25） |
| vis-network | - | 前端图谱可视化 |
| echarts | 5 | 前端图表 |
| vue-router | 4 | 前端路由 |

---

## 2. 数据模型

### 2.1 SQLite 表结构

#### users（用户）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| username | VARCHAR(50) | 用户名（唯一索引） |
| email | VARCHAR(100) | 邮箱 |
| password_hash | VARCHAR(255) | bcrypt 哈希 |
| role | VARCHAR(10) | `admin` / `user` |
| is_active | BOOLEAN | 是否激活 |
| created_at | DATETIME | 创建时间 |

#### documents（文档）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| title | VARCHAR(255) | 文档标题 |
| doc_type | VARCHAR(50) | 文件扩展名 |
| category | VARCHAR(100) | 分类 |
| file_path | VARCHAR(500) | 文件路径 |
| status | VARCHAR(20) | pending/processing/ready/failed |
| **store** | **VARCHAR(10)** | **存储目标：vector/graph/both** |
| created_at | DATETIME | |
| updated_at | DATETIME | |

#### chunks（分块/全文）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| document_id | FK→documents | 所属文档 |
| **content** | **TEXT** | **分块文本或全文（KG 文档）** |
| embedding_id | VARCHAR(100) | Milvus Lite ID（仅向量文档） |
| chunk_index | INTEGER | 块序号（KG 文档固定为 0） |
| metadata_json | TEXT | JSON 元数据 |
| created_at | DATETIME | |

#### knowledge_bases（知识库）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| name | VARCHAR(100) | 名称（唯一） |
| description | TEXT | 描述 |
| created_at | DATETIME | |
| updated_at | DATETIME | |

#### conversation_logs（对话日志）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| session_id | VARCHAR(100) | 会话 ID（索引） |
| query | TEXT | 用户问题 |
| rewritten_query | TEXT | 改写后查询 |
| answer | TEXT | AI 回答 |
| sources | TEXT | JSON 来源数组 |
| **route** | **VARCHAR(10)** | **AGENT / KG / NL2SQL** |
| latency_ms | INTEGER | 响应延迟 |
| token_count | INTEGER | Token 数 |
| model | VARCHAR(100) | 模型名 |
| nl2sql_sql | TEXT | NL2SQL 生成的 SQL |
| nl2sql_prompt | TEXT | NL2SQL 完整提示词 |
| created_at | DATETIME | |

#### feedbacks（反馈）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| session_id | VARCHAR(100) | 会话 ID |
| rating | VARCHAR(10) | like/dislike |
| suggestion | TEXT | 建议文本 |
| created_at | DATETIME | |

#### 关联表

| 表名 | 说明 | 字段 |
|------|------|------|
| document_knowledge_base | 文档↔知识库 M:N | document_id, knowledge_base_id |
| user_knowledge_base | 用户↔知识库 M:N | user_id, knowledge_base_id |

### 2.2 Neo4j 图模型

#### 节点：`:Entity`

```
(:Entity {
  name: "张三",           // 实体名称（唯一约束）
  type: "person",         // person/org/product/concept/location
  chunk_ids: [1, 5, 12], // 关联的 SQLite chunk ID 列表
  properties: "{}",       // JSON 额外属性
  internal_id: UUID       // 内部标识
})
```

#### 关系：动态类型

```
(:Entity {name:"张三"})-[:负责]->(:Entity {name:"A项目"})
(:Entity {name:"张三"})-[:任职于]->(:Entity {name:"创新事业部"})
(:Entity {name:"A项目"})-[:属于]->(:Entity {name:"创新事业部"})
```

#### 索引

```cypher
CREATE INDEX entity_name IF NOT EXISTS FOR (n:Entity) ON (n.name)
```

### 2.3 Milvus Lite 集合结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR | 文档 chunk ID |
| text | VARCHAR | 原文内容 |
| embedding | FLOAT_VECTOR(2048) | 稠密向量（doubao-embedding） |
| sparse_embedding | SPARSE_FLOAT_VECTOR | BM25 稀疏向量 |
| metadata_json | VARCHAR | JSON 元数据 |

检索方式：
- 稠密检索：`ANN搜索`（cosine 相似度）
- 稀疏检索：`ANN搜索`（IP 内积）
- 混合检索：`hybrid_search` + RRFRanker 融合

---

## 3. API 设计

### 3.1 路由列表

所有 API 均以 `/api/v1` 为前缀。

| 路径 | 方法 | 权限 | 说明 |
|------|------|------|------|
| **认证** | | | |
| /auth/register | POST | 公开 | 注册 |
| /auth/login | POST | 公开 | 登录返回 JWT |
| /auth/me | GET | 登录 | 当前用户信息 |
| **对话** | | | |
| /chat | POST | 登录 | 流式问答（SSE, 支持 mode=rag/kg/nl2sql） |
| /chat/history | GET | 登录 | 历史消息（支持 mode） |
| /chat/sessions | GET | 登录 | 会话列表（按 mode 过滤 route） |
| /chat/sessions/{id} | DELETE | 登录 | 删除会话（支持 mode） |
| /chat/sessions/{id} | PUT | 登录 | 重命名会话 |
| **文档** | | | |
| /documents/upload | POST | 管理员 | 上传文档 (+ store 参数) |
| /documents | GET | 管理员 | 文档列表 (+ store 过滤) |
| /documents/{id} | DELETE | 管理员 | 删除文档 |
| /documents/{id}/reprocess | POST | 管理员 | 重新处理文档 |
| **知识库** | | | |
| /knowledge-bases | GET/POST | 管理员 | 知识库 CRUD |
| /knowledge-bases/{id} | PUT/DELETE | 管理员 | 编辑/删除 |
| /knowledge-bases/{id}/documents | GET/PUT | 管理员 | 文档关联 |
| /knowledge-bases/{id}/users | GET/PUT | 管理员 | 用户权限 |
| **知识图谱** | | | |
| /knowledge-graph/graph | GET | 登录 | 全量图谱数据 |
| /knowledge-graph/entities/search | GET | 登录 | 搜索实体 |
| /knowledge-graph/entities/{id} | GET | 登录 | 实体详情 |
| /knowledge-graph/entities/{id} | PUT | 管理员 | 更新实体 |
| /knowledge-graph/entities/{id} | DELETE | 管理员 | 删除实体 |
| /knowledge-graph/entities/{id}/relationship-count | GET | 管理员 | 节点关系数 |
| /knowledge-graph/entities/batch-delete | POST | 管理员 | 批量删除实体 |
| /knowledge-graph/relationships | POST | 管理员 | 手动创建关系 |
| /knowledge-graph/relationships | PUT | 管理员 | 修改关系类型 |
| /knowledge-graph/relationships | DELETE | 管理员 | 删除关系 |
| /knowledge-graph/relationships/batch-delete | POST | 管理员 | 批量删除关系 |
| /knowledge-graph/extract | POST | 管理员 | 重建全局图谱 |
| **NL2SQL** | | | |
| /nl2sql/config | GET/PUT | 管理员 | NL2SQL 配置 CRUD |
| /nl2sql/config/connection | GET/PUT | 管理员 | 数据库连接配置 |
| /nl2sql/config/prompts | GET/PUT | 管理员 | 提示词配置 |
| /nl2sql/test-connection | POST | 管理员 | 测试数据库连接 |
| **其他** | | | |
| /logs | GET | 管理员 | 问答日志 |
| /feedback | GET/POST | 登录 | 用户反馈 |
| /stats/overview | GET | 管理员 | 统计概览 |
| /stats/trends | GET | 管理员 | 趋势数据 |
| /alerts | GET | 管理员 | 告警检测 |
| /config | GET/PUT | 管理员 | 运行时配置 |
| /users | GET | 管理员 | 用户管理 |

### 3.2 SSE 协议（/chat 流式响应）

```
data: {"type": "token", "content": "根据知识"}
data: {"type": "token", "content": "图谱信息"}
data: {"type": "tool_call", "tool": "search_knowledge_graph"}
data: {"type": "sources", "sources": [
  {
    "chunk_id": "",
    "document_title": "知识图谱",
    "content": "[实体] 苹果公司 --(创立)--> 乔布斯",
    "score": 1.0,
    "type": "kg",
    "graph": {
      "nodes": [{"id": "g_0", "name": "苹果公司", "type": "concept"}, ...],
      "edges": [{"source": "g_0", "target": "g_1", "type": "创立"}, ...]
    }
  }
]}
data: [DONE]
```

NL2SQL 模式额外事件：

```
data: {"type": "sources", "sources": [
  {"type": "nl2sql", "sql": "SELECT TOP 50 ...", "resultData": "{\"data\":[...]}", ...},
  {"type": "chart", "spec": {"type":"bar", "x":"客户", "y":["销售额"], ...}}
]}
```

### 3.3 认证机制

- **JWT**（HS256, 7天过期）
- 前端存储在 `localStorage.token`
- Axios 拦截器自动附加 `Authorization: Bearer <token>`
- 401 自动跳转登录页

---

## 4. RAG 引擎

### 4.1 文件：`backend/app/rag/`

```
rag/
├── __init__.py
├── retriever.py            # 检索编排：改写 → 混合检索 → 重排序
├── hybrid_retriever.py     # RRF 融合：向量 + BM25
├── bm25_retriever.py       # BM25EmbeddingFunction(language="zh")
├── reranker.py             # LLM 批量相关性重评分（单次调用所有结果）
├── query_rewriter.py       # LLM 代词解析 + 查询补全
├── generator.py            # RAG 系统 Prompt + 流式生成
└── document_processor.py   # 文本提取 + 分块 + 向量化
```

### 4.2 处理流程

```
用户问题
    │
    ├─ 1. Query Rewriting（LLM 改写）
    │     原始："它多少钱？" → 改写："iPhone 15 的价格是多少？"
    │
    ├─ 2. Hybrid Retrieval（混合检索）
    │     稠密检索 (Milvus Lite, cosine) ──┐
    │     BM25 稀疏检索 (Milvus Lite, IP) ──┤── RRF 融合
    │                                       │
    │     Score(c) = Σ 1/(k + rank(c))
    │
    ├─ 3. Re-ranking（LLM 批量重排序）
    │     所有结果一次发给 LLM 统一评分 0-10
    │     按评分降序取 reranker_top_k 条
    │
    └─ 4. Generation
          System Prompt + 上下文 + 历史消息 → LLM 流式输出
```

### 4.3 核心算法：RRF 融合

```python
fusion_scores = {}
k_const = 60

for rank, item in enumerate(vector_results):
    fusion_scores[id] += 1 / (k_const + rank + 1)

for rank, item in enumerate(bm25_results):
    fusion_scores[id] += 1 / (k_const + rank + 1)

sorted_ids = sorted(fusion_scores, key=lambda x: fusion_scores[x], reverse=True)
```

### 4.4 BM25 中文检索

```python
from milvus_model.hybrid import BM25EmbeddingFunction

# 使用 jieba 中文分词
_bm25_ef = BM25EmbeddingFunction(language="zh")

# 编码查询
query_sparse = _bm25_ef.encode_queries([query])

# 编码文档（需要先 fit corpus）
_bm25_ef.fit([all_texts])
doc_sparse = _bm25_ef.encode_documents([text])
```

---

## 5. 知识图谱引擎

### 5.1 文件：`backend/app/kg/`

```
kg/
├── __init__.py
├── entity_extractor.py  # 实体提取（全文→LLM→结构化）
└── graph_retriever.py   # 实体匹配 → 图遍历 → 关系文本
```

> **注意**：`query_router.py` 和 `graph_generator.py` 已移除（功能由 deepagents Agent 接管）。

### 5.2 处理流程

```
用户问题："库克跟苹果公司的关系"
    │
    ├─ Step 1: 种子实体匹配（neo4j_service.py）
    │     Cypher: MATCH (e) WHERE $search_text CONTAINS e.name
    │     匹配到: "库克"(person), "苹果公司"(product)
    │
    ├─ Step 2: 图遍历（neo4j_service.py）
    │     1跳: MATCH (e)-[r]-(neighbor) WHERE e.name IN $names
    │     多跳: MATCH (e)-[*1..depth]-(connected)
    │     返回: (库克)--接任-->(乔布斯)
    │           (苹果公司)--创立-->(乔布斯)
    │
    ├─ Step 3: 构建关系文本（graph_retriever.py）
    │     [实体] 库克 --(接任)--> 乔布斯
    │     [实体] 苹果公司 --(创立)--> 乔布斯
    │     [实体] 苹果公司 --(推出)--> iPhone
    │
    └─ Step 4: Agent 生成
         KG Agent 基于关系文本用中文回答
```

> **变更说明**：原 Step 4（Chunk 收集与打分）和 Step 5（graph_generator）已移除。KG 检索不再从 SQLite 查询 chunk 原文，只返回关系文本，由 Agent 直接生成回答。

### 5.3 实体提取（entity_extractor.py）

```
文档全文 (≤3000字)
    │
    ├─ LLM Prompt：
    │   从文本中提取以下实体类型：
    │   - person: 人物
    │   - org: 组织/公司/部门
    │   - product: 产品/项目
    │   - concept: 概念/术语
    │   - location: 地点
    │   以及实体间的关系
    │
    ├─ LLM 返回 JSON：
    │   {"entities": [{"name": "张三", "type": "person", ...}],
    │    "relationships": [{"source": "张三", "target": "A项目", "type": "负责"}]}
    │
    └─ 写入 Neo4j：
         MERGE (Entity {name: "张三"})
         MERGE (Entity {name: "A项目"})
         MERGE (张三)-[:负责]->(A项目)
```

### 5.4 关系路径文本格式化

```
[实体] 库克 --(接任)--> 乔布斯
[实体] 苹果公司 --(创立)--> 乔布斯
[实体] 苹果公司 --(推出)--> iPhone

=== 实体间连接路径 ===
  库克 --(接任)--> 乔布斯 --(创立)--> 苹果公司
```

---

## 6. 三 Agent 架构

### 6.1 设计原则

```
┌──────────────────────────────────────────────────────┐
│                    三 Agent 架构                       │
│                                                      │
│  ┌──────────────────────────────────────────────────┐│
│  │          api/chat.py (三路分发)                   ││
│  │                                                   ││
│  │  mode=rag  → get_rag_agent()                      ││
│  │    tools: [search_knowledge_base]                 ││
│  │    prompt: RAG_SYSTEM_PROMPT                      ││
│  │    thread: rag_u{user.id}_{session_id}            ││
│  │    route: AGENT                                   ││
│  │                                                   ││
│  │  mode=kg   → get_kg_agent()                       ││
│  │    tools: [search_knowledge_graph]                 ││
│  │    prompt: KG_SYSTEM_PROMPT                       ││
│  │    thread: kg_u{user.id}_{session_id}             ││
│  │    route: KG                                      ││
│  │                                                   ││
│  │  mode=nl2sql→ get_nl2sql_agent()                  ││
│  │    tools: [query_database, make_chart]             ││
│  │    prompt: NL2SQL_SYSTEM_PROMPT                   ││
│  │    thread: nl2sql_u{user.id}_{session_id}          ││
│  │    route: NL2SQL                                  ││
│  └──────────────────────────────────────────────────┘│
│                                                      │
│  三个 Agent 共用一个 _create_agent() 工厂函数          │
│  各自拥有独立的 AsyncSqliteSaver checkpointer         │
└──────────────────────────────────────────────────────┘
```

### 6.2 Agent 初始化顺序（main.py lifespan）

```
1. Neo4j 初始化（失败则 KG 禁用）
2. RAG Agent 初始化（不依赖 Neo4j）
3. KG Agent 初始化（依赖 Neo4j，仅在 Neo4j 正常时）
4. NL2SQL Agent 初始化（独立于 KG）
5. BM25 索引重建（从已有文档数据）
```

### 6.3 Agent 系统提示词

**RAG Agent：**
```
你是一个专业的客服助手。你可以使用 search_knowledge_base 工具从知识库中检索信息。
工作流程：
1. 根据用户问题调用 search_knowledge_base 检索相关知识
2. 基于检索到的内容用中文回答用户
3. 如果检索结果不足以回答，明确告知用户
```

**KG Agent：**
```
你是一个知识图谱分析助手。你可以使用 search_knowledge_graph 工具从知识图谱中检索实体关系。
工作流程：
1. 根据用户问题调用 search_knowledge_graph 检索相关实体关系
2. 基于检索到的关系用中文回答用户
3. 如果图谱中没有找到相关信息，明确告知用户
```

**NL2SQL Agent：**
```
你是一个数据分析助手。你可以使用两个工具：
- query_database：根据自然语言查询数据仓库，得到表格数据
- make_chart：根据"上一次 query_database 的结果"生成图表配置

工作流程：
1. 用户提出数据问题 → 调用 query_database 查询
2. 拿到结果后用中文回答用户的问题，对数据做有意义的解读
3. 当用户明确要求"画图"时 → 调用 make_chart
```

### 6.4 NL2SQL 工具：query_database

```
输入: 自然语言查询
流程:
  1. 读取 NL2SQL 配置（数据库连接 + 提示词三件套）
  2. 读取运行时配置的 nl2sql_max_rows（默认 50）
  3. 构造 system prompt（含字段结构/术语映射/Q&A示例 + TOP N 限制）
  4. LLM 生成 SQL
  5. _ensure_top_limit() 兜底注入/夹紧 TOP N
  6. pyodbc 执行 SQL Server
  7. 返回格式化表格 + 缓存到 thread（供 make_chart 使用）

输出: 表格文本（SQL + 数据行）
```

### 6.5 NL2SQL 工具：make_chart

```
输入: chart_type, x_field, y_fields, title
流程:
  1. 从 thread 缓存读取上一次 query_database 的结果数据
  2. 校验字段名和图表类型
  3. 构造 ECharts spec
  4. 推送到 _current_sources

支持图表类型: bar, pie, line, area, scatter, stacked_bar
```

### 6.6 会话隔离

| 维度 | RAG | KG | NL2SQL |
|------|-----|-----|--------|
| session_id 前缀 | `session_` | `kg_` | `nl2sql_` |
| thread_id 前缀 | `rag_u{id}_` | `kg_u{id}_` | `nl2sql_u{id}_` |
| route 日志值 | AGENT | KG | NL2SQL |
| localStorage key | `chat_session_id` | `kg_session_id` | `nl2sql_session_id` |

---

## 7. 文档处理流程

### 7.1 上传时序

```
用户选择文件 + 存储目标
    │
    ▼
┌────────────────────────────────────────────────────┐
│  1. 保存文件到 uploads/                             │
│  2. 创建 Document 记录（status=pending, store=X）    │
│  3. 关联知识库（仅 vector/both）                      │
│  4. status = processing                            │
└────────────────────────┬───────────────────────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
      store=vector/both      store=graph/both
              │                     │
              ▼                     ▼
┌──────────────────┐   ┌────────────────────────┐
│  RAG 处理         │   │  KG 处理                │
│  extract_text()   │   │  extract_text()         │
│  split_text()     │   │  LLM 提取实体/关系       │
│  → Milvus Lite    │   │  全文存 SQLite chunks   │
│  (稠密+稀疏向量)   │   │  → 写入 Neo4j           │
│  → BM25 索引重建   │   └────────────────────────┘
└──────────────────┘
              │                     │
              └──────────┬──────────┘
                         ▼
                  status = ready
```

### 7.2 store 值对应的处理

| store 值 | RAG 处理 | KG 处理 | 知识库关联 |
|----------|---------|---------|-----------|
| `vector` | ✅ 分块+向量化+BM25 | ❌ | ✅ |
| `graph` | ❌ | ✅ 实体提取→Neo4j | ❌（图谱全局） |
| `both` | ✅ | ✅ | ✅ |

---

## 8. 前端设计

### 8.1 路由

| 路径 | 组件 | 说明 |
|------|------|------|
| `/login` | LoginView | 登录 |
| `/register` | RegisterView | 注册 |
| `/` | ChatView | 客服对话（三 Tab） |
| `/admin` | AdminView | 管理后台（9 个 Tab） |

### 8.2 管理后台 Tab

| Tab | 组件 | 说明 |
|-----|------|------|
| 仪表盘 | DashboardView | 统计卡片 + 趋势图 |
| 文档管理 | DocumentUploader + 内联表格 | 上传 + 列表（子标签: 向量/图谱） |
| 知识库 | KnowledgeBaseManager | CRUD + 文档/用户关联 |
| **知识图谱** | **KnowledgeGraphViewer + KgNodeTable + KgEdgeTable** | **全景图 + 节点维护 + 关系维护** |
| NL2SQL | Nl2SqlPanel | 连接配置 + 提示词三件套 |
| 用户管理 | UserManager | 用户 CRUD + 权限 |
| 问答日志 | LogViewer | 日志列表 + 详情 |
| 用户反馈 | FeedbackPanel | 反馈统计 + 列表 |
| 参数配置 | SettingsPanel | 运行时参数（含 nl2sql_max_rows） |

### 8.3 图谱可视化技术选型

| 场景 | 库 | 说明 |
|------|-----|------|
| 管理后台全景图 | vis-network | Barnes-Hut 物理引擎，支持大规模图（200+节点） |
| 问答弹窗子图 | vis-network | 深度滑条控制展开层级，种子节点星形高亮 |

### 8.4 vis-network 配置

```javascript
physics: {
  barnesHut: {
    gravitationalConstant: -4000,
    centralGravity: 0.3,
    springLength: 180,
    springConstant: 0.04,
    damping: 0.09,
    avoidOverlap: 0.1,
  },
  stabilization: { iterations: 800 }
}
```

### 8.5 节点着色

| 类型 | 颜色 | 16进制 |
|------|------|--------|
| person（人物） | 红色 | `#e91e63` |
| org（组织） | 蓝色 | `#2196f3` |
| product（产品/项目） | 绿色 | `#4caf50` |
| concept（概念） | 橙色 | `#ff9800` |
| location（地点） | 紫色 | `#9c27b0` |

---

## 9. 配置与部署

### 9.1 环境变量（`.env`）

```ini
# LLM
VOLC_API_KEY=your_api_key
VOLC_ENDPOINT=https://ark.cn-beijing.volces.com/api/v3
LLM_MODEL_NAME=ep-xxxx-xxxxx
EMBEDDING_MODEL_NAME=ep-xxxx-xxxxx

# 存储
MILVUS_LITE_URI=./milvus_lite.db
EMBEDDING_DIM=2048
DATABASE_URL=sqlite:///./sprag.db
UPLOAD_DIR=./uploads

# 认证
JWT_SECRET_KEY=change-this-to-a-random-secret
DEFAULT_ADMIN_PASSWORD=admin123

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### 9.2 运行时配置（runtime_config.json）

```json
{
  "enable_query_rewriting": true,
  "enable_hybrid_retrieval": true,
  "enable_reranker": true,
  "enable_knowledge_graph": true,
  "kg_extract_on_upload": true,
  "retriever_top_k": 10,
  "reranker_top_k": 5,
  "bm25_top_k": 10,
  "hybrid_fusion_k": 60,
  "chunk_size": 500,
  "chunk_overlap": 50,
  "llm_temperature": 0.7,
  "nl2sql_detail_logging": false,
  "nl2sql_max_rows": 50,
  "kg_max_depth": 5
}
```

### 9.3 数据流汇总

```
上传 → 处理 → 存储 → 检索 → 生成
 │       │       │       │      │
 │       │       │       │      └─ LLM 流式输出（SSE, 三模式）
 │       │       │       │
 │       │       │       ├─ RAG: Milvus Lite 稠密+稀疏 → RRF → 批量Reranker
 │       │       │       ├─ KG:  Neo4j BFS → 关系文本 → Agent 生成
 │       │       │       └─ NL2SQL: LLM 生成 SQL → pyodbc → 表格+图表
 │       │       │
 │       │       ├─ SQLite: 文档/分块/日志/用户
 │       │       ├─ Milvus Lite: 稠密向量 + BM25 稀疏向量
 │       │       └─ Neo4j: 实体节点+关系边
 │       │
 │       ├─ vector: 分块 → 向量化（Milvus Lite）
 │       └─ graph:  LLM提取实体 → Neo4j
 │
 └─ 文件系统: 文档原件
```

### 9.4 路径说明

| 内容 | 路径 |
|------|------|
| 后端入口 | `backend/app/main.py` |
| 数据库文件 | `backend/sprag.db` |
| 向量数据 | `backend/milvus_lite.db` |
| 上传文档 | `backend/uploads/` |
| 运行时配置 | `backend/runtime_config.json` |
| NL2SQL 配置 | `backend/nl2sql_config.json` |
| 前端入口 | `frontend/src/main.js` |
| 路由定义 | `frontend/src/router/index.js` |
| API 客户端 | `frontend/src/api/index.js` |
