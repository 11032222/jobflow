"""Interview Agent：面试复盘分析（文档 3.10 面试总结 Agent、6.6 面试复盘流程）。

双通道：优先 LLM，不可用或输出不合法时降级规则引擎，两条通道产出同一 schema。

本模块只做「理解」——输入纯 dict、输出纯 dict，不接触 Session、不写库、不管状态
（Agent 与业务解耦原则）。持久化与状态流转由 interview_review_service 负责。
"""
import json
import logging

from app.agents.llm import llm_service
from app.models.interview import SELF_RESULT_SCORE

logger = logging.getLogger(__name__)

# 规则引擎知识点关键词表（LLM 不可用时的兜底分类依据）
KEYWORD_TABLE: dict[str, list[str]] = {
    "Java基础": [
        "hashmap", "concurrenthashmap", "arraylist", "集合", "泛型", "反射",
        "jvm", "gc", "垃圾回收", "类加载", "线程", "synchronized", "volatile",
        "aqs", "线程池", "juc", "锁",
    ],
    "Spring": [
        "spring", "springboot", "ioc", "aop", "bean", "事务", "mvc",
        "starter", "自动装配", "循环依赖",
    ],
    "Redis": [
        "redis", "缓存", "持久化", "rdb", "aof", "穿透", "击穿", "雪崩",
        "分布式锁", "过期策略", "跳表", "zset",
    ],
    "MySQL": [
        "mysql", "索引", "b+树", "explain", "隔离级别", "mvcc", "事务",
        "分库分表", "慢查询", "回表", "sql",
    ],
    "消息队列": ["kafka", "rabbitmq", "rocketmq", "消息队列", "mq", "削峰", "幂等"],
    "计算机网络": ["tcp", "udp", "http", "https", "三次握手", "四次挥手", "dns", "cookie", "session"],
    "操作系统": ["进程", "线程切换", "内存管理", "虚拟内存", "死锁", "io多路复用", "epoll"],
    "算法与数据结构": ["算法", "链表", "二叉树", "排序", "动态规划", "双指针", "复杂度", "手撕"],
    "分布式与架构": ["分布式", "微服务", "注册中心", "负载均衡", "限流", "熔断", "一致性", "cap"],
    "项目与软技能": [
        "项目", "难点", "职业规划", "为什么", "自我介绍", "团队", "优缺点", "反问",
    ],
}

_WEAK_THRESHOLD = 0.6
_MAX_PROMPT_CHARS = 1200


