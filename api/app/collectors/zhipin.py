"""BOSS 直聘 Adapter：HTTP 公开接口优先，失败则走 CDP（crawlers/boss-zhipin/boss_cdp）。"""
from __future__ import annotations

import logging
import re
from datetime import datetime

import httpx

from app.collectors.base import PlatformAdapter
from app.collectors.zhipin_cdp import crawl_jobs_sync, get_debug_port, launch_debug_chrome
from app.collectors.zhaopin import parse_salary

logger = logging.getLogger(__name__)

# BOSS 城市代码（与 crawlers/boss-zhipin README 一致，可从 URL 的 city 参数核对）
CITY_CODES = {
    "全国": "100010000",
    "北京": "101010100",
    "上海": "101020100",
    "广州": "101280100",
    "深圳": "101280600",
    "杭州": "101210100",
    "成都": "101270100",
    "南京": "101190100",
    "武汉": "101200100",
    "西安": "101110100",
    "苏州": "101190400",
    "天津": "101030100",
    "重庆": "101040100",
    "长沙": "101250100",
    "郑州": "101180100",
    "青岛": "101120200",
    "合肥": "101220100",
    "东莞": "101281600",
    "佛山": "101280800",
    "宁波": "101210400",
    "厦门": "101230200",
    "济南": "101120100",
    "福州": "101230100",
    "无锡": "101190200",
    "昆明": "101290100",
    "大连": "101070200",
    "沈阳": "101070100",
    "哈尔滨": "101050100",
    "长春": "101060100",
    "石家庄": "101090100",
    "南昌": "101240100",
}
DEFAULT_CITY = "100010000"

# BOSS 薪资筛选项（K/月）
# 402 3K以下 / 403 3-5K / 404 5-10K / 405 10-20K / 406 20-50K / 407 50K以上
SALARY_BANDS = [
    (0, 3000, "402"),
    (3000, 5000, "403"),
    (5000, 10000, "404"),
    (10000, 20000, "405"),
    (20000, 50000, "406"),
    (50000, 10**9, "407"),
]

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.zhipin.com/web/geek/job",
}


def city_to_code(city: str | None) -> str:
    if not city:
        return DEFAULT_CITY
    city = city.strip()
    if city.isdigit():
        return city
    return CITY_CODES.get(city, DEFAULT_CITY)


def salary_to_code(salary_min: int | None, salary_max: int | None) -> str | None:
    """把元/月区间映射到 BOSS 薪资筛选项。"""
    if salary_min is None and salary_max is None:
        return None
    lo = salary_min if salary_min is not None else 0
    for band_lo, band_hi, code in SALARY_BANDS:
        if lo >= band_lo and lo < band_hi:
            return code
    return None


def _job_type_text(raw) -> str | None:
    mapping = {0: "全职", 1: "全职", 2: "兼职", 3: "实习", 4: "校招"}
    if raw is None or raw == "":
        return "全职"
    if isinstance(raw, int) or (isinstance(raw, str) and raw.isdigit()):
        return mapping.get(int(raw), "全职")
    return str(raw)



_RESP_HEADINGS = {"岗位职责", "工作职责", "职位描述", "职责描述", "主要职责", "你需要做", "你将负责"}
_REQ_HEADINGS = {"任职要求", "岗位要求", "任职资格", "工作要求", "职位要求", "我们需要你", "希望你具备"}


def _split_job_description(text: str | None) -> tuple[str | None, str | None]:
    """把详情页描述拆成「岗位职责 / 任职要求」两段。"""
    if not text or not text.strip():
        return None, None
    parts = re.split(r"(岗位职责|工作职责|职位描述|职责描述|主要职责|你需要做|你将负责|任职要求|岗位要求|任职资格|工作要求|职位要求|我们需要你|希望你具备)", text.strip())
    resp: list[str] = []
    req: list[str] = []
    current: str | None = None
    for part in parts:
        key = part.strip()
        if key in _RESP_HEADINGS:
            current = "resp"
        elif key in _REQ_HEADINGS:
            current = "req"
        elif key and current == "resp":
            resp.append(key)
        elif key and current == "req":
            req.append(key)
    return ("\n".join(resp) or None), ("\n".join(req) or None)
