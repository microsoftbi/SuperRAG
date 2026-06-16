# 知识库功能 — 实现计划

## Task 1: 数据模型

- 创建 `backend/app/models/knowledge_base.py` — KnowledgeBase + 两个关联表
- 修改 `backend/app/models/document.py` — 添加多对多关系
- 更新 `models/__init__.py`

## Task 2: Schemas

- 创建 `backend/app/schemas/knowledge_base.py` — KB + 关联 Pydantic 模型
- 更新 `schemas/__init__.py`

## Task 3: API

- 创建 `backend/app/api/knowledge_bases.py` — KB CRUD
- 创建 `backend/app/api/users.py` — 用户列表 + 知识库权限分配
- 修改 `backend/app/api/documents.py` — 上传/列表支持知识库
- 修改 `backend/app/api/chat.py` — 检索时传入用户知识库范围

## Task 4: 检索适配

- 修改 `backend/app/services/vector_store.py` — similarity_search 支持 where_filter
- 修改 `backend/app/rag/retriever.py` — 增加知识库过滤
- 修改 `backend/app/rag/bm25_retriever.py` — 增加知识库过滤

## Task 5: 前端

- 创建 `frontend/src/components/admin/KnowledgeBaseManager.vue`
- 创建 `frontend/src/components/admin/UserManager.vue`
- 修改 `frontend/src/views/AdminView.vue` — 新增标签页
- 修改 `frontend/src/components/admin/DocumentUploader.vue` — 知识库多选
- 修改 `frontend/src/api/index.js` — 新增 API

## Task 6: 数据迁移 + 测试