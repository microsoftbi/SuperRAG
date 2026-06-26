# SuperRAG 客服对话 RAG + KG + NL2SQL 系统

面向终端客户的智能客服问答系统，基于 **RAG（检索增强生成）+ 知识图谱（Neo4j）** 双引擎 + **NL2SQL（自然语言问数）** 三合一架构。

## 技术栈

- **后端**：Python, FastAPI, LangChain / deepagents, Milvus Lite（向量库）, Neo4j（图谱）, SQLAlchemy, SQLite, pyodbc + FreeTDS（SQL Server）
- **前端**：Vue 3, Vite, vis-network（图谱可视化）
- **LLM**：火山引擎 API（豆包大模型 / DeepSeek）
- **Agent 框架**：deepagents v0.5+（三 Agent：RAG / KG / NL2SQL，独立 checkpointer）

## 快速启动

### 前置条件

- Python 3.11+
- Node.js 18+
- 火山引擎方舟平台 API 密钥
- Neo4j 数据库（可选，图谱引擎需要）

### 后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # 编辑 .env 填入火山引擎密钥 + Neo4j 密码
python run.py               # http://localhost:8000
```

### 前端

```bash
cd frontend 
npm install
npm run dev                 # http://localhost:5173
```

### 默认管理员账号

```
用户名: admin
密码:   admin123
```

## 项目结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口（三 Agent 初始化）
│   ├── config.py            # 配置（Neo4j / LLM / 分块参数 / Milvus）
│   ├── database.py          # 数据库（含自动迁移）
│   ├── models/              # ORM 模型
│   ├── schemas/             # Pydantic 模式
│   ├── api/
│   │   ├── chat.py          # 问答入口（三模式：rag / kg / nl2sql）
│   │   ├── documents.py     # 文档管理（含 KG 实体提取）
│   │   ├── knowledge_graph.py # KG 管理 API（含 Node/Edge 维护）
│   │   ├── nl2sql.py        # NL2SQL 配置 API
│   │   └── ...
│   ├── agents/              # deepagents 集成
│   │   ├── agent_factory.py # 三 Agent：RAG / KG / NL2SQL（独立 checkpointer）
│   │   └── tools.py         # 工具函数（RAG检索 / KG检索 / NL2SQL问数+图表）
│   ├── rag/                 # RAG 引擎（向量+BM25）
│   │   ├── retriever.py, generator.py, document_processor.py ...
│   │   ├── hybrid_retriever.py  # RRF 融合检索
│   │   ├── reranker.py      # LLM 批量重排序
│   │   ├── bm25_retriever.py    # BM25EmbeddingFunction(language="zh")
│   │   └── query_rewriter.py    # LLM 查询改写
│   ├── kg/                  # 知识图谱引擎
│   │   ├── entity_extractor.py  # 实体提取
│   │   └── graph_retriever.py   # 图遍历检索（仅返回关系文本）
│   └── services/
│       ├── neo4j_service.py # Neo4j 连接/读写
│       ├── vector_store.py  # Milvus Lite 向量库（稠密+稀疏双向量）
│       ├── nl2sql_config.py # NL2SQL 配置持久化
│       └── runtime_config.py # 运行时配置（含 nl2sql_max_rows）
└── tests/
frontend/
├── src/
│   ├── views/
│   │   ├── ChatView.vue     # 对话页（三 Tab：RAG / 知识图谱 / 问数）
│   │   └── AdminView.vue    # 管理后台
│   ├── components/
│   │   ├── admin/
│   │   │   ├── Nl2SqlPanel.vue         # NL2SQL 配置面板
│   │   │   ├── SettingsPanel.vue       # 参数配置（含 nl2sql_max_rows）
│   │   │   ├── LogViewer.vue           # 问答日志（含 NL2SQL 详情）
│   │   │   ├── DocumentChunkViewer.vue # 文档分块查看
│   │   │   ├── KnowledgeGraphViewer.vue# 全景图谱（graph/nodes/edges 三 Tab）
│   │   │   ├── KgNodeTable.vue         # 节点维护（CRUD + 批量删除）
│   │   │   ├── KgEdgeTable.vue         # 关系维护（修改类型 + 批量删除）
│   │   │   └── ...
│   │   └── chat/
│   │       ├── ChatWindow.vue          # RAG+KG 聊天窗
│   │       ├── Nl2SqlChat.vue          # 问数 聊天窗
│   │       ├── MessageBubble.vue       # 消息气泡（含结果表格 + ECharts 图表）
│   │       ├── SessionSidebar.vue      # 会话侧边栏（按 mode 隔离）
│   │       ├── MiniGraphModal.vue      # 图谱弹窗
│   │       └── ...
│   └── api/                 # API 客户端
```

