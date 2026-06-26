# backend/app/services/neo4j_service.py
"""Neo4j graph database service for knowledge graph operations.

全局知识图谱，无论节点标签是 :Entity 还是 :Person/:Organization 等，
都通过 .name 属性匹配，不区分标签。
"""

import json
import logging
import re
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


def cql_escape(val: str) -> str:
    """将字符串转义为 Cypher 字符串字面量（单引号包围）。"""
    escaped = val.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


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
        无 internal_id 的节点会自动补一个 UUID，以便后续编辑/删除。
        """
        # 旧数据兼容：先补 internal_id
        self.ensure_internal_ids()

        with self.driver.session() as session:
            # 读取所有节点
            result = session.run(
                """
                MATCH (e)
                WHERE e.name IS NOT NULL
                RETURN e.name AS name, labels(e) AS labels,
                       e.internal_id AS internal_id, e.type AS e_type,
                       e.chunk_ids AS chunk_ids,
                       e.properties AS properties
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
                    "properties": rec["properties"] or "{}",
                    "labels": rec["labels"] or [],
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
                    # 无向查询会返回 (a→b) 和 (b→a) 两条，排序 id 去重
                    ids = sorted([src_data["id"], dst_data["id"]])
                    key = (ids[0], ids[1], record["rel_type"])
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

    # ═══════════════════════════════════════════════
    # 节点维护（管理后台）
    # ═══════════════════════════════════════════════

    def find_entity_by_id(self, internal_id: str) -> dict | None:
        """按 internal_id 查节点。"""
        with self.driver.session() as session:
            rec = session.run(
                """
                MATCH (e)
                WHERE e.internal_id = $id
                RETURN e.name AS name, e.type AS type,
                       e.properties AS properties,
                       e.chunk_ids AS chunk_ids,
                       labels(e) AS labels
                """,
                id=internal_id,
            ).single()
            if not rec:
                return None
            return {
                "id": internal_id,
                "name": rec["name"],
                "type": rec["type"],
                "properties": rec["properties"],
                "chunk_ids": rec["chunk_ids"] or [],
                "labels": rec["labels"] or [],
            }

    def count_entity_relationships(self, internal_id: str) -> int:
        """统计节点的关系数（用于删除前告警）。"""
        with self.driver.session() as session:
            rec = session.run(
                """
                MATCH (e)-[r]-()
                WHERE e.internal_id = $id
                RETURN count(r) AS cnt
                """,
                id=internal_id,
            ).single()
            return int(rec["cnt"]) if rec else 0

    def update_entity(self, internal_id: str, name: str, type: str,
                       properties: dict) -> dict | None:
        """按 internal_id 改节点的 name / type / properties，保留所有关系。

        若 new_name 已被另一个节点占用，返回 None（调用方决定怎么做）。
        """
        props_json = json.dumps(properties or {}, ensure_ascii=False)
        with self.driver.session() as session:
            # 1. 找到当前节点
            current = session.run(
                "MATCH (e) WHERE e.internal_id = $id RETURN e.name AS cur_name",
                id=internal_id,
            ).single()
            if not current:
                return None
            cur_name = current["cur_name"]

            # 2. 若改名了，先检查目标名是否被别人占用
            if name != cur_name:
                conflict = session.run(
                    """
                    MATCH (e) WHERE e.name = $name AND e.internal_id <> $id
                    RETURN e.internal_id AS other_id LIMIT 1
                    """,
                    name=name, id=internal_id,
                ).single()
                if conflict:
                    return {"conflict": True, "other_id": conflict["other_id"]}

            # 3. 更新
            session.run(
                """
                MATCH (e) WHERE e.internal_id = $id
                SET e.name = $name,
                    e.type = $type,
                    e.properties = $props
                """,
                id=internal_id, name=name, type=type, props=props_json,
            )
            return {"conflict": False, "id": internal_id, "name": name, "type": type}

    def delete_entity(self, internal_id: str) -> bool:
        """删除节点及其所有关系。"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e) WHERE e.internal_id = $id
                WITH e, count{(e)-[]-()} AS rel_count
                DETACH DELETE e
                RETURN rel_count
                """,
                id=internal_id,
            ).single()
            return result is not None

    def update_relationship(self, source_name: str, target_name: str,
                             old_type: str, new_type: str) -> bool:
        """改关系类型：删旧 + 建新。

        因 Neo4j 不支持直接改 type，必须重建。源/目标实体不变。
        """
        old_clean = old_type.replace(" ", "_").replace("-", "_")
        new_clean = new_type.replace(" ", "_").replace("-", "_")
        with self.driver.session() as session:
            # 先确认有源边
            rec = session.run(
                f"""
                MATCH (a {{name: $src}})-[r:`{old_clean}`]->(b {{name: $dst}})
                RETURN count(r) AS cnt
                """,
                src=source_name, dst=target_name,
            ).single()
            if not rec or rec["cnt"] == 0:
                return False
            # 删旧建新
            session.run(
                f"""
                MATCH (a {{name: $src}})-[r:`{old_clean}`]->(b {{name: $dst}})
                DELETE r
                """,
                src=source_name, dst=target_name,
            )
            session.run(
                f"""
                MATCH (a {{name: $src}}), (b {{name: $dst}})
                MERGE (a)-[:`{new_clean}`]->(b)
                """,
                src=source_name, dst=target_name,
            )
            return True

    def ensure_internal_ids(self) -> int:
        """为所有缺 internal_id 的节点补一个 UUID（旧数据兼容）。

        返回补写的节点数。
        """
        with self.driver.session() as session:
            rec = session.run(
                """
                MATCH (e) WHERE e.name IS NOT NULL AND e.internal_id IS NULL
                SET e.internal_id = randomUUID()
                RETURN count(e) AS cnt
                """
            ).single()
            return int(rec["cnt"]) if rec else 0

    def get_distinct_types(self) -> list[str]:
        """获取知识图谱中所有已使用的实体类型。"""
        with self.driver.session() as session:
            result = session.run(
                "MATCH (e:Entity) WHERE e.type IS NOT NULL "
                "RETURN DISTINCT e.type AS type ORDER BY type"
            )
            return [r["type"] for r in result]

    def count_entities_by_type(self, type_name: str) -> int:
        """统计给定节点类型在 Neo4j 中的使用数。"""
        with self.driver.session() as session:
            rec = session.run(
                "MATCH (e:Entity) WHERE e.type = $type RETURN count(e) AS cnt",
                type=type_name,
            ).single()
            return int(rec["cnt"]) if rec else 0

    def count_relationships_by_type(self, rel_type: str) -> int:
        """统计给定关系类型在 Neo4j 中的使用数。"""
        with self.driver.session() as session:
            rec = session.run(
                "MATCH ()-[r]->() WHERE type(r) = $type RETURN count(r) AS cnt",
                type=rel_type,
            ).single()
            return int(rec["cnt"]) if rec else 0

    def find_unregistered_types(self, db_session, is_node: bool = True) -> list[str]:
        """查找 Neo4j 中使用了但未在 SQLite 注册的类型。"""
        from app.models.kg_type import NodeType, RelationshipType

        if is_node:
            with self.driver.session() as session:
                result = session.run(
                    "MATCH (e:Entity) WHERE e.type IS NOT NULL "
                    "RETURN DISTINCT e.type AS type"
                )
                neo4j_types = {r["type"] for r in result}
            registered = {
                r[0] for r in db_session.query(NodeType.name).all()
            }
        else:
            with self.driver.session() as session:
                # Cypher 没有直接的"查询所有关系类型"语法，用函数
                result = session.run("CALL db.relationshipTypes()")
                neo4j_types = {r["relationshipType"] for r in result}
            registered = {
                r[0] for r in db_session.query(RelationshipType.name).all()
            }

        return sorted(neo4j_types - registered)

    def execute_cypher(self, cypher: str) -> dict:
        """执行任意 Cypher 查询，返回摘要信息。

        Returns:
            {"success": bool, "summary": str, "count": int, "error": str | None}
        """
        with self.driver.session() as session:
            try:
                result = session.run(cypher)
                summary = result.consume()
                counters = summary.counters
                total = (
                    (counters.nodes_created or 0)
                    + (counters.nodes_deleted or 0)
                    + (counters.relationships_created or 0)
                    + (counters.relationships_deleted or 0)
                    + (counters.properties_set or 0)
                    + (counters.labels_added or 0)
                    + (counters.labels_removed or 0)
                )
                return {
                    "success": True,
                    "summary": (
                        f"创建 {counters.nodes_created or 0} 节点, "
                        f"创建 {counters.relationships_created or 0} 关系, "
                        f"删除 {counters.nodes_deleted or 0} 节点, "
                        f"删除 {counters.relationships_deleted or 0} 关系, "
                        f"设置 {counters.properties_set or 0} 属性"
                    ),
                    "count": total,
                    "error": None,
                }
            except Exception as e:
                return {
                    "success": False,
                    "summary": "执行失败",
                    "count": 0,
                    "error": str(e),
                }

    def export_cypher(self) -> str:
        """将当前图谱所有节点和关系导出为 Cypher MERGE 语句（幂等，可重复执行）。"""
        with self.driver.session() as session:
            # 节点（兼容所有标签，不限于 :Entity）
            nodes_result = session.run(
                "MATCH (n) WHERE n.name IS NOT NULL "
                "RETURN n.name AS name, n.type AS type, labels(n) AS labels, "
                "       n.internal_id AS internal_id, n.properties AS props "
                "ORDER BY n.name"
            )
            lines = []
            node_count = 0
            for rec in nodes_result:
                name = rec["name"]
                # 类型推断（与 get_full_graph 一致）
                ntype = rec["type"]
                if not ntype:
                    lbls = rec["labels"] or []
                    if "Person" in lbls:
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
                internal_id = rec["internal_id"] or str(hash(name))

                var = f"n{node_count}"
                set_items = [
                    f"{var}.type = {cql_escape(ntype)}",
                    f"{var}.internal_id = {cql_escape(internal_id)}",
                ]
                raw_props = rec["props"]
                if raw_props and raw_props not in ("{}", ""):
                    try:
                        pobj = json.loads(raw_props) if isinstance(raw_props, str) else raw_props
                        for k, v in pobj.items():
                            set_items.append(f"{var}.{k} = {cql_escape(str(v))}")
                    except (json.JSONDecodeError, TypeError):
                        pass

                on_create = ",\n        ".join(set_items)
                lines.append(
                    f"MERGE ({var}:Entity {{name: {cql_escape(name)}}})\n"
                    f"ON CREATE SET\n    {on_create};"
                )
                node_count += 1

            lines.append("")

            # 关系（去重，兼容所有标签）
            edges_result = session.run(
                "MATCH (a)-[r]-(b) "
                "WHERE a.name IS NOT NULL AND b.name IS NOT NULL AND a.name <> b.name "
                "RETURN a.name AS src, b.name AS dst, type(r) AS rel_type"
            )
            seen = set()
            edge_count = 0
            for rec in edges_result:
                src, dst = rec["src"], rec["dst"]
                key = tuple(sorted([src, dst])) + (rec["rel_type"],)
                if key in seen:
                    continue
                seen.add(key)
                lines.append(
                    f"MATCH (a:Entity {{name: {cql_escape(src)}}}), "
                    f"(b:Entity {{name: {cql_escape(dst)}}})\n"
                    f"MERGE (a)-[:{rec['rel_type']}]->(b);"
                )
                edge_count += 1

            header = (
                f"// SuperRAG 知识图谱导出\n"
                f"// 节点: {node_count}, 关系: {edge_count}\n\n"
            )
            return header + "\n".join(lines)