# backend/app/agents/agent_factory.py
"""Deep agent factory: builds the agent with SqliteSaver checkpointer + tools."""

import logging
import os

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.config import settings
from app.agents.tools import build_rag_tools, build_kg_tools, build_nl2sql_tools

logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = """你是一个专业的客服助手。你可以使用 search_knowledge_base 工具从知识库中检索信息。

工作流程：
1. 根据用户问题调用 search_knowledge_base 检索相关知识
2. 基于检索到的内容用中文回答用户
3. 如果检索结果不足以回答，明确告知用户

回答规则：
- 使用 [来源N] 标注引用的来源
- 用中文回答，语气专业友好
- 不编造信息，不依赖训练知识
- 简洁准确，直接回答用户问题"""

KG_SYSTEM_PROMPT = """你是一个知识图谱分析助手。你可以使用 search_knowledge_graph 工具从知识图谱中检索实体关系。

工作流程：
1. 根据用户问题调用 search_knowledge_graph 检索相关实体关系
2. 基于检索到的关系用中文回答用户
3. 如果图谱中没有找到相关信息，明确告知用户

回答规则：
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


_rag_agent = None
_rag_checkpointer = None
_rag_sqlite_conn = None

_kg_agent = None
_kg_checkpointer = None
_kg_sqlite_conn = None

_nl2sql_agent = None
_nl2sql_checkpointer = None
_nl2sql_conn = None


def _get_db_path() -> str:
    db_path = settings.database_url.replace("sqlite:///", "")
    if db_path.startswith("./"):
        db_path = db_path[2:]
    return os.path.abspath(db_path)


async def _create_agent(tools, system_prompt, temperature=0.7):
    """创建 deepagent 通用函数。"""
    import aiosqlite
    db_path = _get_db_path()
    aio_conn = await aiosqlite.connect(db_path)
    checkpointer = AsyncSqliteSaver(aio_conn)
    await checkpointer.setup()

    model = ChatOpenAI(
        model=settings.llm_model_name,
        api_key=settings.volc_api_key,
        base_url=settings.volc_endpoint,
        temperature=temperature,
        streaming=True,
        extra_body={"reasoning_effort": None},
    )

    from deepagents import create_deep_agent
    agent = create_deep_agent(
        model=model,
        system_prompt=system_prompt,
        tools=tools,
        checkpointer=checkpointer,
    )
    return agent, checkpointer, aio_conn


async def init_rag_agent(rag_retriever):
    """初始化 RAG agent（只含 search_knowledge_base）。"""
    global _rag_agent, _rag_checkpointer, _rag_sqlite_conn
    tools = build_rag_tools(rag_retriever)
    _rag_agent, _rag_checkpointer, _rag_sqlite_conn = await _create_agent(tools, RAG_SYSTEM_PROMPT)
    logger.info("✅ RAG agent initialized (tools=%d)", len(tools))
    return _rag_agent


async def init_kg_agent(graph_retriever):
    """初始化 KG agent（只含 search_knowledge_graph）。"""
    global _kg_agent, _kg_checkpointer, _kg_sqlite_conn
    tools = build_kg_tools(graph_retriever)
    _kg_agent, _kg_checkpointer, _kg_sqlite_conn = await _create_agent(tools, KG_SYSTEM_PROMPT)
    logger.info("✅ KG agent initialized (tools=%d)", len(tools))
    return _kg_agent


async def init_nl2sql_agent():
    """初始化 NL2SQL agent。"""
    global _nl2sql_agent, _nl2sql_checkpointer, _nl2sql_conn
    tools = build_nl2sql_tools()
    _nl2sql_agent, _nl2sql_checkpointer, _nl2sql_conn = await _create_agent(tools, NL2SQL_SYSTEM_PROMPT, temperature=0.3)
    logger.info("✅ NL2SQL agent initialized (tools=%d)", len(tools))
    return _nl2sql_agent


def get_rag_agent():
    return _rag_agent


def get_kg_agent():
    return _kg_agent


def get_nl2sql_agent():
    return _nl2sql_agent


async def close_agents():
    for conn_name in ['_rag_sqlite_conn', '_kg_sqlite_conn', '_nl2sql_conn']:
        conn = globals().get(conn_name)
        if conn:
            await conn.close()