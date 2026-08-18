"""v1 路由汇总。"""
from fastapi import APIRouter

from app.api.v1 import (
    applications,
    auth,
    companies,
    interviews,
    jobs,
    preferences,
    profiles,
    recommendations,
    resumes,
    settings,
    system,
    tasks,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["简历"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["求职画像"])
api_router.include_router(preferences.router, prefix="/preferences", tags=["求职偏好"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["岗位"])
api_router.include_router(companies.router, prefix="/companies", tags=["公司"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["推荐"])
api_router.include_router(applications.router, prefix="/applications", tags=["投递"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["面试"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Agent任务"])
api_router.include_router(system.router, prefix="/system", tags=["系统状态"])
api_router.include_router(settings.router, prefix="/settings", tags=["模型配置"])
