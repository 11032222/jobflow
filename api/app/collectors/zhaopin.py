"""智联招聘 Adapter：解析 sou.zhaopin.com 的 SSR 页面 __INITIAL_STATE__。"""
import json
import logging
import re
from datetime import datetime

import httpx

from app.collectors.base import PlatformAdapter

logger = logging.getLogger(__name__)

# 智联常用城市代码（cityId）
CITY_CODES = {
    "北京": 530, "上海": 538, "天津": 639, "重庆": 551,
    "深圳": 765, "杭州": 653, "广州": 681, "成都": 801,
    "苏州": 727, "武汉": 741, "南京": 635, "西安": 701,
    "长沙": 749, "郑州": 719, "青岛": 715, "大连": 600,
    "沈阳": 596, "合肥": 664, "厦门": 698, "宁波": 716,
    "济南": 704, "昆明": 757, "南昌": 665, "哈尔滨": 575,
    "长春": 587, "石家庄": 632, "福州": 692, "无锡": 729,
    "佛山": 762, "东莞": 763,
}
CODE_TO_CITY = {v: k for k, v in CITY_CODES.items()}

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.zhaopin.com/",
}

# 用于从城市名反查代码；若未收录则默认使用北京
DEFAULT_CITY_ID = 530


def _client() -> httpx.Client:
    return httpx.Client(timeout=25, headers=DEFAULT_HEADERS, follow_redirects=True)


def parse_salary(text: str | None) -> tuple[int | None, int | None]:
    """解析薪资文本，返回 (min, max) 元/月。支持 '1.4-1.5万' / '20-40K·16薪' / '8000-12000元' / '面议'。"""
    if not text:
        return None, None
    text = str(text).strip()
    if "面议" in text or "面谈" in text or "不限" in text:
        return None, None
    # 去掉「·16薪」以免把薪数当成金额
    text = re.sub(r"[·•.\s]*\d+\s*薪", "", text)
    nums = [float(n) for n in re.findall(r"[\d.]+", text)]
    if not nums:
        return None, None
    if "万" in text and "元" not in text:
        unit = 10000
    elif re.search(r"[kK千]", text):
        unit = 1000
    else:
        unit = 1
    if len(nums) >= 2:
        return int(nums[0] * unit), int(nums[1] * unit)
    return int(nums[0] * unit), None


def _normalize_job(raw: dict, city_code: int) -> dict | None:
    """将智联 positionList 元素标准化为 Job dict。"""
    name = raw.get("name")
    if not name:
        return None
    company_name = raw.get("companyName") or ""
    salary_text = raw.get("salary60") or raw.get("salaryReal")
    salary_min, salary_max = parse_salary(salary_text)
    tags = []
    for tag in raw.get("jobSkillTags") or []:
        if isinstance(tag, dict) and tag.get("name"):
            tags.append(tag["name"])

    source_id = raw.get("number") or str(raw.get("jobId") or "")
    if not source_id:
        return None
    city = raw.get("workCity") or CODE_TO_CITY.get(city_code) or ""

    return PlatformAdapter._build_job(
        title=name.strip(),
        company_name=company_name.strip(),
        city=city,
        district=raw.get("cityDistrict") or None,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_text=salary_text,
        education=raw.get("education") or None,
        experience=raw.get("workingExp") or None,
        job_type=raw.get("workType") or None,
        industry=raw.get("industryName") or None,
        tags=tags,
        description=raw.get("jobDescription") or None,
        responsibilities=None,
        requirements=None,
        publish_time=_parse_time(raw.get("publishTime") or raw.get("firstPublishTime")),
        source="zhaopin",
        source_url=raw.get("positionURL") or raw.get("positionUrl") or "",
        source_job_id=str(source_id),
    )


def _parse_time(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None


def _extract_state(html: str) -> dict:
    m = re.search(r"__INITIAL_STATE__=(\{.*?\})\s*</script>", html, re.S)
    if not m:
        raise RuntimeError("无法从页面解析 __INITIAL_STATE__")
    raw = re.sub(r":undefined", ":null", m.group(1))
    return json.loads(raw)


class ZhaopinAdapter(PlatformAdapter):
    platform = "zhaopin"

    def search_jobs(
        self,
        keyword: str,
        city: str | None = None,
        page: int = 1,
        page_size: int = 30,
        **kwargs,
    ) -> list[dict]:
        pages = max(1, int(kwargs.get("pages") or 1))
        city_code = CITY_CODES.get(city or "", DEFAULT_CITY_ID)
        jobs: list[dict] = []
        seen: set[str] = set()
        with _client() as client:
            for p in range(page, page + pages):
                url = f"https://sou.zhaopin.com/?jl={city_code}&kw={keyword}&p={max(p, 1)}"
                logger.info("智联采集: %s", url)
                resp = client.get(url)
                resp.raise_for_status()
                state = _extract_state(resp.text)
                for raw in state.get("positionList") or []:
                    job = _normalize_job(raw, city_code)
                    if not job:
                        continue
                    sid = job["source_job_id"]
                    if sid in seen:
                        continue
                    seen.add(sid)
                    jobs.append(job)
                    if len(jobs) >= page_size * pages:
                        break
                if len(jobs) >= page_size * pages:
                    break
        logger.info("智联采集完成: %d 条", len(jobs))
        return jobs

    def get_company_info(self, company_name: str) -> dict | None:
        """智联页面仅含基础公司信息，返回精简结果。"""
        if not company_name:
            return None
        return {"name": company_name, "source": "zhaopin"}
