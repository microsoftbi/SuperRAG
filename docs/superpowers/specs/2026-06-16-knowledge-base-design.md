# SPRAG 客服对话系统 — 设计文档：知识库与权限集成

## 概述

将文档的 `category` 字段升级为正式的知识库（Knowledge Base）实体，实现多对多关系。用户权限与知识库绑定，用户只能检索被分配的知识库中的内容。

## 数据模型

### knowledge_bases 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增主键 |
| name | String(100) | 知识库名称，唯一 |
| description | Text | 描述 |
| created_at | DateTime | |
| updated_at | DateTime | |

### document_knowledge_base 表（多对多）

| 字段 | 类型 | 说明 |
|------|------|------|
| document_id | Integer FK | → documents.id |
| knowledge_base_id | Integer FK | → knowledge_bases.id |

复合主键 `(document_id, knowledge_base_id)`

### user_knowledge_base 表（多对多）

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | Integer FK | → users.id |
| knowledge_base_id | Integer FK | → knowledge_bases.id |

复合主键 `(user_id, knowledge_base_id)`

## Document 模型变更

- 保留 `category` 字段（兼容旧数据）
- 新增 `knowledge_bases` 关系（多对多）
- 前端上传时，`category` 输入框被替换为知识库多选下拉

## 权限逻辑

| 角色 | 知识库权限 |
|------|-----------|
| admin | 管理所有知识库（CRUD）；可向任意知识库上传文档；对话时检索全部 |
| user | 仅检索被分配的知识库中的文档；看不到未被分配的知识库内容 |

## API 设计

### 知识库管理（仅 admin）

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/knowledge-bases` | 列表（admin 全部，user 仅被分配的） |
| POST | `/api/v1/knowledge-bases` | 创建 {name, description} |
| PUT | `/api/v1/knowledge-bases/{id}` | 编辑 |
| DELETE | `/api/v1/knowledge-bases/{id}` | 删除（级联关联关系） |

### 文档-知识库关联

- 文档上传/编辑时，支持传入 `knowledge_base_ids: list[int]`
- GET `/api/v1/documents` 增加 `knowledge_base_id` 筛选

### 用户-知识库分配（仅 admin）

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/users` | 用户列表（admin 管理用） |
| PUT | `/api/v1/users/{id}/knowledge-bases` | 设置用户的知识库权限 {knowledge_base_ids: [...]} |
| GET | `/api/v1/users/{id}/knowledge-bases` | 查看用户的知识库权限 |

### 检索变化

由于文档 ↔ 知识库是多对多关系（存在 SQLite 关联表中），而每个 Chunk 在 ChromaDB 中只存了 `document_id`，检索策略如下：

```python
# 1. 通过 SQLite 查询用户有权限的文档 ID
document_ids = (
    db.query(document_knowledge_base.c.document_id)
    .filter(document_knowledge_base.c.knowledge_base_id.in_(user_kb_ids))
    .distinct()
    .all()
)

# 2. 在 ChromaDB 中按 document_id 过滤
results = self.collection.query(
    query_embeddings=[query_embedding],
    n_results=top_k,
    where={"document_id": {"$in": document_ids}},
    include=["documents", "metadatas", "distances"],
)

# 3. BM25 同理，从 SQLite chunks 中按 document_id 过滤
```

`Retriever.retrieve()` 和 `VectorStoreService.similarity_search()` 增加可选的 `where_filter` 参数。

## 前端变更

### 新增标签页

管理后台新增「知识库管理」标签：

```
知识库列表
┌─────────────────────────────────────────────┐
│ 名称           │ 描述        │ 文档数 │ 操作 │
├─────────────────────────────────────────────┤
│ 产品手册       │ ...         │ 12     │ 编辑│
│ 售后政策       │ ...         │ 5      │ 编辑│
│ 技术文档       │ ...         │ 8      │ 编辑│
└─────────────────────────────────────────────┘
[ + 新建知识库 ]
```

### 用户管理标签页

管理后台新增「用户管理」标签：

```
用户列表
┌─────────────────────────────────────────────┐
│ 用户名  │ 邮箱         │ 角色  │ 知识库权限 │
├─────────────────────────────────────────────┤
│ admin   │ admin@...    │ admin │ 全部      │
│ zhangsan│ zhang@...    │ user  │ [选择...] │
└─────────────────────────────────────────────┘
```

### 文档上传变更

```
上传文档
┌─────────────────────────────────┐
│ [选择文件]  test.pdf            │
│ 标题: [iPhone 15 使用手册]      │
│ 知识库: [✓ 产品手册] [✓ 技术支持]│
│         [  售后政策  ]          │
│                                 │
│ [       上  传       ]          │
└─────────────────────────────────┘
```

### 对话界面

用户对话时，顶部显示当前可用的知识库：

```
SPRAG 客服助手                     admin | 退出
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[📚 产品手册] [📚 售后政策] [📚 技术文档]
```

但普通用户只看得到自己被分配的知识库。

## 数据迁移

已有文档的 `category` 字段保留不动，系统自动创建一个同名的知识库并关联旧文档：

```python
def migrate_categories():
    """One-time migration: category → knowledge_base."""
    categories = db.query(Document.category).distinct().all()
    for (cat,) in categories:
        kb = KnowledgeBase(name=cat)
        db.add(kb)
        db.flush()
        documents = db.query(Document).filter(Document.category == cat).all()
        for doc in documents:
            db.execute(document_knowledge_base.insert().values(
                document_id=doc.id, knowledge_base_id=kb.id
            ))
```

## 文件变更清单

### 后端新增

| 文件 | 说明 |
|------|------|
| `app/models/knowledge_base.py` | KnowledgeBase + 关联表 |
| `app/schemas/knowledge_base.py` | Pydantic schemas |
| `app/api/knowledge_bases.py` | 知识库 CRUD API |
| `app/api/users.py` | 用户列表 + 权限分配 |

### 后端修改

| 文件 | 修改内容 |
|------|----------|
| `app/models/document.py` | 添加多对多关系 |
| `app/schemas/document.py` | 添加 knowledge_base_ids 字段 |
| `app/api/documents.py` | 上传/列表支持知识库 |
| `app/rag/document_processor.py` | 在 metadata 中写入 |
| `app/rag/retriever.py` | 增加 knowledge_base_ids 过滤 |
| `app/rag/bm25_retriever.py` | 增加知识库过滤 |
| `app/api/chat.py` | 获取用户的知识库并传给检索 |

### 前端新增

| 文件 | 说明 |
|------|------|
| `src/components/admin/KnowledgeBaseManager.vue` | 知识库管理 |
| `src/components/admin/UserManager.vue` | 用户管理 + 权限分配 |

### 前端修改

| 文件 | 修改内容 |
|------|----------|
| `src/views/AdminView.vue` | 新增标签页 |
| `src/components/admin/DocumentUploader.vue` | 知识库多选 |
| `src/components/chat/ChatWindow.vue` | 显示当前知识库 |
| `src/api/index.js` | 新增 API 函数 |