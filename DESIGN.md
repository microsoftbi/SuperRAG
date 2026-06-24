# SPRAG 系统详细设计文档

> 版本：v0.3 | 更新日期：2026-06-17

---

## 目录

1. [系统架构](#1-系统架构)
2. [数据模型](#2-数据模型)
3. [API 设计](#3-api-设计)
4. [RAG 引擎](#4-rag-引擎)
5. [知识图谱引擎](#5-知识图谱引擎)
6. [路由调度](#6-路由调度)
7. [文档处理流程](#7-文档处理流程)
8. [前端设计](#8-前端设计)
9. [配置与部署](#9-配置与部署)

---

## 1. 系统架构

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      前端 (Vue 3 + Vite)                     │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ ChatView    │  │ AdminView    │  │ KnowledgeGraph    │  │
│  │ 对话界面     │  │ 管理后台      │  │ Viewer            │  │
│  └──────┬──────┘  └──────┬───────┘  └────────┬──────────┘  │
│         │                │                    │              │
│         ▼                ▼                    ▼              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Axios / SSE (Event Stream)              │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────┬──────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────┐
│                    后端 (FastAPI)                           │
│                                                             │
│  ┌──────────┐  ┌───────────┐  ┌────────────┐               │
│  │ API 路由  │  │ RAG 引擎   │  │ KG 引擎     │              │
│  │ chat.py   │  │ retriever │  │ query_     │              │
│  │ documents │  │ generator │  │ router.py  │              │
│  │ knowledge_│  │ document_ │  │ entity_    │              │
│  │ graph.py  │  │ processor │  │ extractor  │              │
│  └─────┬─────┘  └─────┬─────┘  │ graph_     │              │
│        │              │        │ retriever  │              │
│        │              │        │ graph_     │              │
│        │              │        │ generator  │              │
│        │              │        └──────┬─────┘              │
│        ▼              ▼               ▼                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              服务层 (Services)                        │  │
│  │  ┌───────────┐ ┌───────────┐ ┌──────────────────┐   │  │
│  │  │LLM Service│ │Vector     │ │Neo4j Service     │   │  │
│  │  │(火山引擎)  │ │Store      │ │(Bolt 协议)       │   │  │
│  │  └───────────┘ │(ChromaDB)  │ └──────────────────┘   │  │
│  │                └───────────┘                          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │                  │                    │
          ▼                  ▼                    ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐
│   SQLite     │  │  ChromaDB    │  │  Neo4j               │
│   sprag.db   │  │  chroma_db/  │  │  bolt://localhost    │
│  文档/用户/   │  │  向量索引     │  │  实体/关系图          │
│  日志/分块    │  │              │  │                      │
└──────────────┘  └──────────────┘  └──────────────────────┘
```

### 1.2 存储分层

| 存储 | 存储内容 | 访问方式 | 依赖 |
|------|---------|---------|------|
| SQLite | 用户、文档、知识库、分块、日志、反馈 | SQLAlchemy ORM | 无 |
| ChromaDB | 文档分块的嵌入向量 | VectorStoreService | `pip install chromadb` |
| Neo4j | 实体节点、关系边 | Neo4jService | `brew install neo4j` |
| 文件系统 | 上传文档原件（PDF/DOCX 等） | 直接文件读写 | 无 |
| JSON 文件 | 运行时配置参数 | runtime_config.py | 无 |

### 1.3 核心依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| fastapi | 0.104+ | Web 框架 |
| sqlalchemy | 2.0+ | ORM |
| neo4j | 5.20+ | Neo4j 驱动 |
| chromadb | 0.4+ | 向量数据库 |
| langchain | 0.1+ | 文本分块 |
| rank-bm25 | 0.2+ | 关键词检索 |
| openai | - | LLM 客户端（兼容火山引擎） |
| vis-network | - | 前端图谱可视化 |
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
| embedding_id | VARCHAR(100) | ChromaDB ID（仅向量文档） |
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
| **route** | **VARCHAR(10)** | **RAG/KG** |
| latency_ms | INTEGER | 响应延迟 |
| token_count | INTEGER | Token 数 |
| model | VARCHAR(100) | 模型名 |
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
| /chat | POST | 登录 | 流式问答（SSE） |
| **文档** | | | |
| /documents/upload | POST | 管理员 | 上传文档 (+ store 参数) |
| /documents | GET | 管理员 | 文档列表 (+ store 过滤) |
| /documents/{id} | DELETE | 管理员 | 删除文档 |
| **知识库** | | | |
| /knowledge-bases | GET/POST | 管理员 | 知识库 CRUD |
| /knowledge-bases/{id} | PUT/DELETE | 管理员 | 编辑/删除 |
| /knowledge-bases/{id}/documents | GET/PUT | 管理员 | 文档关联 |
| /knowledge-bases/{id}/users | GET/PUT | 管理员 | 用户权限 |
| **知识图谱** | | | |
| /knowledge-graph/graph | GET | 登录 | 全量图谱数据 |
| /knowledge-graph/entities/search | GET | 登录 | 搜索实体 |
| /knowledge-graph/entities/{id} | GET | 登录 | 实体详情 |
| /knowledge-graph/extract | POST | 管理员 | 重建全局图谱 |
| /knowledge-graph/entities | POST | 管理员 | 手动创建实体 |
| /knowledge-graph/relationships | POST | 管理员 | 手动创建关系 |
| /knowledge-graph/relationships | DELETE | 管理员 | 删除关系 |
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
data: {"type": "sources", "sources": [
  {
    "chunk_id": "2",
    "document_title": "知识图谱",
    "content": "[匹配] 苹果公司\n[实体] 苹果公司 --(创立)--> 乔布斯",
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
├── bm25_retriever.py       # BM25 关键词检索
├── reranker.py             # LLM 相关性重评分
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
    │     向量检索 (ChromaDB) ──┐
    │     BM25 关键词检索 ──────┤── RRF 融合
    │                           │
    │     Score(c) = Σ 1/(k + rank(c))
    │
    ├─ 3. Re-ranking（LLM 重排序）
    │     对 Top-K 结果逐条评分 0-10
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

---

## 5. 知识图谱引擎

### 5.1 文件：`backend/app/kg/`

```
kg/
├── __init__.py
├── query_router.py      # LLM 路由判断（RAG/KG）
├── entity_extractor.py  # 实体提取（全文→LLM→结构化）
├── graph_retriever.py   # 实体匹配 → 图遍历 → chunk 收集
└── graph_generator.py   # KG 专用 Prompt + 生成
```

### 5.2 处理流程

```
用户问题："库克跟苹果公司的关系"
    │
    ├─ Step 1: 路由判断（query_router.py）
    │     调 LLM 判断问题类型
    │     返回: {"route": "KG"}
    │
    ├─ Step 2: 实体匹配（neo4j_service.py）
    │     Cypher: MATCH (e:Entity) WHERE $query CONTAINS e.name
    │     匹配到: "库克"(person), "苹果公司"(product)
    │
    ├─ Step 3: 图遍历（neo4j_service.py）
    │     1跳: MATCH (e)-[r]-(neighbor)
    │     2跳: MATCH (e)-[*1..2]-(connected)
    │     返回: (库克)--接任-->(乔布斯)
    │           (苹果公司)--创立-->(乔布斯)
    │
    ├─ Step 4: Chunk 收集与打分（graph_retriever.py）
    │     从 Neo4j 实体节点读取 chunk_ids
    │     从 SQLite 查询 chunk 原文
    │     打分规则：
    │       种子实体自身 → 2.0
    │       1跳邻居路径   → 1.0
    │       2跳邻居       → 0.5
    │
    └─ Step 5: 生成（graph_generator.py）
         KG_SYSTEM_PROMPT + 关系描述 + 文档片段 → LLM 流式输出
```

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

### 5.4 打分与排序

```
种子实体自身 chunk          score = 2.0    ← 最高优先级
通过关系路径找到的 chunk     score = 1.0    ← 1跳邻居
2跳展开找到的 chunk          score = 0.5    ← 2跳邻居
```

### 5.5 关系路径文本格式化

```
[匹配] 苹果公司
[匹配] 库克
[实体] 库克 --(接任)--> 乔布斯
[实体] 苹果公司 --(创立)--> 乔布斯
[实体] 苹果公司 --(推出)--> iPhone
```

---

## 6. 路由调度

### 6.1 文件：`backend/app/api/chat.py`

```
@router.post("/chat")
def chat(request, user):
    │
    ├─ 1. 调用 QueryRouter.route(query)
    │     返回 "RAG" 或 "KG"
    │
    ├─ 2. if route == "KG" && Neo4j 已连接:
    │     ├─ graph_retriever.retrieve(query)
    │     ├─ if 有结果 → _handle_kg_response()
    │     └─ if 无结果 → fallback 到 RAG
    │
    └─ 3. if route == "RAG":
          └─ _handle_rag_response()
```

### 6.2 路由判断 Prompt

```text
系统：判断用户问题适合 RAG（事实检索）还是 KG（实体关系）。
      示例：
      - "退款流程是什么？" → RAG
      - "A项目的负责人是谁？" → KG
用户：问题：{query}
模型：{"route": "KG", "reason": "实体关系"}
```

### 6.3 容错

- QueryRouter 失败（LLM 异常）→ 默认走 RAG
- KG 检索无结果 → 自动降级到 RAG
- Neo4j 连接失败 → KG 功能关闭，全走 RAG

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
│  → ChromaDB       │   │  全文存 SQLite chunks   │
│  → BM25 索引      │   │  → 写入 Neo4j           │
└──────────────────┘   └────────────────────────┘
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

### 7.3 全文存储规则

- KG 文档不分块，原文存为 1 条 SQLite chunk 记录（`chunk_index=0`）
- entity 节点的 `chunk_ids` 指向该 chunk 的 ID
- 图检索时通过 chunk_id 回 SQLite 取原文

---

## 8. 前端设计

### 8.1 路由

| 路径 | 组件 | 说明 |
|------|------|------|
| `/login` | LoginView | 登录 |
| `/register` | RegisterView | 注册 |
| `/` | ChatView | 客服对话 |
| `/admin` | AdminView | 管理后台（8 个 Tab） |

### 8.2 管理后台 Tab

| Tab | 组件 | 说明 |
|-----|------|------|
| 仪表盘 | DashboardView | 统计卡片 + 趋势图 |
| 文档管理 | DocumentUploader + 内联表格 | 上传 + 列表（子标签: 向量/图谱） |
| 知识库 | KnowledgeBaseManager | CRUD + 文档/用户关联 |
| **知识图谱** | **KnowledgeGraphViewer** | **vis-network 全景图谱** |
| 用户管理 | UserManager | 用户 CRUD + 权限 |
| 问答日志 | LogViewer | 日志列表 + 详情 |
| 用户反馈 | FeedbackPanel | 反馈统计 + 列表 |
| 参数配置 | SettingsPanel | 运行时参数 |

### 8.3 图谱可视化技术选型

| 场景 | 库 | 说明 |
|------|-----|------|
| 管理后台全景图 | vis-network | Barnes-Hut 物理引擎，支持大规模图（200+节点） |
| 问答弹窗子图 | vis-network | 深度滑条控制展开层级，种子节点星形高亮 |

**对比 Cytoscape**：vis-network 的 Barnes-Hut 物理引擎在处理中等规模图时布局更自然，且 API 更简洁，适合子图动态切换。

### 8.4 vis-network 配置

```javascript
physics: {
  barnesHut: {
    gravitationalConstant: -4000,   // 节点间斥力
    centralGravity: 0.3,           // 向心力
    springLength: 180,             // 边理想长度
    springConstant: 0.04,          // 弹簧刚度
    damping: 0.09,                 // 阻尼
    avoidOverlap: 0.1,             // 避免重叠
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
CHROMA_PERSIST_DIR=./chroma_db
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
  "llm_temperature": 0.7
}
```

### 9.3 数据流汇总

```
上传 → 处理 → 存储 → 检索 → 生成
 │       │       │       │      │
 │       │       │       │      └─ LLM 流式输出（SSE）
 │       │       │       │
 │       │       │       └─ RAG: ChromaDB+BM25 → RRF → Reranker
 │       │       │       └─ KG:  Neo4j BFS → Chunk收集 → 格式化
 │       │       │
 │       │       ├─ SQLite: 文档/分块/日志/用户
 │       │       ├─ ChromaDB: 向量索引
 │       │       └─ Neo4j: 实体节点+关系边
 │       │
 │       ├─ vector: 分块 → 向量化
 │       └─ graph:  LLM提取实体 → Neo4j
 │
 └─ 文件系统: 文档原件
```

### 9.4 路径说明

| 内容 | 路径 |
|------|------|
| 后端入口 | `backend/app/main.py` |
| 数据库文件 | `backend/sprag.db` |
| 向量数据 | `backend/chroma_db/` |
| 上传文档 | `backend/uploads/` |
| 运行时配置 | `backend/runtime_config.json` |
| 前端入口 | `frontend/src/main.js` |
| 路由定义 | `frontend/src/router/index.js` |
| API 客户端 | `frontend/src/api/index.js` |