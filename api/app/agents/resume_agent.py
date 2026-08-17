"""Resume Agent：将简历文本解析为结构化求职画像。LLM 优先，规则引擎 fallback。"""
import logging
import re
from datetime import date

from app.agents.llm import llm_service

logger = logging.getLogger(__name__)

# 常见技能词表（规则引擎用）
COMMON_SKILLS = [
    "Java", "Spring", "Spring Boot", "Spring Cloud", "MyBatis", "MySQL", "Redis",
    "Python", "Django", "Flask", "FastAPI", "Go", "Golang", "Vue.js", "React",
    "JavaScript", "TypeScript", "HTML", "CSS", "Linux", "Docker", "Kubernetes",
    "Git", "Maven", "Gradle", "RabbitMQ", "Kafka", "Elasticsearch", "MongoDB",
    "PostgreSQL", "Oracle", "SQL", "Hadoop", "Spark", "Hive", "Flink",
    "TensorFlow", "PyTorch", "机器学习", "深度学习", "NLP", "C++", "C#",
    "PHP", "Tableau", "Excel", "Selenium", "Appium", "JUnit", "JMeter",
    "Nginx", "消息队列", "微服务", "分布式", "大数据", "数据分析",
]


class ResumeAgent:
    """简历解析 Agent。"""

    def parse(self, raw_text: str) -> dict:
        text = raw_text or ""
        if not text.strip():
            return {"status": "EMPTY", "profile": None}
        if llm_service.available:
            result = self._llm_parse(text)
            if result:
                result["source"] = "LLM"
                return {"status": "SUCCESS", "profile": result}
        profile = self._rule_parse(text)
        profile["source"] = "RULE"
        return {"status": "SUCCESS", "profile": profile}

    def _llm_parse(self, text: str) -> dict | None:
        prompt = (
            "你是简历解析助手。请从下面的简历文本中提取结构化信息，只输出 JSON，不要任何其他内容。\n"
            "输出格式：\n"
            "{\n"
            '  "name": "姓名", "title": "求职意向职位", "phone": "电话", "email": "邮箱",\n'
            '  "city": "所在城市", "years_of_experience": 整数, "education_level": "博士/硕士/本科/大专",\n'
            '  "school": "毕业学校", "major": "专业", "summary": "30-60字个人简介",\n'
            '  "skills": [{"name": "技能名", "level": "beginner/intermediate/advanced/expert", "years": 整数}],\n'
            '  "experiences": [{"type": "education/work/project/certificate/award/other",\n'
            '    "school_or_company": "学校或公司名", "degree": "学历(教育)", "major": "专业(教育)",\n'
            '    "title": "职位或项目名", "start_date": "YYYY-MM", "end_date": "YYYY-MM 或 null",\n'
            '    "description": "描述"}]\n'
            "}\n"
            "注意：简历中不存在的信息填 null 或空数组，不要编造。\n\n"
            f"简历文本：\n{text[:6000]}"
        )
        data = llm_service.chat_json([{"role": "user", "content": prompt}])
        if not data:
            return None
        return self._validate_llm_output(data)

    def _validate_llm_output(self, data: dict) -> dict | None:
        if not isinstance(data.get("name"), str) and not isinstance(data.get("title"), str):
            return None
        data.setdefault("skills", [])
        data.setdefault("experiences", [])
        for exp in data["experiences"]:
            if not isinstance(exp, dict):
                continue
            if not exp.get("type"):
                exp["type"] = "other"
        return data

    # ---- 规则引擎 fallback ----
    def _rule_parse(self, text: str) -> dict:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        phone = self._find_phone(text)
        email = self._find_email(text)
        name = self._find_name(text, lines)
        school = self._find_school(text)
        skills = self._find_skills(text)
        return {
            "name": name,
            "title": None,
            "phone": phone,
            "email": email,
            "city": None,
            "years_of_experience": self._find_years(text),
            "education_level": self._find_education(text),
            "school": school,
            "major": None,
            "summary": None,
            "skills": [{"name": s, "level": None, "years": None} for s in skills[:12]],
            "experiences": [],
        }

    @staticmethod
    def _find_phone(text: str) -> str | None:
        m = re.search(r"(?<!\d)1[3-9]\d{9}(?!\d)", text)
        if m:
            return m.group(0)
        m = re.search(r"\d{3,4}-\d{7,8}", text)
        return m.group(0) if m else None

    @staticmethod
    def _find_email(text: str) -> str | None:
        m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
        return m.group(0) if m else None

    @staticmethod
    def _find_name(text: str, lines: list[str]) -> str | None:
        for pattern in [r"姓名[：:\s]*([\u4e00-\u9fa5]{2,4})", r"([\u4e00-\u9fa5]{2,3})\s*[\u4e00-\u9fa5]{0,4}(简历|求职)"]:
            m = re.search(pattern, text)
            if m:
                return m.group(1)
        if lines and re.search(r"[\u4e00-\u9fa5]{2,4}", lines[0]) and len(lines[0]) <= 12:
            return lines[0]
        return None

    @staticmethod
    def _find_school(text: str) -> str | None:
        m = re.search(r"[\u4e00-\u9fa5]{2,15}(大学|学院)", text)
        return m.group(0) if m else None

    @staticmethod
    def _find_skills(text: str) -> list[str]:
        found = []
        lowered = text.lower()
        for skill in COMMON_SKILLS:
            if len(skill) <= 1:
                continue
            pattern = skill.lower().replace("+", r"\+").replace(".", r"\.").replace("#", r"\#")
            if re.search(rf"(?<![a-zA-Z0-9]){pattern}(?![a-zA-Z0-9])", lowered):
                found.append(skill)
        # 按技能在原文本中出现顺序排序
        found.sort(key=lambda s: lowered.find(s.lower()))
        return found

    @staticmethod
    def _find_years(text: str) -> int | None:
        m = re.search(r"(\d+)\s*年(以上)?(工作经验|开发经验|后端经验|从业经验)", text)
        if m:
            return int(m.group(1))
        return None

    @staticmethod
    def _find_education(text: str) -> str | None:
        for level in ("博士", "硕士", "本科", "大专", "中专"):
            if level in text:
                return level
        return None


resume_agent = ResumeAgent()
