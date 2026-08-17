"""Mock Adapter：生成演示岗位数据，用于无网络/演示场景。"""
from datetime import datetime, timedelta

from app.collectors.base import PlatformAdapter

DEMO_JOBS = [
    {
        "title": "Java后端开发工程师（模拟）",
        "company": "云启科技",
        "city": "上海",
        "salary_text": "1.8-2.8万·14薪",
        "education": "本科",
        "experience": "3-5年",
        "job_type": "全职",
        "tags": ["Java", "Spring Boot", "MySQL", "Redis"],
        "desc": "负责核心业务系统后端研发，参与高并发架构设计。",
    },
    {
        "title": "Java开发实习生（模拟）",
        "company": "云启科技",
        "city": "上海",
        "salary_text": "200-300元/天",
        "education": "本科",
        "experience": "经验不限",
        "job_type": "实习",
        "tags": ["Java", "Spring", "MySQL"],
        "desc": "协助完成业务功能开发与测试，提供导师辅导。",
    },
    {
        "title": "Python后端开发工程师（模拟）",
        "company": "智算互联",
        "city": "北京",
        "salary_text": "2-3.5万·16薪",
        "education": "本科",
        "experience": "3-5年",
        "job_type": "全职",
        "tags": ["Python", "FastAPI", "MySQL", "Redis"],
        "desc": "负责 AI 平台后端服务研发。",
    },
    {
        "title": "前端开发工程师（Vue）（模拟）",
        "company": "数聚未来",
        "city": "杭州",
        "salary_text": "1.8-3万·15薪",
        "education": "本科",
        "experience": "1-3年",
        "job_type": "全职",
        "tags": ["Vue.js", "JavaScript", "Element Plus"],
        "desc": "负责中后台产品前端研发。",
    },
]


def _parse_salary(text: str) -> tuple[int | None, int | None]:
    import re

    if not text:
        return None, None
    nums = [float(n) for n in re.findall(r"[\d.]+", text)]
    if not nums:
        return None, None
    unit = 10000 if "万" in text and "元" not in text else 1
    if len(nums) >= 2:
        return int(nums[0] * unit), int(nums[1] * unit)
    return int(nums[0] * unit), None


class MockAdapter(PlatformAdapter):
    platform = "mock"

    def search_jobs(
        self,
        keyword: str,
        city: str | None = None,
        page: int = 1,
        page_size: int = 30,
    ) -> list[dict]:
        jobs = []
        for idx, item in enumerate(DEMO_JOBS):
            if keyword and keyword.lower() not in item["title"].lower():
                continue
            if city and city not in item["city"]:
                continue
            min_s, max_s = _parse_salary(item["salary_text"])
            jobs.append(
                self._build_job(
                    title=item["title"],
                    company_name=item["company"],
                    city=item["city"],
                    district=None,
                    salary_min=min_s,
                    salary_max=max_s,
                    salary_text=item["salary_text"],
                    education=item["education"],
                    experience=item["experience"],
                    job_type=item["job_type"],
                    industry="互联网",
                    tags=item["tags"],
                    description=item["desc"],
                    responsibilities=None,
                    requirements=None,
                    publish_time=datetime.now() - timedelta(days=idx),
                    source="mock",
                    source_url="",
                    source_job_id=f"mock-{keyword}-{idx}",
                )
            )
        return jobs

    def get_company_info(self, company_name: str) -> dict | None:
        if not company_name:
            return None
        return {"name": company_name, "source": "mock"}
