# backend/app/models/kg_type.py
"""SQLite 模型：节点类型和关系类型注册表。

类型定义为全局、不绑定知识库的命名实体。
所有节点/关系的 type 字段都应校验为已注册类型。
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text, func

from app.database import Base


class NodeType(Base):
    """节点类型注册表。"""

    __tablename__ = "node_types"

    name = Column(String(100), primary_key=True)  # e.g. "person"
    label = Column(String(200), nullable=False)    # 显示名 e.g. "人物"
    color = Column(String(20), default="#607d8b")  # 十六进制颜色
    description = Column(Text, default="")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<NodeType {self.name}>"


class RelationshipType(Base):
    """关系类型注册表。"""

    __tablename__ = "relationship_types"

    name = Column(String(100), primary_key=True)  # e.g. "works_at"
    label = Column(String(200), nullable=False)    # 显示名 e.g. "工作于"
    color = Column(String(20), default="#5e35b1")  # 边颜色
    description = Column(Text, default="")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<RelationshipType {self.name}>"