import json
import logging
from collections.abc import Generator

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.volc_api_key,
            base_url=settings.volc_endpoint,
            timeout=60.0,
        )
        self.model = settings.llm_model_name

    def llm_chunk(self, document_content: str) -> list[str]:
        """Use LLM to intelligently chunk a document into meaningful segments."""
        prompt = f"""你是一个文档分块助手。请将以下文档内容分割成有意义的、语义完整的块。

要求：
1. 每个块应该是一个语义完整的段落或章节
2. 保持内容的连贯性和逻辑完整性
3. 不要破坏段落或句子的完整性
4. 每个块的内容不宜过长也不宜过短（建议200-800字）
5. 直接返回JSON格式的结果

请以以下JSON格式返回（只返回JSON，不要有其他内容）：
{{"chunks": ["块1的内容", "块2的内容", ...]}}

文档内容如下：
---
{document_content}
---"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                reasoning_effort=None,
            )
            content = response.choices[0].message.content or ""
            # Try to parse JSON from the response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)
            chunks = result.get("chunks", [])
            if not chunks:
                chunks = [document_content]
            return chunks
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"LLM chunk error: {e}")
            paragraphs = [p.strip() for p in document_content.split("\n\n") if p.strip()]
            if not paragraphs:
                paragraphs = [document_content]
            return paragraphs

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
        logger.info(
            "embed: base_url=%s model=%s api_key_set=%s texts_count=%d",
            self.client.base_url,
            settings.embedding_model_name,
            bool(self.client.api_key),
            len(texts),
        )
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            try:
                response = self.client.embeddings.create(
                    model=settings.embedding_model_name,
                    input=batch,
                )
                all_embeddings.extend([item.embedding for item in response.data])
                logger.info("embed batch %d OK (%d items)", i // BATCH_SIZE, len(batch))
            except Exception as e:
                logger.error("embed batch %d FAILED: %s (type=%s)", i // BATCH_SIZE, e, type(e).__name__)
                logger.error("embed config: base_url=%s model=%s api_key_set=%s",
                             self.client.base_url, settings.embedding_model_name, bool(self.client.api_key))
                raise RuntimeError(
                    f"Embedding调用失败: {e}\n"
                    f"base_url={self.client.base_url} "
                    f"model={settings.embedding_model_name} "
                    f"api_key_set={bool(self.client.api_key)}"
                ) from e
        return all_embeddings