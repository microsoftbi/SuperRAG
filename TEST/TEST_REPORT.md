# SuperRAG 自动化测试报告

**日期**: 2026-06-24
**测试范围**: NL2SQL 行数限制 + 问数图表(make_chart)+ 知识图谱节点/关系维护 API
**测试框架**: pytest 9.0.2 (Python 3.11.15)
**测试目录**: `backend/tests/`

---

## 一、总体结果

| 指标 | 值 |
|---|---|
| **测试总数** | 52 |
| ✅ **通过** | **52 (100%)** |
| ❌ 失败 | 0 |
| ⚠ Error | 0 |
| ⏱ 总耗时 | 14.12 秒 |
| 警告 | 8(均为第三方库 deprecation,与本项目无关) |

```
======================= 52 passed, 8 warnings in 14.12s ========================
```

---

## 二、新增测试文件

| 文件 | 用例数 | 覆盖功能 |
|---|---:|---|
| `tests/test_knowledge_graph_api.py` | 15 | KG 节点/关系维护 API(本次新增) |
| `tests/test_make_chart_tool.py` | 10 | 问数图表 make_chart 工具(本次新增) |
| `tests/test_nl2sql_limits.py` | 15 | NL2SQL 行数限制 + TOP 注入(本次新增) |
| **新增合计** | **40** | — |
| 旧有测试 | 12 | RAG/BM25/重排/查询改写/文档处理/Chat API |
| **测试总计** | **52** | |

---

## 三、详细用例与结果

### 3.1 NL2SQL 行数限制(`test_nl2sql_limits.py`) — 15 / 15 ✅

#### A. `TestEnsureTopLimit` — TOP 子句注入与夹紧(8)

| # | 用例 | 验证内容 | 结果 |
|--:|---|---|:--:|
| 1 | `test_inject_when_no_top` | SQL 无 TOP 时自动注入 `TOP {max_rows}` | ✅ |
| 2 | `test_keep_when_top_within_limit` | TOP N ≤ 上限,保留不动 | ✅ |
| 3 | `test_clamp_when_top_exceeds_limit` | TOP N > 上限,夹紧为上限 | ✅ |
| 4 | `test_distinct_keyword` | `SELECT DISTINCT` 后正确注入 TOP | ✅ |
| 5 | `test_lowercase_sql` | 大小写不敏感的 SQL 解析 | ✅ |
| 6 | `test_leading_whitespace` | 前导空格不破坏注入 | ✅ |
| 7 | `test_top_equal_to_limit` | TOP N == 上限,保留 | ✅ |
| 8 | `test_complex_select_with_join` | 含 JOIN 的复杂 SQL 也能注入 | ✅ |

#### B. `TestThreadCache` — 按 thread 缓存查询结果(5)

| # | 用例 | 验证内容 | 结果 |
|--:|---|---|:--:|
| 9 | `test_cache_and_retrieve` | 写入后能取回相同数据 | ✅ |
| 10 | `test_unknown_thread` | 未知 thread_id 返回 None | ✅ |
| 11 | `test_none_thread_id_noop` | `thread_id=None` 不缓存且不报错 | ✅ |
| 12 | `test_lru_eviction` | 超过 20 个 thread 时按插入序淘汰 | ✅ |
| 13 | `test_update_moves_to_end` | 重写已有 key 刷新位置,不被淘汰 | ✅ |

#### C. `reset_tool_state`(2)

| # | 用例 | 验证内容 | 结果 |
|--:|---|---|:--:|
| 14 | `test_reset_tool_state_sets_thread_id` | 设置 thread_id 并清空 sources/minigraph | ✅ |
| 15 | `test_reset_tool_state_none` | 传 None 时正确清空 | ✅ |

---

### 3.2 问数图表 make_chart 工具(`test_make_chart_tool.py`) — 10 / 10 ✅

#### A. 正常路径(4)

| # | 用例 | 验证内容 | 结果 |
|--:|---|---|:--:|
| 1 | `test_make_chart_bar` | 单 Y 字段柱图 spec 生成正确(title/x/y/data) | ✅ |
| 2 | `test_make_chart_multiple_y` | 多 Y 字段(堆叠柱图)保留全部 | ✅ |
| 3 | `test_make_chart_pie_single_y_only` | 饼图传多 Y 时自动取首个 | ✅ |
| 4 | `test_make_chart_default_title` | 不传 title 自动生成 "{Y} 按 {X}" | ✅ |

#### B. 校验失败(5)

| # | 用例 | 验证内容 | 结果 |
|--:|---|---|:--:|
| 5 | `test_make_chart_no_data` | 无缓存数据 → "没有可用的查询结果" 警告 | ✅ |
| 6 | `test_make_chart_invalid_type` | 非法 chart_type → "不支持的图表类型" | ✅ |
| 7 | `test_make_chart_invalid_x_field` | X 字段不存在 → "不在结果列中" | ✅ |
| 8 | `test_make_chart_invalid_y_field` | 任一 Y 字段不存在 → 报错 | ✅ |
| 9 | `test_make_chart_empty_y` | Y 字段为空 → "不能为空" | ✅ |

#### C. 序列化(1)

| # | 用例 | 验证内容 | 结果 |
|--:|---|---|:--:|
| 10 | `test_make_chart_spec_is_json_serializable` | 含 Decimal/datetime 的数据可 `json.dumps` 不抛错 | ✅ |

---

### 3.3 知识图谱维护 API(`test_knowledge_graph_api.py`) — 15 / 15 ✅

#### A. 节点维护(7)

