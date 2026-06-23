# SPRAG → SuperRAG — 客服对话 RAG + KG + NL2SQL 系统

面向终端客户的智能客服问答系统，基于 **RAG（检索增强生成）+ 知识图谱（Neo4j）** 双引擎 + **NL2SQL（自然语言问数）** 三合一架构。

## 技术栈

- **后端**：Python, FastAPI, LangChain / deepagents, ChromaDB, Neo4j, SQLAlchemy, SQLite, pyodbc + FreeTDS（SQL Server）
- **前端**：Vue 3, Vite, vis-network（图谱可视化）
- **LLM**：火山引擎 API（豆包大模型 / DeepSeek）
- **Agent 框架**：deepagents v0.5+（双 Agent：RAG/KG + NL2SQL，独立 checkpointer）

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
│   ├── main.py              # FastAPI 入口（双 Agent 初始化）
│   ├── config.py            # 配置（Neo4j / LLM / 分块参数）
│   ├── database.py          # 数据库（含自动迁移）
│   ├── models/              # ORM 模型
│   ├── schemas/             # Pydantic 模式
│   ├── api/
│   │   ├── chat.py          # 问答入口（双模式：rag / nl2sql）
│   │   ├── documents.py     # 文档管理（含 KG 实体提取）
│   │   ├── knowledge_graph.py # KG 管理 API
│   │   ├── nl2sql.py        # NL2SQL 配置 API
│   │   └── ...
│   ├── agents/              # deepagents 集成
│   │   ├── agent_factory.py # 双 Agent：RAG/KG + NL2SQL
│   │   └── tools.py         # 工具函数（RAG检索 / KG检索 / NL2SQL问数）
│   ├── rag/                 # RAG 引擎（向量+BM25）
│   │   ├── retriever.py, generator.py, document_processor.py ...
│   ├── kg/                  # 知识图谱引擎
│   │   ├── entity_extractor.py  # 实体提取
│   │   ├── graph_retriever.py   # 图遍历检索
│   │   └── graph_generator.py   # KG 生成
│   └── services/
│       ├── neo4j_service.py # Neo4j 连接/读写
│       ├── nl2sql_config.py # NL2SQL 配置持久化
│       └── runtime_config.py # 运行时配置
└── tests/
frontend/
├── src/
│   ├── views/
│   │   ├── ChatView.vue     # 对话页（双 Tab：RAG+图谱 / 问数）
│   │   └── AdminView.vue    # 管理后台
│   ├── components/
│   │   ├── admin/
│   │   │   ├── Nl2SqlPanel.vue         # NL2SQL 配置面板
│   │   │   ├── SettingsPanel.vue       # 参数配置
│   │   │   ├── LogViewer.vue           # 问答日志（含 NL2SQL 详情）
│   │   │   ├── DocumentChunkViewer.vue # 文档分块查看
│   │   │   ├── KnowledgeGraphViewer.vue# 全景图谱
│   │   │   └── ...
│   │   └── chat/
│   │       ├── ChatWindow.vue          # RAG+图谱 聊天窗
│   │       ├── Nl2SqlChat.vue          # 问数 聊天窗
│   │       ├── MessageBubble.vue       # 消息气泡（含结果表格）
│   │       ├── SessionSidebar.vue      # 会话侧边栏
│   │       ├── MiniGraphModal.vue      # 图谱弹窗
│   │       └── ...
│   └── api/                 # API 客户端
```

## 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                     ChatView.vue                          │
│  ┌──────────────┐  ┌──────────────┐                      │
│  │ [RAG+图谱] Tab│  │  [问数] Tab  │                      │
│  │ ChatWindow    │  │ Nl2SqlChat   │                      │
│  │ sessionId A   │  │ sessionId B  │                      │
│  └──────┬───────┘  └──────┬───────┘                      │
│         │                  │                              │
│         ▼                  ▼                              │
│  ┌──────────────┐  ┌──────────────┐                      │
│  │ deepagent A  │  │ deepagent B  │                      │
│  │ RAG/KG Agent  │  │ NL2SQL Agent  │                      │
│  │ 独立 checkpointer│  │ 独立 checkpointer│                     │
│  └──────┬───────┘  └──────┬───────┘                      │
└─────────┼──────────────────┼──────────────────────────────┘
          │                  │
          ▼                  ▼
┌──────────────────┐  ┌──────────────────┐
│ RAG + KG 引擎     │  │ NL2SQL 引擎      │
│ ┌────┐ ┌──────┐  │  │ ┌─────────────┐  │
│ │RAG │ │ KG   │  │  │ │ LLM 生成 SQL │  │
│ │Chr-│ │Neo4j │  │  │ │ pyodbc 执行  │  │
│ │oma │ │图遍历 │  │  │ │ 结果表格渲染  │  │
│ └────┘ └──────┘  │  │ └─────────────┘  │
└──────────────────┘  └──────────────────┘
```

### 核心特性

| 特性 | 说明 |
|------|------|
| **RAG 引擎** | 文档分块 → 向量化(ChromaDB) + BM25 混合检索 → 重排序 → 生成回答 |
| **KG 引擎** | LLM 实体提取 → Neo4j 图数据库 → 图遍历（可配深度 2-6）→ 关系回答 |
| **NL2SQL 问数** | 独立 deepagent → 动态拼提示词（schema+术语+示例）→ LLM 生成 SQL → pyodbc 执行 SQL Server → 格式化表格 |
| **双对话 Tab** | [RAG+图谱] 和 [问数] 共用页面，会话历史完全隔离 |
| **会话持久化** | deepagents AsyncSqliteSaver + ConversationLog 表，刷新恢复历史 |
| **知识库权限** | 文档用户组隔离，管理员可分配知识库访问权限 |

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

### 运行时配置 `runtime_config.json`

管理员在管理后台「参数配置」页面调整，保存立即生效：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `nl2sql_detail_logging` | 问数明细日志（SQL+提示词）开关 | `false` |
| `kg_max_depth` | 知识图谱遍历深度 | `5`（范围 2-6） |

### NL2SQL 配置 `nl2sql_config.json`

管理员在管理后台「NL2SQL」页面配置，包含：

- 数据库连接（SQL Server 地址/端口/账号/库名）
- 提示词三件套：字段结构 / 专业术语 / Q&A示例