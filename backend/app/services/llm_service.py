from collections.abc import Generator

from openai import OpenAI

from app.config import settings


class LLMService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.volc_api_key,
            base_url=settings.volc_endpoint,
            timeout=60.0,
        )
        self.model = settings.llm_model_name

    def chat(self, messages: list[dict], temperature: float = 0.7) -> str:
        """非流式对话，返回完整内容。"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=False,
        )
        return response.choices[0].message.content or ""

    def chat_stream(
        self, messages: list[dict], temperature: float = 0.7
    ) -> Generator[str, None, None]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    def embed(self, texts: list[str]) -> list[list[float]]:
        """批量向量化，自动按 API 限制分批（火山引擎单次最多 10 条）。"""
        BATCH_SIZE = 10
        all_embeddings = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            response = self.client.embeddings.create(
                model=settings.embedding_model_name,
                input=batch,
            )
            all_embeddings.extend([item.embedding for item in response.data])
        return all_embeddings
