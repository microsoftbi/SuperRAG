# backend/app/agents/tools.py
"""Tools for the deep agent: wraps RAG retriever and KG graph_retriever.

Tools 通过 ContextVar 共享当前请求的 sources / kg_paths / minigraph，
agent 流式响应结束后由 chat.py 从 ContextVar 读取并推送给前端。
"""

import json
import logging
import re

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# 当前请求的工具调用收集（模块级变量，每次 chat 请求 reset）
# deepagents 工具在同步上下文中执行，使用模块变量即可安全传递
_current_sources: list[dict] = []
_current_kg_minigraph: dict | None = None
_current_thread_id: str | None = None
_current_retrieval_detail: dict | None = None

# 按 thread_id 缓存上一次 query_database 的完整结果数据，供 make_chart 复用
# 简易 LRU：超过 _THREAD_CACHE_MAX 时按插入顺序淘汰
_THREAD_CACHE_MAX = 20
_thread_last_data: dict[str, dict] = {}


def reset_tool_state(thread_id: str | None = None):
    """每次 chat 请求开始时调用，重置收集状态并绑定当前 thread_id。"""
    global _current_sources, _current_kg_minigraph, _current_thread_id, _current_retrieval_detail
    _current_sources = []
    _current_kg_minigraph = None
    _current_thread_id = thread_id
    _current_retrieval_detail = None


def get_collected_sources() -> list[dict]:
    return _current_sources


def get_collected_kg_minigraph() -> dict | None:
    return _current_kg_minigraph


def get_retrieval_detail() -> dict | None:
    return _current_retrieval_detail


def cache_retrieval_detail(detail: dict | None):
    """供 chat.py fallback 路径设置 retrieval_detail。"""
    global _current_retrieval_detail
    if detail:
        _current_retrieval_detail = detail


def _cache_thread_data(thread_id: str | None, data: list[dict], columns: list[dict]) -> None:
    """缓存 thread 的最新查询结果。"""
    if not thread_id:
        return
    global _thread_last_data
    if thread_id in _thread_last_data:
        _thread_last_data.pop(thread_id)
    _thread_last_data[thread_id] = {"data": data, "columns": columns}
    while len(_thread_last_data) > _THREAD_CACHE_MAX:
        _thread_last_data.pop(next(iter(_thread_last_data)))


def _get_thread_data(thread_id: str | None) -> dict | None:
    if not thread_id:
        return None
    return _thread_last_data.get(thread_id)


