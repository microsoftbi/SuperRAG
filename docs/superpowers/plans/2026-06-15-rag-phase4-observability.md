# RAG 客服对话系统 — 实现计划 (Phase 4)

**Goal:** 构建可观测性仪表盘，实现检索质量分析、趋势图表、轻量告警

**Architecture:**
- Stats API: 聚合 ConversationLog + Feedback 数据
- Dashboard 前端: 调用量/延迟/命中率/满意度图表
- Alert API: 简单异常检测

---

## Task 1: Stats API

**Files:**
- Create: `backend/app/api/stats.py`

聚合指标：
- 每日调用量
- 平均/最大/P95 延迟
- 检索命中率（有结果 vs 空结果）
- 满意度趋势（按天）
- Top 文档分类统计

## Task 2: Alert API

**Files:**
- Create: `backend/app/api/alerts.py`

检测规则：
- 最近 10 条平均延迟 > 10s → 告警
- 最近 10 条空结果率 > 50% → 告警
- 最近 10 条满意度 < 30% → 告警

## Task 3: 前端 Dashboard

**Files:**
- Create: `frontend/src/components/admin/DashboardView.vue`
- Modify: `frontend/src/views/AdminView.vue` — 新增仪表盘标签
- Modify: `frontend/src/api/index.js` — stats/alert API
