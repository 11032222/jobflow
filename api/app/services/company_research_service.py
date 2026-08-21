"""公司信息补全：招聘页字段 + 联网搜索摘要。"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from urllib.parse import quote, urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.company import Company

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _client() -> httpx.Client:
    return httpx.Client(timeout=12, headers=HEADERS, follow_redirects=True, trust_env=False)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def search_web(query: str, limit: int = 5) -> list[dict]:
    """Bing / DuckDuckGo 兜底搜索公司公开信息。"""
    results: list[dict] = []
    try:
        results.extend(_search_bing(query, limit))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Bing 搜索失败: %s", exc)
    if len(results) < 2:
        try:
            results.extend(_search_duckduckgo(query, limit))
        except Exception as extra:  # noqa: BLE001
            logger.warning("DuckDuckGo 搜索失败: %s", extra)
    # 去重
    seen: set[str] = set()
    uniq: list[dict] = []
    for item in results:
        key = (item.get("url") or item.get("title") or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append(item)
        if len(uniq) >= limit:
            break
    return uniq


def _search_bing(query: str, limit: int) -> list[dict]:
    url = f"https://www.bing.com/search?q={quote(query)}&setlang=zh-hans"
    with _client() as client:
        resp = client.get(url)
        resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    out: list[dict] = []
    for li in soup.select("li.b_algo")[: limit + 2]:
        a = li.select_one("h2 a")
        cap = li.select_one(".b_caption p") or li.select_one("p")
        if not a:
            continue
        title = _clean(a.get_text())
        href = a.get("href") or ""
        snippet = _clean(cap.get_text()) if cap else ""
        if title:
            out.append({"title": title, "url": href, "snippet": snippet})
        if len(out) >= limit:
            break
    return out


def _search_duckduckgo(query: str, limit: int) -> list[dict]:
    url = "https://html.duckduckgo.com/html/"
    with _client() as client:
        resp = client.post(url, data={"q": query, "kl": "cn-zh"})
        resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    out: list[dict] = []
    for a in soup.select("a.result__a")[:limit]:
        title = _clean(a.get_text())
        href = a.get("href") or ""
        snippet_el = a.find_parent("div", class_="result")
        snippet = ""
        if snippet_el:
            sn = snippet_el.select_one(".result__snippet")
            snippet = _clean(sn.get_text()) if sn else ""
        if title:
            out.append({"title": title, "url": href, "snippet": snippet})
    return out


def _summarize(name: str, hits: list[dict], extra: dict | None, user_id: int | None) -> str:
    bits = [h.get("snippet") or h.get("title") for h in hits if h.get("snippet") or h.get("title")]
    extra = extra or {}
    from app.agents.llm import llm_service

    if llm_service.is_available(user_id) and bits:
        prompt = (
            f"根据以下公开搜索结果，用中文写一段不超过180字的公司简介，客观陈述业务与规模，不要编造。\n"
            f"公司名：{name}\n"
            f"已知字段：{json.dumps(extra, ensure_ascii=False)}\n"
            f"搜索结果：{json.dumps(hits[:5], ensure_ascii=False)}\n"
            "只输出简介正文。"
        )
        text = llm_service.chat_text([{"role": "user", "content": prompt}], user_id=user_id)
        if text:
            return text.strip()[:400]
    if extra.get("description"):
        return str(extra["description"])[:400]
    joined = "；".join(bits[:3])
    if joined:
        return f"{name}：{joined}"[:400]
    industry = extra.get("industry") or "相关"
    scale = extra.get("scale") or ""
    tail = f"，规模{scale}" if scale else ""
    return f"{name}是一家{industry}领域企业{tail}。"


def _name_core(name: str) -> str:
    return re.sub(r"(股份有限公司|有限责任公司|有限公司|集团|控股)$", "", name or "").strip()


def _relevant_hits(name: str, hits: list[dict]) -> list[dict]:
    core = _name_core(name)
    keys = [name, core]
    if len(core) >= 4:
        keys.append(core[:4])
    kept = []
    for hit in hits:
        blob = f"{hit.get('title') or ''} {hit.get('snippet') or ''}"
        if any(k and k in blob for k in keys):
            # 排除只命中省份/城市词条的百科
            if re.search(r"省[，,].*省会|省级行政区|中华人民共和国省级", blob) and core not in blob:
                continue
            kept.append(hit)
    return kept


def research_company(
    db: Session,
    company: Company,
    extra: dict | None = None,
    user_id: int | None = None,
) -> Company:
    """联网搜索并回填公司简介 / 官网 / 行业。"""
    extra = extra or {}
    query = f'"{company.name}" 公司'
    hits = _relevant_hits(company.name, search_web(query, limit=8))
    if not hits:
        hits = _relevant_hits(company.name, search_web(f"{_name_core(company.name)} 公司简介", limit=8))
    known = {
        "industry": extra.get("industry") or company.industry,
        "scale": extra.get("scale") or company.scale,
        "company_type": extra.get("company_type") or company.company_type,
        "address": extra.get("address") or company.address,
        "description": extra.get("description") or company.description,
    }
    summary = _summarize(company.name, hits, known, user_id)
    website = company.website
    for hit in hits:
        host = urlparse(hit.get("url") or "").netloc.lower()
        if host and "bing.com" not in host and "duckduckgo.com" not in host and "baidu.com" not in host:
            if company.name[:2] in host or host.endswith(".com") or host.endswith(".cn"):
                if not website:
                    website = hit.get("url")
                break
    if extra.get("industry") and not company.industry:
        company.industry = extra["industry"]
    if extra.get("scale") and not company.scale:
        company.scale = extra["scale"]
    if extra.get("company_type") and not company.company_type:
        company.company_type = extra["company_type"]
    if extra.get("address") and not company.address:
        company.address = extra["address"]
    if extra.get("logo_url") and not company.logo_url:
        company.logo_url = extra["logo_url"]
    company.description = summary
    company.website = website
    company.profile_json = json.dumps({"sources": hits[:5], "query": query}, ensure_ascii=False)
    company.profile_status = "ANALYZED" if hits or known.get("description") else "FAILED"
    company.profile_updated_at = datetime.now()
    db.add(company)
    db.commit()
    db.refresh(company)
    logger.info("公司研究完成 %s status=%s hits=%s", company.name, company.profile_status, len(hits))
    return company
