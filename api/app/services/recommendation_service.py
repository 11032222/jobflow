"""推荐匹配服务（规则引擎 fallback，后续可接 LLM）。"""
import json
import logging
import re

from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.match_result import MatchResult
from app.models.preference import Preference
from app.models.profile import CandidateProfile, ProfileSkill
from app.services.job_text import education_rank, experience_years_required

logger = logging.getLogger(__name__)

EDUCATION_ORDER = {"博士": 5, "硕士": 4, "研究生": 4, "本科": 3, "大专": 2, "专科": 2, "中专": 1, "高中": 1, "不限": 0}


def _parse_experience_years(text: str | None) -> tuple[int, int] | None:
    """从 '3-5年' / '经验不限' / '5年以上' 解析出 (min, max)。"""
    if not text:
        return None
    if "不限" in text or "无经验" in text:
        return (0, 0)
    nums = [int(n) for n in re.findall(r"\d+", text)]
    if not nums:
        return None
    if "以上" in text or "应届" in text:
        return (nums[0], 99)
    if len(nums) == 1:
        return (0, nums[0])
    return (nums[0], nums[1])


def _skill_score(profile: CandidateProfile, job: Job) -> float:
    """技能匹配：岗位要求技能与候选人技能的覆盖率。"""
    job_tags: list[str] = []
    if job.tags:
        try:
            job_tags = [str(t).lower() for t in json.loads(job.tags)]
        except (json.JSONDecodeError, TypeError):
            job_tags = []
    # 从要求文本提取可能的技能词（基于候选人已知技能反查）
    profile_skills = {s.name.lower() for s in (profile.skills or [])}
    if not profile_skills:
        return 50.0

    hit = sum(1 for t in job_tags if any(t in sk or sk in t for sk in profile_skills))
    if job_tags:
        return round(hit / len(job_tags) * 100, 2)

    # 无 tags 时，从 requirements 中检查候选人技能是否出现
    req = (job.requirements or "").lower()
    hit = sum(1 for sk in profile_skills if sk and sk in req)
    return round(min(hit / len(profile_skills) * 100, 100), 2)


def _experience_score(profile: CandidateProfile, job: Job) -> tuple[float, str | None]:
    req = _parse_experience_years(job.experience)
    years = profile.years_of_experience or 0
    min_years = experience_years_required(job.experience)
    if req is None and min_years <= 0:
        return 60.0, None
    lo, hi = req if req is not None else (min_years, 99)
    if years >= lo and (years <= hi or hi >= 99):
        return (90.0 if years <= (hi + 1) or hi >= 99 else 70.0), None
    if years < lo:
        # 差 1 年以内只扣分；明显低于要求视为硬性不满足
        if lo - years >= 2:
            return max(0.0, 25 - (lo - years) * 5), (
                f"经验不满足硬性要求：岗位要求{job.experience or str(lo)+'年'}，当前{years}年"
            )
        return max(30.0, 100 - (lo - years) * 20), None
    return 60.0, None


def _education_score(profile: CandidateProfile, job: Job) -> tuple[float, str | None]:
    """学历硬性门槛：候选人低于岗位要求时记硬性不满足。"""
    req_label, req_level = education_rank(job.education)
    cand_label, cand_level = education_rank(profile.education_level)
    if req_level <= 0:
        return 100.0, None
    if cand_level >= req_level:
        return 100.0 if cand_level == req_level else 100.0, None
    gap = req_level - cand_level
    score = max(0.0, 20.0 - gap * 10)
    reason = f"学历不满足硬性要求：岗位要求{req_label}，当前为{cand_label or '未填写'}"
    return score, reason


def _preference_score(
    profile: CandidateProfile, job: Job, pref: Preference | None
) -> float:
    if pref is None:
        return 60.0
    score = 60.0
    cities = [c.strip() for c in json.loads(pref.cities or "[]")]
    positions = [p.strip() for p in json.loads(pref.target_positions or "[]")]
    keywords = [k.strip() for k in json.loads(pref.keywords or "[]")]

    if cities and job.city and any(c in job.city for c in cities):
        score += 15
    if positions and any(p.lower() in job.title.lower() for p in positions):
        score += 15
    if keywords and any(k.lower() in job.title.lower() for k in keywords):
        score += 10
    if pref.salary_min and job.salary_max and job.salary_max < pref.salary_min:
        score -= 10
    if pref.salary_max and job.salary_min and job.salary_min > pref.salary_max:
        score -= 10
    return round(max(0.0, min(score, 100.0)), 2)