class InterviewAgent:
    """面试复盘 Agent。"""

    def review(
        self,
        interview: dict,
        questions: list[dict],
        job: dict | None = None,
        user_id: int | None = None,
    ) -> dict:
        """产出复盘结果。questions 每项需含 id / question / self_result。

        必定返回合法结果：LLM 不可用或输出不合法时自动降级规则引擎。
        """
        if not questions:
            return {
                "source": "RULE",
                "model_name": None,
                "summary": "本次面试没有录入任何问题，无法生成复盘。",
                "dimensions": [],
                "weak_points": [],
                "review_points": [],
                "question_labels": [],
            }

        if llm_service.is_available(user_id):
            result = self._review_by_llm(interview, questions, job, user_id)
            if result is not None:
                return result
            logger.info("Interview Agent LLM 输出不可用，降级规则引擎 user_id=%s", user_id)

        return self._review_by_rule(questions)

    # ------------------------------------------------------------ LLM 通道

    def _review_by_llm(
        self,
        interview: dict,
        questions: list[dict],
        job: dict | None,
        user_id: int | None,
    ) -> dict | None:
        """LLM 通道。输出不合法返回 None，由调用方降级。"""
        # 数据安全原则：只带岗位与问题，不带联系人 / 电话 / 会议链接
        job_brief = ""
        if job:
            job_brief = f"\n面试岗位：{job.get('title') or ''} @ {job.get('company_name') or ''}"

        lines = []
        for q in questions:
            lines.append(
                f"- id={q['id']} | 问题：{q.get('question', '')} "
                f"| 我的回答：{q.get('my_answer') or '（未填写）'} "
                f"| 自评：{q.get('self_result', 'PARTIAL')}"
            )
        q_text = "\n".join(lines)[:_MAX_PROMPT_CHARS]

        prompt = (
            "你是资深技术面试复盘专家。请分析下面这场面试的问题与作答情况，只输出 JSON：\n"
            '{"summary": "本次面试总结(80-120字)", '
            '"dimensions": [{"category": "考察方向", "count": 题数, "score": 0到1的掌握度, "stars": 1到5的星级}], '
            '"weak_points": ["回答不好的问题原文", "..."], '
            '"review_points": ["需要复习的知识点", "..."], '
            '"question_labels": [{"question_id": 题目id, "category": "分类", "knowledge_point": "涉及知识点"}]}\n\n'
            "要求：question_labels 必须使用下面给出的真实 id，不要编造；"
            "自评 MASTERED=已掌握、PARTIAL=回答不完整、FAILED=完全不会。"
            f"{job_brief}\n\n面试问题：\n{q_text}"
        )

        data = llm_service.chat_json([{"role": "user", "content": prompt}], user_id=user_id)
        normalized = self._normalize(data, questions)
        if normalized is None:
            return None
        normalized["source"] = "LLM"
        normalized["model_name"] = llm_service.active_model(user_id)
        return normalized

    def _normalize(self, data: dict | None, questions: list[dict]) -> dict | None:
        """校验并规整 LLM 输出。任一必需结构缺失即判定不可用。"""
        if not isinstance(data, dict):
            return None
        summary = data.get("summary")
        dims = data.get("dimensions")
        if not isinstance(summary, str) or not summary.strip():
            return None
        if not isinstance(dims, list) or not dims:
            return None

        clean_dims = []
        for d in dims:
            if not isinstance(d, dict) or not d.get("category"):
                continue
            score = self._to_float(d.get("score"), default=0.5)
            clean_dims.append(
                {
                    "category": str(d["category"])[:64],
                    "count": self._to_int(d.get("count"), default=0),
                    "score": round(score, 2),
                    "stars": self._to_int(d.get("stars"), default=max(1, round(score * 5))),
                }
            )
        if not clean_dims:
            return None

        # 关键：只接受传入集合里真实存在的 question_id，模型可能编造 id
        valid_ids = {q["id"] for q in questions}
        labels = []
        for lab in data.get("question_labels") or []:
            if not isinstance(lab, dict):
                continue
            qid = self._to_int(lab.get("question_id"), default=-1)
            if qid not in valid_ids:
                logger.debug("丢弃不存在的 question_id=%s", lab.get("question_id"))
                continue
            labels.append(
                {
                    "question_id": qid,
                    "category": str(lab.get("category") or "")[:64] or None,
                    "knowledge_point": str(lab.get("knowledge_point") or "")[:512] or None,
                }
            )

        return {
            "summary": summary.strip(),
            "dimensions": clean_dims,
            "weak_points": self._to_str_list(data.get("weak_points")),
            "review_points": self._to_str_list(data.get("review_points")),
            "question_labels": labels,
        }

    @staticmethod
    def _to_str_list(value) -> list[str]:
        """规整为字符串列表。非 list（如模型误返回单个字符串）包成单元素列表，
        避免字符串被逐字符迭代成 ['T','C','P',...]。"""
        if value is None:
            return []
        if isinstance(value, str):
            value = [value] if value.strip() else []
        elif not isinstance(value, list):
            return []
        return [str(v)[:500] for v in value if v][:20]

    # ----------------------------------------------------------- 规则引擎通道

    def _review_by_rule(self, questions: list[dict]) -> dict:
        """规则引擎：关键词分类 + 掌握度加权。LLM 不可用时保证功能可用。"""
        grouped: dict[str, list[dict]] = {}
        labels = []
        for q in questions:
            text = q.get("question", "")
            category = q.get("category") or self.classify(text)
            # 规则通道下命中的关键词即知识点，否则「待复习知识点」在无模型时永远为空
            knowledge_point = q.get("knowledge_point") or self.extract_points(text, category)
            q = {**q, "knowledge_point": knowledge_point}
            grouped.setdefault(category, []).append(q)
            labels.append(
                {
                    "question_id": q["id"],
                    "category": category,
                    "knowledge_point": knowledge_point,
                }
            )

        dimensions, weak_points = [], []
        for category, items in grouped.items():
            avg = sum(
                SELF_RESULT_SCORE.get(i.get("self_result"), 0.0) for i in items
            ) / len(items)
            dimensions.append(
                {
                    "category": category,
                    "count": len(items),
                    "score": round(avg, 2),
                    "stars": max(1, round(avg * 5)),
                }
            )
            if avg < _WEAK_THRESHOLD:
                weak_points += [
                    i.get("question", "") for i in items if i.get("self_result") != "MASTERED"
                ]
        dimensions.sort(key=lambda d: d["score"])

        weak_categories = [d["category"] for d in dimensions if d["score"] < _WEAK_THRESHOLD]
        review_points = [
            i.get("knowledge_point") or i.get("question", "")
            for cat in weak_categories
            for i in grouped[cat]
            if i.get("self_result") != "MASTERED"
        ]
        summary = (
            f"本次面试共 {len(questions)} 题，覆盖 {len(dimensions)} 个方向；"
            f"薄弱方向：{'、'.join(weak_categories) if weak_categories else '无'}。"
        )
        return {
            "source": "RULE",
            "model_name": None,
            "summary": summary,
            "dimensions": dimensions,
            "weak_points": weak_points[:20],
            "review_points": review_points[:20],
            "question_labels": labels,
        }

    @staticmethod
    def extract_points(question: str, category: str) -> str | None:
        """从问题文本里抽取命中的关键词作为知识点，未命中返回 None。"""
        keywords = KEYWORD_TABLE.get(category)
        if not keywords:
            return None
        text = (question or "").lower()
        hits = [k for k in keywords if k in text]
        return " / ".join(hits[:3]) if hits else None

    @staticmethod
    def classify(question: str) -> str:
        """关键词命中数最多的类别即为分类，全不命中归入「其他」。"""
        text = (question or "").lower()
        best, hits = "其他", 0
        for category, keywords in KEYWORD_TABLE.items():
            n = sum(1 for k in keywords if k in text)
            if n > hits:
                best, hits = category, n
        return best

    # ---------------------------------------------------------------- 工具

    @staticmethod
    def _to_int(value, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_float(value, default: float = 0.0) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _compact(data: dict) -> str:
        try:
            return json.dumps(data, ensure_ascii=False, default=str)[:_MAX_PROMPT_CHARS]
        except (TypeError, ValueError):
            return str(data)[:_MAX_PROMPT_CHARS]


interview_agent = InterviewAgent()
