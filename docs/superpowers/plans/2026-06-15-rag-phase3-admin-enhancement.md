# RAG 客服对话系统 — 实现计划 (Phase 3)

**Goal:** 完善管理后台，实现问答日志记录与查看、用户反馈收集、运行时参数配置

**Architecture:** 
- ConversationLog + Feedback ORM 模型（SQLite）
- 对话日志在 chat API 中自动记录
- 反馈 API（点赞/点踩 + 建议）
- 运行时配置 API（持久化到 JSON 文件）
- 前端管理后台增加日志查看、参数配置标签页

---

## Task 1: 数据模型（ConversationLog + Feedback）

**Files:**
- Create: `backend/app/models/conversation_log.py`
- Create: `backend/app/models/feedback.py`
- Create: `backend/app/schemas/conversation_log.py`
- Create: `backend/app/schemas/feedback.py`

## Task 2: 对话日志集成

**Files:**
- Modify: `backend/app/api/chat.py` — 记录日志
- Create: `backend/app/api/logs.py` — 日志查询 API

## Task 3: 反馈 API

**Files:**
- Create: `backend/app/api/feedback.py`

## Task 4: 运行时配置 API

**Files:**
- Create: `backend/app/services/runtime_config.py`
- Create: `backend/app/api/config.py`

## Task 5: 前端 — 管理后台标签页重构

**Files:**
- Modify: `frontend/src/views/AdminView.vue` — 标签页导航
- Create: `frontend/src/components/admin/LogViewer.vue`
- Create: `frontend/src/components/admin/SettingsPanel.vue`
- Create: `frontend/src/components/admin/FeedbackPanel.vue`
- Modify: `frontend/src/components/chat/MessageBubble.vue` — 反馈按钮
- Modify: `frontend/src/api/index.js` — 新 API

## Task 6: 测试
