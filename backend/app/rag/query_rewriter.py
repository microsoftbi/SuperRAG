# backend/app/rag/query_rewriter.py
"""Query rewriting and coreference resolution for multi-turn conversation."""

from app.services.llm_service import LLMService

REWRITE_SYSTEM_PROMPT = """你是一个专业的搜索查询改写助手。你的任务是根据对话历史，将用户最新的问题改写成适合检索的独立查询。

规则：
1. 解析代词（如"这个"、"它"、"那个"、"它们"等）指代的具体内容
2. 将不完整的问题补充完整
3. 保留原问题的核心意图
4. 直接输出改写后的查询，不要任何解释或前缀
5. 如果问题已经很清晰无需改写，则原样输出"""


class QueryRewriter:
    """Rewrites user queries based on conversation history for better retrieval."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    def rewrite(self, query: str, history: list[dict]) -> str:
        """Rewrite the user query based on conversation history for better retrieval.

        Args:
            query: The user's latest query
            history: List of previous messages [{"role": str, "content": str}]

        Returns:
            Rewritten query string
        """
        if not history or len(history) < 2:
            return query

        recent_history = history[-4:]
        history_text = "\n".join(
            f"{'用户' if m['role'] == 'user' else '助手'}: {m['content']}"
            for m in recent_history
        )

        messages = [
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"对话历史：\n{history_text}\n\n"
                    f"当前问题：{query}\n\n改写后的查询："
                ),
            },
        ]

        rewritten = ""
        for chunk in self.llm_service.chat_stream(messages, temperature=0.3):
            rewritten += chunk

        result = rewritten.strip().strip('"\'')
        return result if result else query
