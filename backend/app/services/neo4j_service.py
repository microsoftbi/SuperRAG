# backend/app/services/neo4j_service.py
"""Neo4j graph database service for knowledge graph operations.

全局知识图谱，无论节点标签是 :Entity 还是 :Person/:Organization 等，
都通过 .name 属性匹配，不区分标签。
"""

import json
import logging
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class Neo4jService:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    # ═══════════════════════════════════════════════
    # 初始化
    # ═══════════════════════════════════════════════

    def initialize(self):
        """启动时创建索引（仅对 :Entity 标签，不影响其他标签）。"""
        with self.driver.session() as session:
            session.run("CREATE INDEX entity_name IF NOT EXISTS FOR (n:Entity) ON (n.name)")
            logger.info("Neo4j indexes created/verified")

    # ═══════════════════════════════════════════════
    # 写入
    # ═══════════════════════════════════════════════

    def import_extraction(self, chunk_ids: list[int],
                          entities: list[dict], relationships: list[dict]):
        """将实体提取结果写入 Neo4j（按名称匹配，不限制标签）。"""
        with self.driver.session() as session:
            for ent in entities:
                # 检查是否存在同名节点（任何标签）
                existing = session.run(
                    "MATCH (e {name: $name}) "
                    "RETURN e.chunk_ids AS ids",
                    name=ent["name"],
                ).single()
                existing_ids = existing["ids"] if existing and existing["ids"] else []
                merged_ids = list(set(existing_ids + chunk_ids))

                # 合并数据：添加/更新 Entity 标签节点
                session.run(
                    """
                    MERGE (e:Entity {name: $name})
                    ON CREATE SET
                        e.type = $type,
                        e.properties = $props,
                        e.chunk_ids = $chunk_ids,
                        e.internal_id = randomUUID()
                    ON MATCH SET
                        e.chunk_ids = $chunk_ids,
                        e.type = CASE WHEN $type <> e.type THEN $type ELSE e.type END,
                        e.properties = $props
                    """,
                    name=ent["name"], type=ent["type"],
                    chunk_ids=merged_ids,
                    props=json.dumps(ent.get("properties", {}), ensure_ascii=False),
                )

            for rel in relationships:
                rel_type = rel["type"].replace(" ", "_").replace("-", "_")
                query = (
                    "MATCH (a {name: $src}) "
                    "MATCH (b {name: $dst}) "
                    f"MERGE (a)-[:`{rel_type}`]->(b)"
                )
                session.run(query, src=rel["source"], dst=rel["target"])

    def delete_all_graph(self):
        """清空全部 Entity 标签的图谱数据（不影响 Person 等其他标签）。"""
        with self.driver.session() as session:
            session.run("MATCH (e:Entity) DETACH DELETE e")

    # ═══════════════════════════════════════════════
    # 读取（供 graph_retriever 调用）
    # ═══════════════════════════════════════════════

    def search_entities(self, search_text: str, limit: int = 20) -> list[dict]:
        """模糊搜索实体（按名称匹配，不限标签）。"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e)
                WHERE e.name CONTAINS $search_text
                RETURN e.name AS name, labels(e) AS labels,
                       e.chunk_ids AS chunk_ids, e.internal_id AS id
                LIMIT $limit
                """,
                search_text=search_text, limit=limit,
            )
            return [record.data() for record in result]

    def find_seed_entities(self, search_text: str) -> list[dict]:
        """在查询字符串中匹配已知实体名（不限标签）。"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e)
                WHERE $search_text CONTAINS e.name
                RETURN DISTINCT e.name AS name, labels(e) AS labels,
                       e.chunk_ids AS chunk_ids
                LIMIT 20
                """,
                search_text=search_text,
            )
            return [record.data() for record in result]

    def bfs_traverse_1hop(self, seed_names: list[str]) -> list[dict]:
        """1 跳遍历：种子实体 + 直接邻居 + 关系（不限标签）。"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e)
                WHERE e.name IN $names
                OPTIONAL MATCH (e)-[r]-(neighbor)
                RETURN e.name AS source, labels(e) AS source_labels,
                       e.chunk_ids AS source_chunk_ids,
                       type(r) AS rel_type,
                       neighbor.name AS target, labels(neighbor) AS target_labels,
                       neighbor.chunk_ids AS target_chunk_ids
                """,
                names=seed_names,
            )
            return [record.data() for record in result]

    def bfs_traverse(self, seed_names: list[str], depth: int = 2) -> list[dict]:
        """多跳遍历（不限标签）。"""
        with self.driver.session() as session:
            result = session.run(
                f"""
                MATCH (e)
                WHERE e.name IN $names
                OPTIONAL MATCH (e)-[*1..{depth}]-(connected)
                RETURN DISTINCT connected.name AS name,
                       labels(connected) AS labels,
                       connected.chunk_ids AS chunk_ids
                """,
                names=seed_names,
            )
            return [record.data() for record in result]

    def find_paths_between(self, names_a: list[str], names_b: list[str],
                            max_depth: int = 5, limit: int = 10) -> list[dict]:
        """查找两组实体之间的最短路径（用于回答"A和B有什么关联"类问题）。"""
        with self.driver.session() as session:
            result = session.run(
                f"""
                MATCH path = shortestPath((a)-[*1..{max_depth}]-(b))
                WHERE a.name IN $names_a AND b.name IN $names_b
                  AND a.name <> b.name
                RETURN [n IN nodes(path) | n.name] AS node_names,
                       [r IN relationships(path) | type(r)] AS rel_types
                LIMIT $limit
                """,
                names_a=names_a, names_b=names_b, limit=limit,
            )
            return [record.data() for record in result]

    def get_full_graph(self) -> dict:
        """获取全局图谱（前端可视化用），返回 {nodes, edges}。

        兼容 :Entity（有 internal_id）和 :Person 等其他标签的节点。
        """
        with self.driver.session() as session:
            # 读取所有节点
            result = session.run(
                """
                MATCH (e)
                WHERE e.name IS NOT NULL
                RETURN e.name AS name, labels(e) AS labels,
                       e.internal_id AS internal_id, e.type AS e_type,
                       e.chunk_ids AS chunk_ids
                """
            )
            all_records = list(result)

            # 构建节点列表：有 internal_id 的用 id，没有的生成
            node_map = {}  # name → node dict
            id_counter = [0]
            nodes = []
            for rec in all_records:
                name = rec["name"]
                # 推断类型
                lbls = rec["labels"] or []
                if rec["e_type"]:
                    ntype = rec["e_type"]
                elif "Person" in lbls:
                    ntype = "person"
                elif "Organization" in lbls:
                    ntype = "org"
                elif "Location" in lbls:
                    ntype = "location"
                elif "CaseNode" in lbls or "Case" in lbls:
                    ntype = "concept"
                elif "Event" in lbls:
                    ntype = "concept"
                elif "Item" in lbls:
                    ntype = "product"
                else:
                    ntype = "concept"

                node_id = rec["internal_id"] or f"auto_{id_counter[0]}"
                id_counter[0] += 1

                chunk_ids = rec["chunk_ids"] or []
                chunk_count = len(chunk_ids)

                node_data = {
                    "id": node_id,
                    "name": name,
                    "type": ntype,
                    "chunk_count": chunk_count,
                }
                node_map[name] = node_data
                nodes.append(node_data)

            # 读取所有关系
            edges_result = session.run(
                """
                MATCH (a)-[r]-(b)
                WHERE a.name IS NOT NULL AND b.name IS NOT NULL
                RETURN DISTINCT a.name AS src_name, b.name AS dst_name,
                       type(r) AS rel_type
                """
            )
            edges = []
            seen_edges = set()
            for record in edges_result:
                src_data = node_map.get(record["src_name"])
                dst_data = node_map.get(record["dst_name"])
                if src_data and dst_data:
                    key = (src_data["id"], dst_data["id"], record["rel_type"])
                    if key not in seen_edges:
                        seen_edges.add(key)
                        edges.append({
                            "source": src_data["id"],
                            "target": dst_data["id"],
                            "type": record["rel_type"],
                        })

            return {"nodes": nodes, "edges": edges}

    def delete_relationship(self, source_name: str, target_name: str, rel_type: str):
        """删除两个实体之间的指定关系。"""
        rel_type_clean = rel_type.replace(" ", "_").replace("-", "_")
        query = (
            "MATCH (a {name: $src})"
            f"-[r:`{rel_type_clean}`]->"
            "(b {name: $dst}) "
            "DELETE r"
        )
        with self.driver.session() as session:
            session.run(query, src=source_name, dst=target_name)