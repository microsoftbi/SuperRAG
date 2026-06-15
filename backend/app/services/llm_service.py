from collections.abc import Generator

from openai import OpenAI

from app.config import settings


class LLMService:
    def __init__(self):
        self.client = OpenAI(
            api_key=f"{settings.volc_access_key}:{settings.volc_secret_key}",
            base_url=f"https://{settings.volc_endpoint}/api/v3",
            timeout=60.0,
        )
        self.model = settings.llm_model_name

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
        response = self.client.embeddings.create(
            model=settings.embedding_model_name,
            input=texts,
        )
        return [item.embedding for item in response.data]
