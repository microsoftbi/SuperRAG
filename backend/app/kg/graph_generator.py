# backend/app/kg/graph_generator.py
"""KG-specific generator with dedicated system prompt for entity-relation answers."""

from collections.abc import Generator as StreamGenerator
import logging

logger = logging.getLogger(__name__)

KG_SYSTEM_PROMPT = """你是一个专业的客服助手，请根据知识图谱中的实体关系信息回答用户的问题。

知识图谱显示了实体（人物、组织、产品等）之间的关联关系，可以帮助你做关系推理和多跳回答。

规则：
1. 只使用图谱信息中的关系回答问题
2. 如果图谱信息不足以完整回答问题，请基于已知信息如实告知
3. 描述关系时用自然语言，如"张三负责A项目"、"A项目属于创新事业部"
4. 使用中文回答，语气专业友好
5. 不要编造不存在的实体或关系"""

KG_USER_TEMPLATE = """知识图谱上下文（实体关系描述）：
{kg_context}

相关文档片段：
{context_text}

用户问题：{query}"""

MAX_HISTORY = 6


class GraphGenerator:
    """KG 管线专用的生成器。"""

    def __init__(self, llm_service):
        self.llm = llm_service

    def build_messages(self, query: str, contexts: list[dict],
                       kg_context_text: str, history: list[dict] | None = None) -> list[dict]:
        """构建带有 KG 上下文的消息列表。"""
        # 文档片段
        snippet_lines = []
        for i, ctx in enumerate(contexts):
            content = ctx.get("content", "")
            source_info = f"[来源{i+1}] {content[:300]}"
            snippet_lines.append(source_info)
        context_text = "\n\n".join(snippet_lines)

        messages = [{"role": "system", "content": KG_SYSTEM_PROMPT}]

        for msg in (history or [])[-MAX_HISTORY:]:
            if "role" in msg and "content" in msg:
                messages.append(msg)

        user_content = KG_USER_TEMPLATE.format(
            kg_context=kg_context_text or "（无特定关系信息）",
            context_text=context_text or "（无相关文档片段）",
            query=query,
        )
        messages.append({"role": "user", "content": user_content})
        return messages

    def generate(self, query: str, contexts: list[dict],
                 kg_context_text: str,
                 history: list[dict] | None = None,
                 temperature: float = 0.7) -> StreamGenerator[str, None, None]:
        """生成 KG 回答（流式）。"""
        messages = self.build_messages(query, contexts, kg_context_text, history)
        yield from self.llm.chat_stream(messages, temperature=temperature)