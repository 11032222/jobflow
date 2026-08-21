"""智联招聘 Adapter：公开 SSR 优先，失败则走已登录调试 Chrome（CDP）。"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime
from urllib.parse import quote

import httpx

from app.collectors.base import PlatformAdapter
from app.services.job_text import format_job_text, parse_job_status, split_job_description

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
    return httpx.Client(timeout=8, headers=DEFAULT_HEADERS, follow_redirects=True, trust_env=False)


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
    description = format_job_text(raw.get("jobDescription") or raw.get("description") or "")
    duties = format_job_text(raw.get("duties")) or None
    reqs = format_job_text(raw.get("requirements_text")) or None
    if description and not (duties and reqs):
        split_d, split_r = split_job_description(description)
        duties = duties or split_d
        reqs = reqs or split_r
    status = parse_job_status(raw.get("status_text"), description, duties, reqs)
    company_info = raw.get("company_info") if isinstance(raw.get("company_info"), dict) else {}

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
        description=description or None,
        responsibilities=duties,
        requirements=reqs,
        publish_time=_parse_time(raw.get("publishTime") or raw.get("firstPublishTime")),
        source="zhaopin",
        source_url=raw.get("positionURL") or raw.get("positionUrl") or "",
        source_job_id=str(source_id),
        status=status,
        company_info=company_info,
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


EXTRACT_CARDS_JS = r"""
(() => {
  const cards = Array.from(document.querySelectorAll('.job-card'));
  const jobs = cards.map((el) => {
    const nameA = el.querySelector('.job-card__name');
    const companyA = el.querySelector('.job-card__company-name');
    const salaryEl = el.querySelector('.job-card__salary');
    const tags = Array.from(el.querySelectorAll('.job-card__skill-tag'))
      .map((x) => (x.innerText || '').trim())
      .filter(Boolean);
    const loc = ((el.querySelector('.job-card__location span') || {}).innerText || '').trim();
    const parts = loc.split(/\s+/).filter(Boolean);
    const href = nameA ? (nameA.href || '') : '';
    const m = href.match(/jobdetail\/([^./]+)/i);
    const edu = tags.find((t) => /初中|高中|中专|大专|本科|硕士|博士/.test(t)) || '';
    const exp = tags.find((t) => /年|经验|应届|在校/.test(t)) || '';
    const jobType = tags.find((t) => /全职|兼职|实习/.test(t)) || '';
    const industry = tags.find((t) => t !== edu && t !== exp && t !== jobType) || '';
    return {
      name: nameA ? nameA.innerText.trim() : '',
      companyName: companyA ? companyA.innerText.trim() : '',
      salary60: salaryEl ? salaryEl.innerText.trim() : '',
      education: edu,
      workingExp: exp,
      industryName: industry,
      workType: jobType,
      jobSkillTags: tags.map((name) => ({ name })),
      workCity: parts[0] || '',
      cityDistrict: parts.slice(1).join(' '),
      number: m ? m[1] : href,
      positionURL: href,
    };
  }).filter((j) => j.name && j.number);
  return JSON.stringify({ ok: true, count: jobs.length, jobs });
})()
"""

DETAIL_JS = r"""
(() => {
  const text = (document.body && document.body.innerText) || '';
  function section(start, ends) {
    const i = text.indexOf(start);
    if (i < 0) return '';
    let rest = text.slice(i + start.length);
    let cut = rest.length;
    for (const e of ends) {
      const j = rest.indexOf('\n' + e);
      const k = rest.indexOf(e);
      const at = j >= 0 ? j : k;
      if (at >= 0 && at < cut) cut = at;
    }
    return rest.slice(0, cut).replace(/^[:：]\s*/, '').trim();
  }
  function firstSection(starts, ends) {
    for (const s of starts) {
      const v = section(s, ends);
      if (v && v.length > 8) return v;
    }
    return '';
  }
  const duties = firstSection(['岗位职责', '工作职责', '职位描述'], ['任职要求', '任职资格', '岗位要求', '工作地点', '公司信息']);
  const req = firstSection(['任职要求', '任职资格', '岗位要求'], ['工作地点', '公司信息', '工商信息']);
  const loc = firstSection(['工作地点'], ['公司信息', '工商信息']);
  const companyBlock = firstSection(['公司信息', '公司介绍'], ['工商信息', '认证资质', '相似职位']);
  const biz = firstSection(['工商信息'], ['认证资质', '相似职位', '以担保']);
  const closed = /停止招聘|职位已关闭|已下线|结束招聘|该职位已失效/.test(text.slice(0, 800));
  const open = /立即投递|立即沟通|招聘中/.test(text.slice(0, 800));
  const lines = (companyBlock || '').split('\n').map(s => s.trim()).filter(Boolean);
  const metaLine = lines.find(t => t.includes('·')) || '';
  const meta = metaLine.split(/[·]/).map(s => s.trim()).filter(Boolean);
  const introIdx = lines.findIndex(t => t.includes('公司介绍'));
  const intro = introIdx >= 0 ? lines.slice(introIdx + 1).join('') : (companyBlock || '');
  return JSON.stringify({
    ok: true,
    duties,
    requirements: req,
    location: loc,
    company_block: companyBlock,
    biz,
    closed,
    open,
    status_text: closed ? '停止招聘' : (open ? '招聘中' : ''),
    company_info: {
      scale: meta.find(t => /人/.test(t)) || '',
      company_type: meta.find(t => /融资|上市|国企|民营|外商/.test(t)) || '',
      industry: meta.find(t => /服务|互联网|软件|咨询|金融|制造|教育|电商/.test(t) && !/公司/.test(t)) || '',
      description: intro || companyBlock || ''
    }
  });
})()
"""


async def _fill_one_zhaopin_detail(cdp, sid, item: dict) -> None:
    url = item.get("positionURL") or ""
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    if not url:
        return
    await cdp.send("Page.navigate", {"url": url}, sid)
    ready = await cdp.wait_eval(
        "document.body && document.body.innerText && "
        "(document.body.innerText.indexOf('任职要求')>=0 || document.body.innerText.indexOf('岗位职责')>=0) ? 1 : 0",
        sid,
        timeout=6,
        interval=0.25,
    )
    if not ready:
        return
    raw = await cdp.eval_js(DETAIL_JS, sid)
    data = json.loads(raw or "{}")
    if not data.get("ok"):
        return
    item["jobDescription"] = "\n".join(
        x for x in (data.get("duties"), data.get("requirements")) if x
    )
    item["duties"] = data.get("duties") or ""
    item["requirements_text"] = data.get("requirements") or ""
    item["status_text"] = data.get("status_text") or ""
    if data.get("closed"):
        item["status_text"] = "停止招聘"
    info = data.get("company_info") or {}
    if data.get("location") and not item.get("cityDistrict"):
        item["cityDistrict"] = data["location"]
    item["company_info"] = info
    if info.get("industry") and not item.get("industryName"):
        item["industryName"] = info["industry"]


async def _fill_zhaopin_details(cdp, sid, jobs: list[dict], detail_max: int = 8) -> None:
    todo = [j for j in jobs if j.get("positionURL")][: max(1, min(detail_max, 8))]
    logger.info("智联并行抓取详情 %s/%s", len(todo), len(jobs))
    sem = asyncio.Semaphore(4)

    async def _one(item: dict) -> None:
        async with sem:
            tid, nsid = await cdp.create_page()
            try:
                await cdp.send("Page.enable", {}, nsid)
                await _fill_one_zhaopin_detail(cdp, nsid, item)
            except Exception as exc:  # noqa: BLE001
                logger.warning("智联详情失败 %s: %s", item.get("positionURL"), exc)
            finally:
                await cdp.close_target(tid)

    if todo:
        await asyncio.gather(*(_one(j) for j in todo))


async def _crawl_zhaopin_cdp(keyword: str, city_code: int, pages: int) -> list[dict]:
    from app.collectors.zhipin_cdp import CDP, get_debug_port

    port = get_debug_port()
    if port is None:
        raise RuntimeError("未检测到调试 Chrome。请先登录智联招聘后再采集。")

    jobs: list[dict] = []
    seen: set[str] = set()
    cdp = await CDP.connect(port)
    tid, sid = await cdp.create_page()
    try:
        await cdp.send("Page.enable", {}, sid)
        for p in range(1, max(1, pages) + 1):
            url = f"https://www.zhaopin.com/jobs?jl={city_code}&kw={quote(keyword)}&p={p}"
            logger.info("智联 CDP 导航: %s", url)
            await cdp.send("Page.navigate", {"url": url}, sid)
            found = await cdp.wait_eval(
                "document.querySelectorAll('.job-card').length",
                sid,
                timeout=8,
                interval=0.25,
            ) or 0
            if not found:
                body = await cdp.eval_js("(document.body ? document.body.innerText : '').slice(0, 200)", sid)
                raise RuntimeError(f"智联页面未出现职位卡片，可能未登录或触发风控。正文: {body!r}")
            raw = await cdp.eval_js(EXTRACT_CARDS_JS, sid)
            data = json.loads(raw or "{}")
            for item in data.get("jobs") or []:
                sid_key = str(item.get("number") or "")
                if not sid_key or sid_key in seen:
                    continue
                seen.add(sid_key)
                jobs.append(item)
            if not data.get("jobs"):
                break
            if p < pages:
                await asyncio.sleep(0.4)
        if jobs:
            await _fill_zhaopin_details(cdp, sid, jobs, detail_max=8)
    finally:
        await cdp.close_page(tid)
    return jobs


def _crawl_zhaopin_cdp_sync(keyword: str, city_code: int, pages: int) -> list[dict]:
    import concurrent.futures

    def _run():
        return asyncio.run(_crawl_zhaopin_cdp(keyword, city_code, pages))

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _run()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_run).result()


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

        http_err = None
        raw_list: list[dict] = []
        from app.collectors.zhipin_cdp import get_debug_port

        if get_debug_port():
            raw_list = _crawl_zhaopin_cdp_sync(keyword, city_code, pages)
        else:
            try:
                with _client() as client:
                    for p in range(page, page + pages):
                        url = f"https://sou.zhaopin.com/?jl={city_code}&kw={keyword}&p={max(p, 1)}"
                        logger.info("智联采集: %s", url)
                        resp = client.get(url)
                        resp.raise_for_status()
                        if "Security Verification" in resp.text or "__INITIAL_STATE__" not in resp.text:
                            raise RuntimeError("智联公开页触发安全验证")
                        state = _extract_state(resp.text)
                        raw_list.extend(state.get("positionList") or [])
            except Exception as exc:  # noqa: BLE001
                http_err = exc
                logger.warning("智联 HTTP 采集失败，尝试 CDP: %s", exc)
                raw_list = _crawl_zhaopin_cdp_sync(keyword, city_code, pages)

        for raw in raw_list:
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
        if http_err and not jobs:
            raise RuntimeError(f"智联采集失败: {http_err}")
        logger.info("智联采集完成: %d 条", len(jobs))
        return jobs

    def get_company_info(self, company_name: str) -> dict | None:
        """智联页面仅含基础公司信息，返回精简结果。"""
        if not company_name:
            return None
        return {"name": company_name, "source": "zhaopin"}