def build_nl2sql_tools():
    logger.info("build_nl2sql_tools")
    """构建 NL2SQL deepagents tools。"""

    @tool
    def query_database(natural_language_query: str) -> str:
        """从数据仓库中查询业务数据。

        适用场景：
        - 用户需要查询销售额、客户统计、报表数据等业务数据
        - 用户问"多少"、"哪些"、"排名"、"统计"等量化问题

        Args:
            natural_language_query: 用户的自然语言问题，应保留完整上下文。

        Returns:
            查询结果文本（SQL + 结果数据），可在最终回答中引用。
        """
        logger.info("query_database called: query=%s", natural_language_query[:60])

        from app.services.nl2sql_config import load_nl2sql_config
        from app.services.runtime_config import load_runtime_config
        from app.config import settings

        cfg = load_nl2sql_config()
        conn_cfg = cfg.get("connection", {})
        prompts = cfg.get("prompts", {})

        # 行数上限：用户在管理后台「参数配置」里设的 nl2sql_max_rows
        try:
            max_rows = int(load_runtime_config().get("nl2sql_max_rows", 50))
        except (TypeError, ValueError):
            max_rows = 50
        max_rows = max(50, min(max_rows, 1000))

        if not conn_cfg.get("host"):
            return "⚠️ 未配置数据库连接，请在管理后台→NL2SQL 中配置。"

        # 构造 system prompt
        system = f"""你是一个数据分析师。根据用户问题生成 SQL Server 兼容的 SQL。

数据库字段结构：
{prompts.get("schema", "未提供")}

专业术语映射：
{prompts.get("terms", "未提供")}

参考问答示例：
{prompts.get("qa_pairs", "未提供")}

要求：
- 只输出 SQL，不要任何额外文字
- 使用中文别名（AS）
- 字段名和表名用中括号 [] 包裹
- **必须用 TOP {max_rows} 限制结果行数**（除非用户明确指定了更小的行数，如"前10名"）
  · 例：`SELECT TOP {max_rows} [字段] AS [别名] FROM [表] ORDER BY ...`
  · 用户说"前 N 名"时用 `TOP N`（N 必须 ≤ {max_rows}）
  · 永远不要省略 TOP 子句
- 如果问题无法用 SQL 回答，输出 "-- 无法生成 SQL" 开头"""

        from app.services.llm_service import LLMService
        llm = LLMService()
        sql = llm.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": natural_language_query},
        ], temperature=0.3)
        sql = sql.strip()
        if sql.startswith("```"):
            sql = sql.split("\n", 1)[-1]
        if sql.endswith("```"):
            sql = sql.rsplit("```", 1)[0]
        sql = sql.strip()

        if sql.startswith("-- 无法生成"):
            return f"无法为当前问题生成 SQL。\n\nLLM 返回: {sql}"

        # 兜底：若 LLM 漏写 TOP，在第一个 SELECT 后强制注入
        sql = _ensure_top_limit(sql, max_rows)

        # 执行 SQL
        try:
            import pyodbc, os as _os
            drv = "/opt/homebrew/Cellar/freetds/1.5.18/lib/libtdsodbc.so"
            if not _os.path.exists(drv):
                drv2 = "/usr/local/lib/libtdsodbc.so"
                drv = drv2 if _os.path.exists(drv2) else drv
            conn_str = (
                f"DRIVER={{{drv}}};"
                f"SERVER={conn_cfg.get('host')};PORT={conn_cfg.get('port', 1433)};"
                f"UID={conn_cfg.get('username')};PWD={conn_cfg.get('password')};"
                f"DATABASE={conn_cfg.get('database')};CHARSET=UTF8;"
            )
            conn = pyodbc.connect(conn_str, timeout=30, autocommit=True)
            cursor = conn.cursor()
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchmany(max_rows)
            truncated = len(rows) >= max_rows  # 命中上限，可能还有更多
            cursor.close()
            conn.close()

            result_data = [dict(zip(columns, row)) for row in rows]

            # 检测列类型（用于前端表格优化）
            def _detect_col_type(col_name, values):
                numeric_count = 0
                for v in values:
                    if v is not None:
                        try:
                            float(v)
                            numeric_count += 1
                        except (ValueError, TypeError):
                            pass
                return "numeric" if numeric_count > len(values) * 0.8 else "text"

            col_types = {
                c: _detect_col_type(c, [row.get(c) for row in result_data])
                for c in columns
            }

            # 收集 sources（含 resultData + _meta 供前端表格渲染）
            global _current_sources
            col_meta = [{"name": c, "type": col_types[c]} for c in columns]
            _current_sources.append({
                "type": "nl2sql",
                "sql": sql,
                "prompt": system,
                "result_rows": len(result_data),
                "resultData": json.dumps({
                    "data": result_data,
                    "_meta": {
                        "total_rows": len(result_data),
                        "columns": col_meta,
                    },
                }, ensure_ascii=False, default=str),
            })

            # 缓存到 thread，供 make_chart 使用
            _cache_thread_data(_current_thread_id, result_data, col_meta)

            if not result_data:
                return f"SQL 执行成功，未返回任何数据。\n\nSQL: {sql}"

            # 返回格式化的结果文本
            lines = [f"SQL: {sql}", ""]
            lines.append("| " + " | ".join(str(c) for c in columns) + " |")
            lines.append("| " + " | ".join("---" for _ in columns) + " |")
            for row in result_data[:20]:
                vals = [str(row.get(c, ""))[:30] for c in columns]
                lines.append("| " + " | ".join(vals) + " |")
            if len(result_data) > 20:
                lines.append(f"*共 {len(result_data)} 行，仅显示前 20 行*")
            else:
                lines.append(f"*共 {len(result_data)} 行*")
            if truncated:
                lines.append(f"*⚠️ 结果已被截断为 {max_rows} 行（管理后台「参数配置」的上限），实际数据可能更多。*")
            return "\n".join(lines)

        except Exception as e:
            return f"❌ SQL 执行失败: {e}"

    @tool
    def make_chart(
        chart_type: str,
        x_field: str,
        y_fields: str,
        title: str = "",
    ) -> str:
        """根据上一次 query_database 的结果生成图表配置（不重新查询数据库）。

        适用场景：
        - 用户说"画个柱图/饼图/折线图"
        - 用户说"把刚才的数据可视化"
        - 用户说"换成饼图"等切换图表类型

        Args:
            chart_type: 图表类型，可选 'bar' | 'pie' | 'line' | 'area' | 'scatter' | 'stacked_bar'
            x_field: X 轴字段名（分类列）。必须是上一次查询结果中的列名。
            y_fields: Y 轴字段名（数值列），多个用英文逗号分隔。必须是上一次查询结果中的列名。
            title: 图表标题（可选，建议填）。

        Returns:
            简短文本说明已生成图表。前端会自动渲染。
        """
        logger.info("make_chart called: type=%s x=%s y=%s", chart_type, x_field, y_fields)

        cached = _get_thread_data(_current_thread_id)
        if not cached or not cached.get("data"):
            return "⚠️ 没有可用的查询结果。请先调用 query_database 查询数据，再生成图表。"

        data = cached["data"]
        cols = cached["columns"]
        col_names = {c["name"] for c in cols}

        # 校验图表类型
        allowed_types = {"bar", "pie", "line", "area", "scatter", "stacked_bar"}
        if chart_type not in allowed_types:
            return f"⚠️ 不支持的图表类型 '{chart_type}'。可选：{', '.join(sorted(allowed_types))}"

        # 校验字段
        if x_field not in col_names:
            return f"⚠️ X 轴字段 '{x_field}' 不在结果列中。可用列：{', '.join(c['name'] for c in cols)}"

        y_list = [y.strip() for y in y_fields.split(",") if y.strip()]
        if not y_list:
            return "⚠️ Y 轴字段不能为空。"
        missing = [y for y in y_list if y not in col_names]
        if missing:
            return f"⚠️ Y 轴字段不存在：{', '.join(missing)}。可用列：{', '.join(c['name'] for c in cols)}"

        # 饼图只支持单 Y
        if chart_type == "pie" and len(y_list) > 1:
            y_list = y_list[:1]

        spec = {
            "type": chart_type,
            "title": title or f"{', '.join(y_list)} 按 {x_field}",
            "x": x_field,
            "y": y_list,
            # 用 json round-trip 把 Decimal/datetime 转为 JSON 友好类型，
            # 避免后续 chat.py 中整个 sources 一起 dumps 时炸
            "data": json.loads(json.dumps(data, ensure_ascii=False, default=str)),
        }

        global _current_sources
        _current_sources.append({
            "type": "chart",
            "spec": spec,
        })

        return f"已生成图表「{spec['title']}」（{chart_type}），共 {len(data)} 条数据。前端会自动渲染。"

    return [query_database, make_chart]


