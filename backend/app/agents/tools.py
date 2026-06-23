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


def reset_tool_state():
    """每次 chat 请求开始时调用，重置收集状态。"""
    global _current_sources, _current_kg_minigraph
    _current_sources = []
    _current_kg_minigraph = None


def get_collected_sources() -> list[dict]:
    return _current_sources


def get_collected_kg_minigraph() -> dict | None:
    return _current_kg_minigraph


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
        from app.config import settings

        cfg = load_nl2sql_config()
        conn_cfg = cfg.get("connection", {})
        prompts = cfg.get("prompts", {})

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
            rows = cursor.fetchmany(50)
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
            _current_sources.append({
                "type": "nl2sql",
                "sql": sql,
                "prompt": system,
                "result_rows": len(result_data),
                "resultData": json.dumps({
                    "data": result_data,
                    "_meta": {
                        "total_rows": len(result_data),
                        "columns": [
                            {"name": c, "type": col_types[c]}
                            for c in columns
                        ],
                    },
                }, ensure_ascii=False, default=str),
            })

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
            return "\n".join(lines)

        except Exception as e:
            return f"❌ SQL 执行失败: {e}"

    return [query_database]


def build_tools(rag_retriever, graph_retriever, query_rewriter=None):
    logger.info("build_tools: rag=%s kg=%s", rag_retriever, graph_retriever)
    """构建 deepagents tools，注入运行时依赖。"""

    @tool
    def search_knowledge_base(query: str) -> str:
        """从向量知识库中检索相关文档片段。

        适用场景：
        - 查询事实、定义、流程、政策、产品规格等
        - 用户问"是什么"、"怎么做"、"多少钱"、"什么时候"等问题

        Args:
            query: 检索关键词或自然语言查询，应包含足够上下文（已替换代词）。

        Returns:
            带 [来源N] 编号的文档片段文本，可在最终回答中引用。
        """
        logger.info("search_knowledge_base called: query=%s", query[:60])
        try:
            contexts, _ = rag_retriever.retrieve(query)
            logger.info("search_knowledge_base: %d contexts", len(contexts))
        except Exception as e:
            logger.error("RAG search failed: %s", e, exc_info=True)
            return f"检索失败: {e}"

        if not contexts:
            return "知识库中未找到相关内容。"

        # 收集 sources
        global _current_sources
        _current_sources = _current_sources + [
            {
                "chunk_id": ctx["id"],
                "document_title": ctx.get("metadata", {}).get("document_title", ""),
                "content": ctx["content"][:200],
                "score": round(ctx.get("rerank_score", ctx.get("score", 0)), 4),
                "type": "rag",
            }
            for ctx in contexts[:5]
        ]

        # 拼成 [来源N] 格式给 LLM
        return "\n\n".join(
            f"[来源{i+1}] {ctx['content']}"
            for i, ctx in enumerate(contexts[:5])
        )

    @tool
    def search_knowledge_graph(query: str) -> str:
        """从知识图谱中检索实体及其关系。

        适用场景：
        - 查询人物、组织、产品、项目之间的关系
        - 多跳推理（如"A的负责人参与过哪些项目"）
        - 实体归属（"X属于哪个部门"）

        Args:
            query: 应包含实体名（人名/组织名/产品名等）。

        Returns:
            实体关系描述文本，每行一条 "[实体] A --(关系)--> B" 格式。
        """
        logger.info("search_knowledge_graph called: query=%s", query[:60])
        try:
            contexts, kg_text, cypher_text = graph_retriever.retrieve(query)
            logger.info("search_knowledge_graph: %d contexts, %d kg_text chars", len(contexts), len(kg_text or ""))
        except Exception as e:
            logger.error("KG search failed: %s", e, exc_info=True)
            return f"图谱检索失败: {e}"

        if not contexts and not kg_text:
            return "知识图谱中未找到相关实体或关系。"

        # 解析 kg_text 构建 minigraph
        minigraph = _build_minigraph(kg_text, contexts)
        global _current_sources, _current_kg_minigraph
        _current_kg_minigraph = minigraph

        _current_sources = _current_sources + [
            {
                "chunk_id": str(contexts[0].get("chunk_id", "")) if contexts else "",
                "document_title": "知识图谱",
                "content": "\n".join(contexts[0].get("kg_paths", [])) if contexts else kg_text,
                "score": min(contexts[0].get("kg_score", 1.0) / 2.0, 1.0) if contexts else 1.0,
                "type": "kg",
                "graph": minigraph,
                "cypher": cypher_text,
            }
        ]

        return f"知识图谱关系：\n{kg_text}\n\n相关文档片段：\n" + "\n\n".join(
            f"[来源{i+1}] {ctx['content'][:300]}" for i, ctx in enumerate(contexts[:3])
        )

    return [search_knowledge_base, search_knowledge_graph]


def _build_minigraph(kg_text: str, contexts: list[dict]) -> dict:
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

    # 从 [匹配] 路径补充节点
    for ctx in contexts[:5]:
        for path in ctx.get("kg_paths", []):
            if path.startswith("[匹配] "):
                name = path[5:].strip()
                graph_nodes.setdefault(name, {"name": name, "type": "concept"})

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