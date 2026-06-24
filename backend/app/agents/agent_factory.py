# backend/app/agents/agent_factory.py
"""Deep agent factory: builds the agent with SqliteSaver checkpointer + tools."""

import logging
import os

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.config import settings
from app.agents.tools import build_tools, build_nl2sql_tools

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个专业的客服助手。你可以使用以下工具帮助用户：

工具说明：
- search_knowledge_base：从向量知识库中检索文档片段（适合查找事实、流程、政策、产品规格等）
- search_knowledge_graph：从知识图谱中检索实体关系（适合查询人物/组织/产品之间的关系、归属、多跳推理）

工作流程：
1. 根据用户问题判断使用哪个工具：
   - 涉及关系、人物、组织、产品归属时优先使用 search_knowledge_graph
   - 涉及事实、定义、操作流程时优先使用 search_knowledge_base
   - 必要时可以两个工具都调用
2. 拿到检索结果后，基于检索到的内容回答
3. 如果检索结果不足以回答，明确告知用户

回答规则：
- 使用 [来源N] 标注引用的来源
- 用中文回答，语气专业友好
- 不编造信息，不依赖训练知识
- 简洁准确，直接回答用户问题"""

NL2SQL_SYSTEM_PROMPT = """你是一个数据分析助手。你可以使用两个工具：
- query_database：根据自然语言查询数据仓库，得到表格数据
- make_chart：根据"上一次 query_database 的结果"生成图表配置，不会再次查询数据库

工作流程：
1. 用户提出数据问题 → 调用 query_database 查询
2. 拿到结果后用中文回答用户的问题，对数据做有意义的解读
3. 当用户明确要求"画图/做图/柱图/饼图/折线图/可视化"等需求时 → 调用 make_chart
   - 切换图表类型（如"换成饼图"）也用 make_chart，无需重新 query_database
   - 根据数据特征选择合适的图表类型：
     · 1 文本列 + 1 数值列且行数<10 → pie
     · 1 文本列 + 1 数值列且行数≥10 → bar
     · 1 时间列 + 数值列 → line
     · 多个数值列对比 → stacked_bar
   - x_field 选分类/时间列，y_fields 选数值列（多个用英文逗号分隔）
   - title 用中文，简洁明确

回答规则：
- 直接回答用户问题，不要编造信息
- 查询无结果时如实告知
- 生成图表后简单告知用户"已生成 XX 图表"，并继续解读数据
- 用中文回答，语气专业"""


_agent = None
_checkpointer = None
_sqlite_conn = None

_nl2sql_agent = None
_nl2sql_checkpointer = None
_nl2sql_conn = None


def _get_db_path() -> str:
    db_path = settings.database_url.replace("sqlite:///", "")
    if db_path.startswith("./"):
        db_path = db_path[2:]
    return os.path.abspath(db_path)


async def init_agent(rag_retriever, graph_retriever, query_rewriter=None):
    """初始化 RAG/KG agent。"""
    import aiosqlite

    global _agent, _checkpointer, _sqlite_conn

    db_path = _get_db_path()
    logger.info("Agent checkpointer SQLite: %s", db_path)

    aio_conn = await aiosqlite.connect(db_path)
    _checkpointer = AsyncSqliteSaver(aio_conn)
    await _checkpointer.setup()

    model = ChatOpenAI(
        model=settings.llm_model_name,
        api_key=settings.volc_api_key,
        base_url=settings.volc_endpoint,
        temperature=0.7,
        streaming=True,
        extra_body={"reasoning_effort": None},
    )

    tools = build_tools(rag_retriever, graph_retriever, query_rewriter)

    from deepagents import create_deep_agent

    _agent = create_deep_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
        checkpointer=_checkpointer,
    )

    logger.info("✅ RAG agent initialized (model=%s, tools=%d)",
                settings.llm_model_name, len(tools))
    return _agent


async def init_nl2sql_agent():
    """初始化 NL2SQL agent，独立 checkpointer。"""
    import aiosqlite

    global _nl2sql_agent, _nl2sql_checkpointer, _nl2sql_conn

    db_path = _get_db_path()
    logger.info("NL2SQL agent checkpointer SQLite: %s", db_path)

    aio_conn = await aiosqlite.connect(db_path)
    _nl2sql_checkpointer = AsyncSqliteSaver(aio_conn)
    await _nl2sql_checkpointer.setup()

    model = ChatOpenAI(
        model=settings.llm_model_name,
        api_key=settings.volc_api_key,
        base_url=settings.volc_endpoint,
        temperature=0.3,
        streaming=True,
        extra_body={"reasoning_effort": None},
    )

    tools = build_nl2sql_tools()

    from deepagents import create_deep_agent

    _nl2sql_agent = create_deep_agent(
        model=model,
        system_prompt=NL2SQL_SYSTEM_PROMPT,
        tools=tools,
        checkpointer=_nl2sql_checkpointer,
    )

    logger.info("✅ NL2SQL agent initialized (tools=%d)", len(tools))
    return _nl2sql_agent


def get_agent():
    return _agent


def get_nl2sql_agent():
    return _nl2sql_agent


async def close_agent():
    global _sqlite_conn
    if _sqlite_conn:
        await _sqlite_conn.close()
        _sqlite_conn = None


async def close_nl2sql_agent():
    global _nl2sql_conn
    if _nl2sql_conn:
        await _nl2sql_conn.close()
        _nl2sql_conn = None