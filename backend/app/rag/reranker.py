# backend/app/rag/reranker.py
"""Re-ranking using batch LLM relevance scoring.

将所有检索结果合并到一条提示词中，让 LLM 一次性打分，
将串行 N 次 LLM 调用降为 1 次。
"""

import re

from app.config import settings
from app.services.llm_service import LLMService

BATCH_RERANK_PROMPT = """你是一个文档相关性评分助手。请判断以下文档片段与用户问题的相关性。

用户问题：{query}

文档片段：
{results}

请对每个文档片段输出一个 0-10 的整数评分，每行一个，格式为：
片段1: <分数>
片段2: <分数>
...

评分标准：
- 0-2：完全不相关
- 3-5：部分相关，但信息不完整或只是泛泛提及
- 6-8：相关，包含了直接回答问题的信息
- 9-10：高度相关，直接且完整地回答了问题

只输出评分，不要任何额外文字。"""


class Reranker:
    """Re-ranker that scores ALL results in a single LLM call."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    def rerank(self, query: str, results: list[dict]) -> list[dict]:
        """Re-rank results using batch LLM scoring (1 call instead of N).

        Args:
            query: Original user query
            results: List of retrieval results

        Returns:
            Re-ranked results sorted by relevance, limited to reranker_top_k
        """
        if not results:
            return []

        top_k = settings.reranker_top_k

        # 构建批量提示词
        result_lines = []
        for i, item in enumerate(results):
            content = item.get("content", "")[:300]  # 每条截断 300 字
            result_lines.append(f"片段{i+1}: {content}")
        results_text = "\n\n".join(result_lines)

        prompt = BATCH_RERANK_PROMPT.format(query=query, results=results_text)
        messages = [
            {"role": "system", "content": "你是一个文档相关性评分助手。"},
            {"role": "user", "content": prompt},
        ]

        # 1 次 LLM 调用
        try:
            response_text = ""
            for chunk in self.llm_service.chat_stream(messages, temperature=0.1):
                response_text += chunk
            scores = self._parse_batch_scores(response_text.strip(), len(results))
        except Exception:
            scores = [0.0] * len(results)

        # 应用分数并排序
        scored = []
        for i, item in enumerate(results):
            item["rerank_score"] = scores[i] if i < len(scores) else 0.0
            scored.append(item)

        scored.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        return scored[:top_k]

    def _parse_batch_scores(self, text: str, expected_count: int) -> list[float]:
        """Parse batch scores from LLM response.

        期望格式：
            片段1: 8
            片段2: 3
            片段3: 9
            ...

        Args:
            text: LLM 返回的文本
            expected_count: 期望的片段数

        Returns:
            float 分数列表，长度 = expected_count，缺失项填 0.0
        """
        scores = [0.0] * expected_count

        # 匹配 "片段N: 数字" 或 "片段N：数字" 或 "N: 数字"
        pattern = re.compile(r"(?:片段)?(\d+)\s*[:：]\s*(\d+)")
        for match in pattern.finditer(text):
            idx = int(match.group(1)) - 1  # 转为 0-based
            raw_score = int(match.group(2))
            normalized = max(0, min(10, raw_score)) / 10.0
            if 0 <= idx < expected_count:
                scores[idx] = normalized

        return scores
