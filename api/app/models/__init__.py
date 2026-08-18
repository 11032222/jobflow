"""ORM 模型统一导出（供 Alembic autogenerate 识别全部表）。"""
from app.models.user import User
from app.models.resume import Resume
from app.models.profile import CandidateProfile, ProfileExperience, ProfileSkill
from app.models.preference import Preference
from app.models.company import Company
from app.models.job import Job
from app.models.job_source import JobSource
from app.models.match_result import MatchResult
from app.models.favorite import Favorite
from app.models.application import Application, ApplicationEvent
from app.models.interview import Interview
from app.models.agent_task import AgentTask, AgentLog
from app.models.system_config import SystemConfig, UserLLMConfig

__all__ = [
    "User",
    "Resume",
    "CandidateProfile",
    "ProfileExperience",
    "ProfileSkill",
    "Preference",
    "Company",
    "Job",
    "JobSource",
    "MatchResult",
    "Favorite",
    "Application",
    "ApplicationEvent",
    "Interview",
    "AgentTask",
    "AgentLog",
    "SystemConfig",
    "UserLLMConfig",
]
