from collections.abc import Generator as StreamGenerator

from app.services.llm_service import LLMService


SYSTEM_PROMPT = """你是一个专业的客服助手。请根据提供的参考文档内容回答用户的问题。

规则：
1. 只使用参考文档中的信息回答问题
2. 如果参考文档中没有相关信息，请明确告知用户你不知道
3. 在回答中引用参考来源，使用 [来源X] 的格式标注
4. 使用中文回答，语气专业友好
5. 回答要简洁准确，不要编造信息"""

MAX_HISTORY = 6


class Generator:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    def build_messages(
        self, query: str, contexts: list[dict], history: list[dict]
    ) -> list[dict]:
        context_text = "\n\n".join(
            f"[来源{i+1}] {item.get('content', '')}"
            for i, item in enumerate(contexts)
        )
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        for msg in history[-MAX_HISTORY:]:
            if "role" in msg and "content" in msg:
                messages.append(msg)

        user_content = f"参考文档：\n{context_text}\n\n用户问题：{query}"
        messages.append({"role": "user", "content": user_content})
        return messages

    def generate_stream(
        self,
        query: str,
        contexts: list[dict],
        history: list[dict],
        temperature: float = 0.7,
        original_query: str | None = None,
    ) -> StreamGenerator[str, None, None]:
        messages = self.build_messages(query, contexts, history)
        yield from self.llm_service.chat_stream(messages, temperature=temperature)
