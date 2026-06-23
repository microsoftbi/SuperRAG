# backend/app/kg/entity_extractor.py
"""Entity extraction from document text using LLM."""

import json
import logging

logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """你是一个实体关系提取器。从以下文本中提取实体和实体间的关系。

实体类型（type字段）：
- person: 人物、职位、角色
- org: 组织、公司、部门、团队
- product: 产品、项目、服务
- concept: 概念、术语、法规、理论
- location: 地点、地区

提取要求：
1. 实体名称用原文中的完整名称
2. 关系描述用简洁的动词短语（如"负责"、"属于"、"位于"、"参与"、"管理"）
3. 如果文本中没有实体或关系，返回空数组

输出严格 JSON 格式（不要 markdown 包裹，不要多余内容）：
{{"entities": [{{"name": "实体名称", "type": "person", "properties": {{}}}}], "relationships": [{{"source": "实体A", "target": "实体B", "type": "关系动词"}}]}}

文本：
{text}"""


class EntityExtractor:
    """对全文进行实体和关系提取，每篇文档只调一次 LLM。"""

    def __init__(self, llm_service):
        self.llm = llm_service

    def extract(self, text: str) -> dict:
        """提取实体和关系。

        Returns:
            {"entities": [...], "relationships": [...]}
        """
        if not text.strip():
            return {"entities": [], "relationships": []}

        truncated = text[:3000]

        messages = [
            {"role": "system", "content": "你是一个实体关系提取助手。"},
            {"role": "user", "content": EXTRACT_PROMPT.format(text=truncated)},
        ]

        try:
            response = "".join(self.llm.chat_stream(messages, temperature=0.1))
            result = self._parse_response(response)
            logger.info(
                "Extracted %d entities, %d relationships",
                len(result.get("entities", [])),
                len(result.get("relationships", [])),
            )
            return result
        except Exception as e:
            logger.error("Entity extraction failed: %s", e)
            return {"entities": [], "relationships": []}

    def _parse_response(self, text: str) -> dict:
        text = text.strip()
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0].strip()
        if not text:
            return {"entities": [], "relationships": []}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse entity extraction response: %s", text[:200])
            return {"entities": [], "relationships": []}