def _recommend_level(score: float) -> str:
    if score >= 90:
        return "S"
    if score >= 75:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    return "D"


def _build_reason(
    skill: float,
    exp: float,
    edu: float,
    pref: float,
    level: str,
    hard_reasons: list[str] | None = None,
) -> str:
    reasons = []
    if hard_reasons:
        reasons.extend(hard_reasons)
    if skill >= 75:
        reasons.append("技能与岗位要求高度匹配")
    elif skill >= 55:
        reasons.append("技能匹配度一般")
    else:
        reasons.append("技能匹配度偏低，建议针对性补充")
    if exp >= 80:
        reasons.append("工作经历符合岗位要求")
    elif exp < 55 and not any("经验" in r for r in (hard_reasons or [])):
        reasons.append("工作年限与岗位要求存在差距")
    if edu >= 90:
        reasons.append("学历满足岗位要求")
    elif edu <= 20 and not any("学历" in r for r in (hard_reasons or [])):
        reasons.append("学历未达到岗位要求")
    if pref >= 75:
        reasons.append("与求职偏好契合度高")
    return "；".join(reasons) if reasons else "综合评估后给出该推荐"


def compute_match(
    db: Session,
    user_id: int,
    profile: CandidateProfile,
    job: Job,
    pref: Preference | None = None,
) -> MatchResult:
    """匹配分析：规则引擎评分 + LLM 可解释增强。"""
    skill = _skill_score(profile, job)
    exp, exp_fail = _experience_score(profile, job)
    edu, edu_fail = _education_score(profile, job)
    pref_score = _preference_score(profile, job, pref)
    hard_reasons = [r for r in (edu_fail, exp_fail) if r]
    total = round(skill * 0.4 + exp * 0.25 + edu * 0.2 + pref_score * 0.15, 2)
    if hard_reasons:
        total = min(total, 35.0)
        level = "D"
    else:
        level = _recommend_level(total)

    result = (
        db.query(MatchResult)
        .filter(MatchResult.profile_id == profile.id, MatchResult.job_id == job.id)
        .first()
    )
    if result is None:
        result = MatchResult(user_id=user_id, profile_id=profile.id, job_id=job.id)
        db.add(result)

    result.skill_score = skill
    result.experience_score = exp
    result.education_score = edu
    result.preference_score = pref_score
    result.match_score = total
    result.recommend_level = level
    result.hard_fail = bool(hard_reasons)
    result.hard_fail_reasons = json.dumps(hard_reasons, ensure_ascii=False)
    result.recommend_reason = _build_reason(skill, exp, edu, pref_score, level, hard_reasons)
    result.status = "SUCCESS"
    result.model_used = "rule"

    # LLM 增强：生成可解释推荐理由与优劣势
    from app.agents.matching_agent import matching_agent

    profile_data = {
        "name": profile.name,
        "title": profile.title,
        "city": profile.city,
        "education": profile.education_level,
        "school": profile.school,
        "major": profile.major,
        "years": profile.years_of_experience,
        "skills": [s.name for s in (profile.skills or [])],
        "summary": profile.summary,
    }
    job_data = {
        "title": job.title,
        "company": job.company_id,
        "city": job.city,
        "salary": job.salary_text,
        "education": job.education,
        "experience": job.experience,
        "tags": job.tags,
        "requirements": job.requirements,
        "description": job.description,
    }
    enhanced = matching_agent.enhance(profile_data, job_data, user_id=user_id)
    if enhanced:
        reason = enhanced["recommend_reason"]
        if hard_reasons:
            reason = "；".join(hard_reasons) + "。" + reason
        result.recommend_reason = reason
        result.strengths = enhanced["strengths"] or None
        result.weaknesses = (enhanced["weaknesses"] or "") or ("；".join(hard_reasons) if hard_reasons else None)
        result.model_used = "llm"

    db.commit()
    db.refresh(result)
    return result