## 系统架构

```
┌───────────────────────────────────────────────────────────┐
│                     ChatView.vue                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  [RAG] Tab   │  │ [知识图谱]   │  │  [问数] Tab  │    │
│  │ ChatWindow   │  │  ChatWindow  │  │ Nl2SqlChat   │    │
│  │ rag_session  │  │ kg_session   │  │ nl2sql_session│    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                  │            │
│         ▼                 ▼                  ▼            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ deepagent A  │  │ deepagent B  │  │ deepagent C  │    │
│  │ RAG Agent    │  │ KG Agent     │  │ NL2SQL Agent │    │
│  │ 独立checkpointer│  │独立checkpointer│  │独立checkpointer│    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼──────────────────┼──────────────────┼──────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐
│ RAG 引擎      │  │ KG 引擎      │  │ NL2SQL 引擎           │
│ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────────────┐ │
│ │ Milvus   │ │  │ │ Neo4j    │ │  │ │ LLM 生成 SQL     │ │
│ │ 稠密+稀疏 │ │  │ │ 图遍历    │ │  │ │ pyodbc 执行      │ │
│ │ BM25 中文 │ │  │ │ 关系文本  │ │  │ │ 表格+图表渲染    │ │
│ └──────────┘ │  │ └──────────┘ │  │ └──────────────────┘ │
│ 批量重排序   │  │  无chunk原文  │  │  TOP N 行数限制      │
└──────────────┘  └──────────────┘  └──────────────────────┘
```

### 核心特性

| 特性 | 说明 |
|------|------|
| **RAG 引擎** | 文档分块 → 向量化(Milvus Lite 稠密+稀疏) + BM25EmbeddingFunction(language="zh") 混合检索 → 批量 LLM 重排序 → 生成回答 |
| **KG 引擎** | LLM 实体提取 → Neo4j 图数据库 → 图遍历（可配深度 2-6）→ 仅返回关系文本（不再查 chunk 原文） |
| **NL2SQL 问数** | 独立 deepagent → 动态拼提示词（schema+术语+示例）→ LLM 生成 SQL → pyodbc 执行 SQL Server → 格式化表格 + ECharts 图表 |
| **三对话 Tab** | RAG / 知识图谱 / 问数 三 Tab，独立会话历史，KG 不可用时 Tab 置灰 |
| **会话持久化** | deepagents AsyncSqliteSaver + ConversationLog 表，刷新恢复历史 |
| **知识库权限** | 文档用户组隔离，管理员可分配知识库访问权限 |
| **NL2SQL 图表** | 用户触发 make_chart 工具，ECharts 渲染（柱图/饼图/折线图/面积图/散点图） |
| **NL2SQL 行数限制** | LLM 生成的 SQL 自动注入 TOP N，管理后台可配范围 50-1000 |
| **KG 节点维护** | 管理后台 graph/nodes/edges 三 Tab，支持 CRUD + 批量删除 |

## 配置

### 环境变量 `.env`

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `VOLC_API_KEY` | 火山引擎 API 密钥 | `4abb27fb-xxxx` |
| `VOLC_ENDPOINT` | API 地址 | `https://ark.cn-beijing.volces.com/api/v3` |
| `LLM_MODEL_NAME` | 对话模型 ID | `ep-xxxx-xxxxx` |
| `EMBEDDING_MODEL_NAME` | Embedding 模型 ID | `ep-xxxx-xxxxx` |
| `NEO4J_URI` | Neo4j 连接地址 | `bolt://localhost:7687` |
| `NEO4J_USER` | Neo4j 用户名 | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j 密码 | `your_password` |
| `MILVUS_LITE_URI` | Milvus Lite 存储路径 | `./milvus_lite.db` |
| `EMBEDDING_DIM` | Embedding 向量维度 | `2048` |

### 运行时配置 `runtime_config.json`

管理员在管理后台「参数配置」页面调整，保存立即生效：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `nl2sql_detail_logging` | 问数明细日志（SQL+提示词）开关 | `false` |
| `nl2sql_max_rows` | NL2SQL 查询最大行数限制 | `50`（范围 50-1000） |
| `kg_max_depth` | 知识图谱遍历深度 | `5`（范围 2-6） |

### NL2SQL 配置 `nl2sql_config.json`

管理员在管理后台「NL2SQL」页面配置，包含：

- 数据库连接（SQL Server 地址/端口/账号/库名）
- 提示词三件套：字段结构 / 专业术语 / Q&A示例
