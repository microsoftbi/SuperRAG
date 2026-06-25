# backend/app/kg/graph_retriever.py
"""Knowledge graph retriever: entity matching → graph traversal → relation text.

全局知识图谱，不绑定知识库，所有用户共享。
只返回关系文本（不再从 SQLite 取 chunk 原文）。
"""

import logging

logger = logging.getLogger(__name__)


class GraphRetriever:
    """KG 检索器。

    流程：
    1. 从用户查询中匹配种子实体（CONTAINS 模糊匹配）
    2. 图遍历（1跳 + 多跳）
    3. 返回关系文本
    """

    def __init__(self, neo4j_service):
        self.neo4j = neo4j_service

    def retrieve(self, query: str, max_depth: int | None = None) -> tuple[list[dict], str]:
        """执行全局 KG 检索。

        Args:
            query: 用户问题
            max_depth: 图遍历深度（默认从运行时配置读取）

        Returns:
            (contexts, formatted_kg_text, cypher_text)
        """
        if max_depth is None:
            try:
                from app.services.runtime_config import load_runtime_config
                max_depth = load_runtime_config().get("kg_max_depth", 5)
            except Exception:
                max_depth = 5
        max_depth = max(2, min(max_depth, 6))  # 限制范围 2-6
        # Step 1: 匹配种子实体
        seed_entities = self.neo4j.find_seed_entities(query)
        if not seed_entities:
            logger.info("GraphRetriever: no seed entities matched for query")
            return [], "", ""

        seed_names = list(set(e["name"] for e in seed_entities))
        logger.info("GraphRetriever: matched seed entities: %s", seed_names)

        # Step 2: 图遍历
        rel_paths = self.neo4j.bfs_traverse_1hop(seed_names)
        connected = self.neo4j.bfs_traverse(seed_names, depth=max_depth) if max_depth >= 1 else []

        # Step 3: 构建格式化关系文本
        path_lines = set()
        for path in rel_paths:
            src = path.get("source")
            dst = path.get("target")
            rt = path.get("rel_type")
            if src and dst and rt:
                path_lines.add(
                    f"[实体] {src} --({rt})--> [实体] {dst} ({path.get('target_type', '')})"
                )
        formatted_kg_text = "\n".join(sorted(path_lines))

        # Step 5.5: 多种子实体间路径查找
        path_section = ""
        if len(seed_names) >= 2:
            try:
                paths = self.neo4j.find_paths_between(seed_names, seed_names,
                                                        max_depth=max_depth, limit=10)
                if paths:
                    path_lines_extra = ["\n\n=== 实体间连接路径 ==="]
                    for p in paths:
                        nodes = p.get("node_names", [])
                        rels = p.get("rel_types", [])
                        if nodes and rels:
                            segments = [nodes[0]]
                            for i, rel in enumerate(rels):
                                segments.append(f"--({rel})-->")
                                segments.append(nodes[i + 1])
                            path_lines_extra.append("  " + " ".join(segments))
                    path_section = "\n".join(path_lines_extra)
            except Exception as e:
                logger.debug("Path finding skipped: %s", e)
        formatted_kg_text += path_section

        # 构建可复制的 Cypher 查询文本
        cypher_parts = []
        cypher_parts.append(f"-- Step 1: 种子匹配（CONTAINS）\n"
                            f"MATCH (e)\n"
                            f"WHERE '{query}' CONTAINS e.name\n"
                            f"RETURN DISTINCT e.name AS name, labels(e) AS labels, "
                            f"e.chunk_ids AS chunk_ids\n"
                            f"LIMIT 20")

        names_list_str = ", ".join(f"'{n}'" for n in seed_names)
        cypher_parts.append(f"\n\n-- Step 2: 1跳图遍历\n"
                            f"MATCH (e)\n"
                            f"WHERE e.name IN [{names_list_str}]\n"
                            f"OPTIONAL MATCH (e)-[r]-(neighbor)\n"
                            f"RETURN e.name AS source, labels(e) AS source_labels,\n"
                            f"       e.chunk_ids AS source_chunk_ids,\n"
                            f"       type(r) AS rel_type,\n"
                            f"       neighbor.name AS target, "
                            f"labels(neighbor) AS target_labels,\n"
                            f"       neighbor.chunk_ids AS target_chunk_ids")

        cypher_parts.append(f"\n\n-- Step 3: 多跳扩展（最多 {max_depth} 跳）\n"
                            f"MATCH (e)\n"
                            f"WHERE e.name IN [{names_list_str}]\n"
                            f"OPTIONAL MATCH (e)-[*1..{max_depth}]-(connected)\n"
                            f"RETURN DISTINCT connected.name AS name,\n"
                            f"       labels(connected) AS labels,\n"
                            f"       connected.chunk_ids AS chunk_ids")

        if len(seed_names) >= 2:
            names_a_str = ", ".join(f"'{n}'" for n in seed_names)
            cypher_parts.append(f"\n\n-- Step 4: 实体间最短路径\n"
                                f"MATCH path = shortestPath((a)-[*1..{max_depth}]-(b))\n"
                                f"WHERE a.name IN [{names_a_str}]\n"
                                f"  AND b.name IN [{names_a_str}]\n"
                                f"  AND a.name <> b.name\n"
                                f"RETURN [n IN nodes(path) | n.name] AS node_names,\n"
                                f"       [r IN relationships(path) | type(r)] AS rel_types\n"
                                f"LIMIT 10")

        cypher_text = "".join(cypher_parts)

        logger.info("GraphRetriever: found %d relation paths (depth=%d)",
                     len(path_lines), max_depth)
        return [], formatted_kg_text, cypher_text