def build_rag_tools(rag_retriever):
    """构建 RAG deepagent tools（只含 search_knowledge_base）。"""
    logger.info("build_rag_tools: rag=%s", rag_retriever)

    @tool
    def search_knowledge_base(query: str) -> str:
        """从向量知识库中检索相关文档片段。"""
        logger.info("search_knowledge_base called: query=%s", query[:60])
        try:
            contexts, _, detail = rag_retriever.retrieve_detail(query)
        except Exception as e:
            logger.error("RAG search failed: %s", e, exc_info=True)
            return f"检索失败: {e}"
        if not contexts:
            return "知识库中未找到相关内容。"
        global _current_sources, _current_retrieval_detail
        _current_retrieval_detail = detail
        _current_sources = _current_sources + [
            {"chunk_id": ctx["id"], "document_title": ctx.get("metadata", {}).get("document_title", ""),
             "content": ctx["content"][:200], "score": round(ctx.get("rerank_score", ctx.get("score", 0)), 4),
             "type": "rag"}
            for ctx in contexts[:5] if ctx.get("rerank_score", ctx.get("score", 0)) > 0
        ]
        return "\n\n".join(f"[来源{i+1}] {ctx['content']}" for i, ctx in enumerate(contexts[:5]))
    return [search_knowledge_base]


def build_kg_tools(graph_retriever):
    """构建 KG deepagent tools（只含 search_knowledge_graph）。"""
    logger.info("build_kg_tools: kg=%s", graph_retriever)

    @tool
    def search_knowledge_graph(query: str) -> str:
        """从知识图谱中检索实体及其关系。"""
        logger.info("search_knowledge_graph called: query=%s", query[:60])
        try:
            _, kg_text, cypher_text = graph_retriever.retrieve(query)
        except Exception as e:
            logger.error("KG search failed: %s", e, exc_info=True)
            return f"图谱检索失败: {e}"
        if not kg_text:
            return "知识图谱中未找到相关实体或关系。"
        minigraph = _build_minigraph(kg_text)
        global _current_sources, _current_kg_minigraph
        _current_kg_minigraph = minigraph
        _current_sources = _current_sources + [{
            "chunk_id": "",
            "document_title": "知识图谱",
            "content": kg_text,
            "score": 1.0,
            "type": "kg", "graph": minigraph, "cypher": cypher_text,
        }]
        return f"知识图谱关系：\n{kg_text}"
    return [search_knowledge_graph]