def _normalize_raw(raw: dict) -> dict | None:
    title = (raw.get("title") or raw.get("jobName") or "").strip()
    source_id = raw.get("encrypt_job_id") or raw.get("encryptJobId") or raw.get("jobId")
    if not title or not source_id:
        return None
    company = (raw.get("company") or raw.get("brandName") or raw.get("boss_name") or "").strip()
    salary_text = raw.get("salary") or raw.get("salaryDesc")
    salary_min, salary_max = parse_salary(salary_text)
    labels = raw.get("labels") or raw.get("jobLabels") or []
    if isinstance(labels, str):
        labels = [x.strip() for x in re.split(r"[|/,，]", labels) if x.strip()]
    path = raw.get("url") or ""
    if path and not path.startswith("http"):
        path = "https://www.zhipin.com" + path
    elif not path and source_id:
        path = f"https://www.zhipin.com/job_detail/{source_id}.html"

    detail = raw.get("detail") or {}
    description = (
        raw.get("desc")
        or raw.get("description")
        or raw.get("postDescription")
        or detail.get("description")
        or ""
    ).strip()
    responsibilities, requirements = _split_job_description(description)
    welfare = detail.get("welfare") or []
    merged_tags = list(labels)
    for tag in welfare:
        if tag and tag not in merged_tags:
            merged_tags.append(tag)
    if not salary_text and detail.get("salary"):
        salary_text = detail.get("salary")
        salary_min, salary_max = parse_salary(salary_text)

    return PlatformAdapter._build_job(
        title=title,
        company_name=company,
        city=raw.get("city") or raw.get("cityName"),
        district=raw.get("district") or raw.get("areaDistrict"),
        salary_min=salary_min,
        salary_max=salary_max,
        salary_text=salary_text,
        education=raw.get("degree") or raw.get("jobDegree"),
        experience=raw.get("experience") or raw.get("jobExperience"),
        job_type=_job_type_text(raw.get("job_type") or raw.get("jobType")),
        industry=None,
        tags=merged_tags,
        description=description or None,
        responsibilities=responsibilities,
        requirements=requirements,
        publish_time=datetime.now(),
        source="zhipin",
        source_url=path,
        source_job_id=str(source_id),
    )


class ZhipinAdapter(PlatformAdapter):
    platform = "zhipin"

    def search_jobs(
        self,
        keyword: str,
        city: str | None = None,
        page: int = 1,
        page_size: int = 30,
        **kwargs,
    ) -> list[dict]:
        city_code = city_to_code(city)
        salary_code = salary_to_code(kwargs.get("salary_min"), kwargs.get("salary_max"))
        pages = max(1, int(kwargs.get("pages") or 1))
        logger.info("BOSS 采集 keyword=%s city=%s/%s salary=%s pages=%s", keyword, city, city_code, salary_code, pages)

        raw_jobs: list[dict] = []
        http_err = None
        try:
            raw_jobs = self._search_http(keyword, city_code, salary_code, pages, page_size)
        except Exception as exc:  # noqa: BLE001
            http_err = exc
            logger.warning("BOSS HTTP 采集失败，尝试 CDP: %s", exc)

        if not raw_jobs:
            raw_jobs = crawl_jobs_sync(keyword, city_code, salary_code, pages)
            if http_err:
                logger.info("BOSS 已回退 CDP，HTTP 错误已忽略")

        jobs = []
        for raw in raw_jobs:
            job = _normalize_raw(raw)
            if job:
                jobs.append(job)
            if len(jobs) >= page_size * pages:
                break
        logger.info("BOSS 采集完成: %d 条", len(jobs))
        return jobs

    def _search_http(
        self,
        keyword: str,
        city_code: str,
        salary_code: str | None,
        pages: int,
        page_size: int,
    ) -> list[dict]:
        """尝试公开 JSON 接口；未登录时通常为空，由调用方回退 CDP。"""
        collected: list[dict] = []
        params_base = {
            "scene": 1,
            "query": keyword,
            "city": city_code,
            "pageSize": min(page_size, 30),
        }
        if salary_code:
            params_base["salary"] = salary_code
        url = "https://www.zhipin.com/wapi/zpgeek/search/joblist.json"
        with httpx.Client(timeout=20, headers=DEFAULT_HEADERS, follow_redirects=True) as client:
            for p in range(1, pages + 1):
                resp = client.get(url, params={**params_base, "page": p})
                resp.raise_for_status()
                data = resp.json()
                zp = data.get("zpData") or {}
                job_list = zp.get("jobList") or []
                if not job_list:
                    msg = data.get("message") or data.get("code")
                    if not collected:
                        raise RuntimeError(f"BOSS HTTP 无数据: {msg}")
                    break
                collected.extend(job_list)
        return collected

    def get_company_info(self, company_name: str) -> dict | None:
        if not company_name:
            return None
        return {"name": company_name, "source": "zhipin"}


def zhipin_ready() -> dict:
    port = get_debug_port()
    return {
        "id": "zhipin",
        "name": "BOSS直聘",
        "ready": port is not None,
        "cdp_port": port,
        "hint": None
        if port
        else "请先点击「启动调试 Chrome」并在弹出窗口登录 BOSS 直聘（也可双击 crawlers/boss-zhipin/start_chrome.bat）",
    }
