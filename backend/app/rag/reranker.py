# backend/app/rag/reranker.py
"""Re-ranking using LLM-based relevance scoring."""

import re

from app.config import settings
from app.services.llm_service import LLMService

RERANK_PROMPT = """请判断以下文档片段与用户问题的相关性。

用户问题：{query}

文档片段：{content}

请只返回一个 0-10 的整数评分，其中：
- 0-2：完全不相关
- 3-5：部分相关，但信息不完整或只是泛泛提及
- 6-8：相关，包含了直接回答问题的信息
- 9-10：高度相关，直接且完整地回答了问题

只返回数字，不要任何其他内容。"""


class Reranker:
    """Re-ranker that uses LLM to score document relevance."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    def rerank(self, query: str, results: list[dict]) -> list[dict]:
        """Re-rank results using LLM relevance scoring.

        Args:
            query: Original user query
            results: List of retrieval results

        Returns:
            Re-ranked results sorted by relevance, limited to reranker_top_k
        """
        if not results:
            return []

        top_k = settings.reranker_top_k

        scored = []
        for item in results:
            content = item.get("content", "")[:500]
            prompt = RERANK_PROMPT.format(query=query, content=content)

            messages = [
                {"role": "system", "content": "你是一个文档相关性评分助手。"},
                {"role": "user", "content": prompt},
            ]

            try:
                response_text = ""
                for chunk in self.llm_service.chat_stream(messages, temperature=0.1):
                    response_text += chunk

                score = self._parse_score(response_text.strip())
                item["rerank_score"] = score
                scored.append(item)
            except Exception:
                item["rerank_score"] = 0
                scored.append(item)

        scored.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        return scored[:top_k]

    def _parse_score(self, text: str) -> float:
        """Parse numeric score from LLM response."""
        matches = re.findall(r"\d+", text)
        if matches:
            score = int(matches[0])
            return max(0, min(10, score)) / 10.0
        return 0.0
