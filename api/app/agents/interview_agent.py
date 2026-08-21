"""Interview Agent：面试复盘总结，输出考察方向、薄弱项与复习建议。"""
import json
import logging

from app.agents.llm import llm_service

logger = logging.getLogger(__name__)


class InterviewAgent:
    """复盘分析 Agent：基于面试记录与问答列表，生成结构化复盘结果。"""

    def parse_transcript(
        self,
        transcript: str,
        user_id: int | None = None,
    ) -> list[dict]:
        """把整段面试对话转写文本拆成结构化问答列表。"""
        transcript = (transcript or "").strip()
        if not transcript or not llm_service.is_available(user_id):
            return []

        prompt = (
            "你是面试记录整理助手。下面是一段面试对话的语音转写文本，"
            "请把其中面试官提出的问题和候选人的回答整理成结构化问答。\n\n"
            "要求：\n"
            "1. 识别面试官提问与候选人回答，忽略寒暄、自我介绍等与考察无关的内容；\n"
            "2. 一个问题对应一条记录，把候选人对该问题的回答合并进 answer；\n"
            "3. 若转写中难以区分提问与回答，尽量按语义切分，保证 question 非空；\n"
            "4. 只输出 JSON 数组，不要 Markdown 代码块或解释，格式为：\n"
            '[{"question": "...", "answer": "..."}]\n\n'
            f"转写文本：\n{transcript}"
        )
        data = llm_service.chat_json(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            user_id=user_id,
        )

        items: list = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and isinstance(data.get("questions"), list):
            items = data["questions"]

        result = []
        for item in items:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question") or "").strip()
            answer = str(item.get("answer") or item.get("my_answer") or "").strip()
            if question:
                result.append({"question": question, "my_answer": answer})
        return result

    def review(
        self,
        interview: dict,
        questions: list[dict],
        user_id: int | None = None,
    ) -> dict | None:
        if not llm_service.is_available(user_id):
            return None

        payload = {
            "company_name": interview.get("company_name"),
            "job_title": interview.get("job_title"),
            "interview_type": interview.get("interview_type"),
            "round_no": interview.get("round_no"),
            "notes": interview.get("notes"),
            "feedback": interview.get("feedback"),
        }
        prompt = (
            "你是资深面试复盘教练。请根据面试信息和问答记录，客观分析并只输出 JSON，"
            "字段如下：\n"
            '{"summary": "本次面试总体总结(80-150字)", '
            '"focus_areas": ["主要考察方向1", "方向2"], '
            '"questions": [{"id": 问题ID, "category": "该问题所属分类", '
            '"mastery": "mastered|partial|missed"}], '
            '"weaknesses": ["暴露的薄弱项"], '
            '"knowledge_points": [{"topic": "知识点", "level": "掌握程度简短描述", '
            '"note": "复习要点"}], '
            '"review_advice": "后续复习与提升建议(80-150字)"}\n\n'
            "mastery 判定规则：mastered=回答完整准确，partial=回答不完整，"
            "missed=基本不会或答错。questions 必须与输入的问题一一对应，保留原 id。\n\n"
            f"面试信息：{json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
            f"问答记录：{json.dumps(questions, ensure_ascii=False, default=str)}"
        )
        data = llm_service.chat_json(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
            user_id=user_id,
        )
        if not isinstance(data, dict) or not isinstance(data.get("summary"), str):
            return None
        return self._normalize(data)

    @staticmethod
    def _normalize(data: dict) -> dict:
        questions = []
        for q in data.get("questions") or []:
            if not isinstance(q, dict) or q.get("id") is None:
                continue
            mastery = str(q.get("mastery", "partial"))
            if mastery not in ("mastered", "partial", "missed"):
                mastery = "partial"
            questions.append(
                {"id": int(q["id"]), "category": str(q.get("category") or "").strip(),
                 "mastery": mastery}
            )

        def as_str_list(value) -> list[str]:
            if not isinstance(value, list):
                return []
            return [str(x).strip() for x in value if str(x).strip()]

        points = []
        for p in data.get("knowledge_points") or []:
            if not isinstance(p, dict):
                continue
            points.append(
                {
                    "topic": str(p.get("topic") or "").strip(),
                    "level": str(p.get("level") or "").strip(),
                    "note": str(p.get("note") or "").strip(),
                }
            )
        return {
            "summary": str(data.get("summary", "")).strip(),
            "focus_areas": as_str_list(data.get("focus_areas")),
            "questions": questions,
            "weaknesses": as_str_list(data.get("weaknesses")),
            "knowledge_points": [x for x in points if x["topic"]],
            "review_advice": str(data.get("review_advice", "")).strip(),
        }


interview_agent = InterviewAgent()