def build_tools(rag_retriever, graph_retriever, query_rewriter=None):
    """（保留兼容）构建 deepagents tools，注入运行时依赖。"""
    logger.info("build_tools: rag=%s kg=%s", rag_retriever, graph_retriever)
    return build_rag_tools(rag_retriever) + build_kg_tools(graph_retriever)


def _build_minigraph(kg_text: str) -> dict:
    """从 kg_text 解析迷你图谱数据。"""
    graph_nodes: dict[str, dict] = {}
    graph_edges: list[dict] = []

    rel_pattern = re.compile(
        r'^\[实体\]\s+(.+?)\s+--\((.+)\)-->\s+\[实体\]\s+(.+?)(?:\s+\((.+)\))?$'
    )
    for line in kg_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = rel_pattern.match(line)
        if m:
            source, rel_type, target, target_type = m.group(1), m.group(2), m.group(3), m.group(4) or "concept"
            # 清洗目标名：去掉尾部的 ()
            target = re.sub(r'\s*\(\)\s*$', '', target).strip()
            graph_nodes.setdefault(source, {"name": source, "type": "concept"})
            graph_nodes.setdefault(target, {"name": target, "type": target_type})
            dup = any(
                e["source"] == target and e["target"] == source and e["type"] == rel_type
                for e in graph_edges
            )
            if not dup:
                graph_edges.append({"source": source, "target": target, "type": rel_type})

    # 分配 ID
    node_id_map = {}
    nodes_list = []
    for i, name in enumerate(graph_nodes):
        node_id = f"g_{i}"
        node_id_map[name] = node_id
        nodes_list.append({"id": node_id, **graph_nodes[name]})

    edges_list = []
    for e in graph_edges:
        src_id = node_id_map.get(e["source"])
        tgt_id = node_id_map.get(e["target"])
        if src_id and tgt_id:
            edges_list.append({"source": src_id, "target": tgt_id, "type": e["type"]})

    return {"nodes": nodes_list, "edges": edges_list}


_TOP_RE = re.compile(r'\bSELECT\b(\s+(?:DISTINCT|ALL))?(\s+TOP\s+\d+(?:\s+PERCENT)?(?:\s+WITH\s+TIES)?)?',
                      re.IGNORECASE)


def _ensure_top_limit(sql: str, max_rows: int) -> str:
    """在外层 SELECT 后注入或夹紧 TOP N。

    - 若 LLM 已有 `TOP N` 且 N ≤ max_rows，保留
    - 若 N > max_rows，替换为 `TOP {max_rows}`
    - 若没有 TOP，在第一个 SELECT 后插入 `TOP {max_rows}`
    - 嵌套子查询里的 TOP 不动（只匹配第一个 SELECT）
    """
    m = _TOP_RE.match(sql.lstrip())
    if not m:
        return sql

    # 偏移：因为我们 match 的是 lstrip 之后的字符串，要把 leading whitespace 还原
    leading_ws = len(sql) - len(sql.lstrip())
    end = m.end() + leading_ws

    existing_top = m.group(2)  # ' TOP 100' 或 None
    if existing_top:
        # 抽取数字
        num_match = re.search(r'\d+', existing_top)
        if num_match:
            n = int(num_match.group())
            if n <= max_rows:
                return sql  # 已经在限制内
            # 替换数字
            new_top = existing_top.replace(num_match.group(), str(max_rows), 1)
            top_start = m.start(2) + leading_ws
            top_end = m.end(2) + leading_ws
            return sql[:top_start] + new_top + sql[top_end:]
        return sql

    # 没有 TOP，注入
    distinct = m.group(1) or ""
    insert_pos = m.start(1) + leading_ws if m.group(1) else (m.end(0) + leading_ws - (len(distinct)))
    # 简化：直接在 SELECT(+DISTINCT) 之后插入 ' TOP N '
    return sql[:end] + f" TOP {max_rows}" + sql[end:]