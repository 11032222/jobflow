"""平台适配器抽象基类（README §9.1：search_jobs / get_job_detail / get_company_info）。"""
from abc import ABC, abstractmethod
from datetime import datetime


class PlatformAdapter(ABC):
    """招聘平台适配器统一接口。返回标准化 Job dict。"""

    platform: str = "base"

    @abstractmethod
    def search_jobs(
        self,
        keyword: str,
        city: str | None = None,
        page: int = 1,
        page_size: int = 30,
    ) -> list[dict]:
        """搜索岗位，返回标准化岗位字典列表。"""

    @abstractmethod
    def get_company_info(self, company_name: str) -> dict | None:
        """获取公司公开信息（用于 Company Agent 后续扩展）。"""

    # ---- 标准化工具 ----

    @staticmethod
    def _build_job(
        *,
        title: str,
        company_name: str,
        city: str | None,
        district: str | None,
        salary_min: int | None,
        salary_max: int | None,
        salary_text: str | None,
        education: str | None,
        experience: str | None,
        job_type: str | None,
        industry: str | None,
        tags: list[str],
        description: str | None,
        responsibilities: str | None,
        requirements: str | None,
        publish_time: datetime | None,
        source: str,
        source_url: str,
        source_job_id: str,
    ) -> dict:
        """统一标准化 Job 字典。"""
        return {
            "title": title,
            "company_name": company_name,
            "city": city,
            "district": district,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_text": salary_text,
            "education": education,
            "experience": experience,
            "job_type": job_type,
            "industry": industry,
            "tags": tags,
            "description": description,
            "responsibilities": responsibilities,
            "requirements": requirements,
            "publish_time": publish_time,
            "source": source,
            "source_url": source_url,
            "source_job_id": source_job_id,
        }