| # | 用例 | 验证内容 | 结果 |
|--:|---|---|:--:|
| 1 | `test_create_entity` | POST `/entities` 创建节点 | ✅ |
| 2 | `test_update_entity_rename_ok` | PUT 改名:保留 internal_id,关系里源/目标名同步更新 | ✅ |
| 3 | `test_update_entity_rename_conflict` | 改名为已存在名 → 409 + 中文错误"已被" | ✅ |
| 4 | `test_update_entity_type_only` | 类型字段允许自定义(如"客户") | ✅ |
| 5 | `test_update_entity_not_found` | 不存在的 entity_id → 404 | ✅ |
| 6 | `test_delete_entity_cascade` | DELETE 节点 → 级联删除其所有关系 | ✅ |
| 7 | `test_delete_entity_not_found` | 删除不存在节点 → 404 | ✅ |

#### B. 关系维护(4)

| # | 用例 | 验证内容 | 结果 |
|--:|---|---|:--:|
| 8 | `test_relationship_count` | GET `/entities/{id}/relationship-count` 返回准确数量 | ✅ |
| 9 | `test_create_relationship` | POST `/relationships` 创建关系 | ✅ |
| 10 | `test_update_relationship_ok` | PUT 改类型:旧关系删除 + 新关系建立 | ✅ |
| 11 | `test_update_relationship_not_found` | 改不存在关系 → 404 | ✅ |
| 12 | `test_delete_relationship` | DELETE `/relationships` 删除指定关系 | ✅ |

#### C. 错误场景 & 端到端(3)

| # | 用例 | 验证内容 | 结果 |
|--:|---|---|:--:|
| 13 | `test_neo4j_unavailable` | Neo4j 未初始化时 PUT/DELETE 等接口返 503 | ✅ |
| 14 | `test_update_entity_validation` | 缺必填字段 → Pydantic 422 | ✅ |
| 15 | `test_full_node_lifecycle` | 完整流程:新建 → 改名 → 加关系 → 改关系类型 → 删除(级联) | ✅ |

---

### 3.4 旧有测试(回归)— 12 / 12 ✅

| 文件 | 用例 | 结果 |
|---|---|:--:|
| `test_bm25_retriever.py` | `test_bm25_tokenize` | ✅ |
| `test_bm25_retriever.py` | `test_bm25_initial_state` | ✅ |
| `test_chat_api.py` | `test_health_endpoint` | ✅ |
| `test_chat_api.py` | `test_upload_unsupported_file` | ✅ |
| `test_document_processor.py` | `test_extract_text_from_txt` | ✅ |
| `test_document_processor.py` | `test_extract_text_unsupported` | ✅ |
| `test_hybrid_retriever.py` | `test_hybrid_rrf_scoring` | ✅ |
| `test_query_rewriter.py` | `test_rewrite_no_history` | ✅ |
| `test_query_rewriter.py` | `test_rewrite_single_message` | ✅ |
| `test_reranker.py` | `test_reranker_parse_score` | ✅ |
| `test_reranker.py` | `test_reranker_empty_results` | ✅ |
| `test_retriever.py` | `test_retriever_returns_list` | ✅ |

---

## 四、测试设计要点

### 4.1 KG API 测试 — `FakeNeo4jService` in-memory 仿真

- **零外部依赖**:用一个内存版 FakeNeo4jService 替换真实 Neo4j 驱动,通过 `monkeypatch` 注入到 `_neo4j_service` 模块变量
- **真正过路由层**:FastAPI `TestClient` 发 HTTP 请求,经过完整的路由分发 + Pydantic 校验 + HTTPException 处理
- **权限绕开**:`app.dependency_overrides[require_admin]` 注入 mock admin,不需要建真实数据库用户
- **关键回归点都锁住**:
  - 改名后 Fake 会同步更新 rels 里的源/目标名(对齐真实 Neo4j 按 internal_id 引用的行为)
  - 重名冲突走 409 + 错误消息含"已被"
  - 删节点级联删边

### 4.2 NL2SQL 限制测试 — 纯单元测试

- **SQL 解析** 用 6 种典型场景覆盖正则边界:`SELECT`、`SELECT DISTINCT`、大小写混合、前导空格、与上限相等
- **LRU 行为** 验证两个微妙点:(1) 第 21 个进入时第 1 个被淘汰;(2) 重写已存在 key 应该刷新位置不被淘汰
- **JSON 友好性** 显式构造含 `Decimal` 和 `datetime` 的数据,验证 chart spec 可序列化(防止 SQL Server 返回 Decimal 时炸服务)

### 4.3 make_chart 测试 — 工具直接调用

- 用 `build_nl2sql_tools()` 取出工具实例,用 LangChain `.invoke()` 方式调用,不经过 LLM
- 预置 thread 缓存模拟"刚执行完 query_database"的状态
- 9 个错误场景全部测试,确保 LLM 传入不合理参数时返回友好提示

---

## 五、警告说明

报告中 8 条警告均为**第三方库的 deprecation**,与项目代码无关:

| 来源 | 警告 |
|---|---|
| pydantic v2 | `class-based config is deprecated`(passlib 内部使用) |
| passlib | `'crypt' is deprecated`(Python 3.13 准备移除) |
| neo4j-driver | 包名建议改为 `neo4j` |

不影响功能,不计入失败。

---

## 六、运行命令

```bash
# 跑本次新增的 40 个用例
cd backend
python3.11 -m pytest tests/test_knowledge_graph_api.py \
                     tests/test_make_chart_tool.py \
                     tests/test_nl2sql_limits.py -v

# 跑全套
python3.11 -m pytest tests/ -v
```

---

## 七、结论

✅ **本轮 3 个新功能(NL2SQL 行数限制、问数图表、KG 节点/关系维护)的 40 个新增测试全部通过**;
✅ **全套 52 个测试 100% 通过,无回归**;
✅ **平均单用例耗时 0.27 秒**,运行快,适合 CI/CD 集成。
