"""
AI 写作助手服务

通过 LLM 提供真实智能写作辅助功能：
1. 文本润色（polish_text）
2. 语法检查（check_grammar）
3. 智能续写（smart_continue）
4. 风格转换（transform_style）
5. 标题生成（generate_titles）
6. 摘要提取（extract_summary）
"""
import json
import logging
from typing import List, Dict, Optional

from shared.services.ai.llm_client import llm_client, LLMClient

logger = logging.getLogger(__name__)

# ── System prompts ──────────────────────────────

POLISH_SYS = "你是一个专业的中文编辑。请润色文本，改进表达和流畅度。返回 JSON：{\"polished_text\": \"润色后文本\", \"suggestions\": [{\"type\": \"style\", \"message\": \"说明\"}], \"improvement_score\": 0-100}"
GRAMMAR_SYS = "你是一个中文语法专家。检查语法问题，返回 JSON：{\"issues\": [{\"type\": \"grammar\", \"message\": \"问题\", \"position\": 0, \"original\": \"原文\", \"suggestion\": \"修改\"}]}"
CONTINUE_SYS = "你是一个专业作家。根据文本内容续写 100-200 字，风格一致。只输出续写内容。"
STYLE_SYS = "你是一个风格转换专家。将文本转为目标风格（formal/casual/concise/detailed）。返回 JSON：{\"result\": \"转换后文本\"}"
TITLES_SYS = "你是一个内容策划专家。根据内容生成标题建议。返回 JSON：{\"titles\": [\"标题1\", \"标题2\"]}"
SUMMARY_SYS = "你是一个摘要生成器。提取核心内容，200 字以内。返回 JSON：{\"summary\": \"摘要\"}"


class AIWritingAssistantService:
    """AI 写作助手服务（基于 LLM）"""

    def __init__(self):
        self._llm: Optional[LLMClient] = None

    @property
    def llm(self) -> Optional[LLMClient]:
        if self._llm is None:
            self._llm = llm_client
        return self._llm

    async def _call_llm(self, system_prompt: str, user_text: str) -> Optional[Dict]:
        client = self.llm
        if not client or not client.is_available:
            return None
        try:
            result = await client.chat_completion(
                messages=[{"role": "user", "content": user_text}],
                system_prompt=system_prompt,
                response_format="json_object",
            )
            if result.get("success"):
                content = result["content"].strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1].rsplit("```", 1)[0]
                return json.loads(content)
            return None
        except Exception as e:
            logger.warning(f"[AIWritingAssistant] LLM call failed: {e}")
            return None

    async def _call_llm_text(self, system_prompt: str, user_text: str) -> Optional[str]:
        client = self.llm
        if not client or not client.is_available:
            return None
        try:
            result = await client.chat_completion(
                messages=[{"role": "user", "content": user_text}],
                system_prompt=system_prompt,
            )
            if result.get("success"):
                return result["content"].strip()
            return None
        except Exception as e:
            logger.warning(f"[AIWritingAssistant] LLM call failed: {e}")
            return None

    async def polish_text(self, text: str) -> Dict:
        if not text.strip():
            return {'polished_text': '', 'suggestions': [], 'improvement_score': 0.0}
        result = await self._call_llm(POLISH_SYS, text)
        if result and 'polished_text' in result:
            return result
        return {'polished_text': text.strip(), 'suggestions': [], 'improvement_score': 0.0}

    async def check_grammar(self, text: str) -> List[Dict]:
        if not text.strip():
            return []
        result = await self._call_llm(GRAMMAR_SYS, text)
        if result and 'issues' in result:
            return result['issues']
        return []

    async def smart_continue(self, text: str, max_length: int = 200) -> str:
        if not text.strip():
            return ""
        result = await self._call_llm_text(CONTINUE_SYS, text)
        return (result or "")[:max_length]

    async def transform_style(self, text: str, target_style: str = 'formal') -> str:
        if not text.strip():
            return ""
        prompt = f"目标风格：{target_style}（formal=正式, casual=轻松, concise=简洁, detailed=详细）\n\n{text}"
        result = await self._call_llm(STYLE_SYS, prompt)
        if result and 'result' in result:
            return result['result']
        return text

    async def generate_titles(self, content: str, count: int = 5, style: str = 'normal') -> List[str]:
        if not content.strip():
            return []
        prompt = f"标题风格：{style}，生成 {count} 个。\n\n{content}"
        result = await self._call_llm(TITLES_SYS, prompt)
        if result and 'titles' in result:
            return result['titles'][:count]
        return []

    async def extract_summary(self, text: str, max_length: int = 200) -> str:
        if not text.strip():
            return ""
        result = await self._call_llm(SUMMARY_SYS, text)
        if result and 'summary' in result:
            return result['summary'][:max_length]
        return ""


ai_writing_assistant = AIWritingAssistantService()
