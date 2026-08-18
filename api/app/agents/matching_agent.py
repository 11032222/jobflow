"""Matching Agent：岗位匹配分析。LLM 生成可解释的推荐理由与优劣势，fallback 规则引擎。"""
import logging

from app.agents.llm import llm_service

logger = logging.getLogger(__name__)


class MatchingAgent:
    """匹配分析 Agent：在规则分数基础上，用 LLM 生成推荐理由/优势/不足。"""

    def enhance(
        self, profile: dict, job: dict, user_id: int | None = None
    ) -> dict | None:
        """返回 {"recommend_reason", "strengths", "weaknesses"}，LLM 不可用时返回 None。"""
        if not llm_service.is_available(user_id):
            return None
        prompt = (
            "你是招聘匹配分析专家。请基于候选人画像与岗位要求，客观分析匹配情况，只输出 JSON：\n"
            '{"recommend_reason": "综合推荐理由(60-100字)", "strengths": "候选人与岗位匹配的优势(60字内)", '
            '"weaknesses": "候选人的不足或差距(60字内，无则空字符串)"}\n\n'
            f"候选人画像：{self._compact(profile)}\n\n"
            f"岗位信息：{self._compact(job)}"
        )
        data = llm_service.chat_json(
            [{"role": "user", "content": prompt}], user_id=user_id
        )
        if not data or not isinstance(data.get("recommend_reason"), str):
            return None
        return {
            "recommend_reason": data.get("recommend_reason", "").strip(),
            "strengths": str(data.get("strengths", "")).strip(),
            "weaknesses": str(data.get("weaknesses", "")).strip(),
        }

    @staticmethod
    def _compact(data: dict) -> str:
        import json

        try:
            return json.dumps(data, ensure_ascii=False, default=str)[:1200]
        except (TypeError, ValueError):
            return str(data)[:1200]


matching_agent = MatchingAgent()
