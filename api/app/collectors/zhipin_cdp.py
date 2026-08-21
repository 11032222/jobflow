"""BOSS 直聘 CDP 采集：复用 crawlers/boss-zhipin/boss_cdp.py 的思路。

连接已登录的真实 Chrome（--remote-debugging-port=9222），从 Vue 状态读取明文薪资，
避免 Playwright 被反爬识别。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import subprocess
import sys
from pathlib import Path

import httpx
import websockets

logger = logging.getLogger(__name__)

DEFAULT_PORT = 9222
# api/app/collectors/ -> 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOCAL_PROFILE = PROJECT_ROOT / "auto-zhipin" / "chrome_profile"
BASE_URL = "https://www.zhipin.com"
SEARCH_PATH = "/web/geek/jobs"

VISIBILITY_JS = """
Object.defineProperty(document, 'hidden', {get: () => false});
Object.defineProperty(document, 'visibilityState', {get: () => 'visible'});
"""

EXTRACT_JS = r"""
(() => {
  const seen = new Set();
  let target = null;
  function walk(vm) {
    if (!vm || seen.has(vm)) return;
    seen.add(vm);
    if (vm.jobList && Array.isArray(vm.jobList) && vm.jobList.length) {
      target = vm;
      return;
    }
    if (vm.$children) {
      for (const c of vm.$children) {
        walk(c);
        if (target) return;
      }
    }
  }
  const root = document.getElementById('app');
  walk(root && root.__vue__);
  if (!target) {
    const all = document.querySelectorAll('*');
    for (let i = 0; i < all.length; i++) {
      const vm = all[i].__vue__;
      if (vm && vm.jobList && Array.isArray(vm.jobList) && vm.jobList.length) {
        target = vm;
        break;
      }
    }
  }
  if (!target) return JSON.stringify({ok: false, reason: 'no-joblist'});
  const jobs = target.jobList.map((j) => ({
    title: j.jobName || '',
    salary: j.salaryDesc || '',
    company: j.brandName || '',
    boss_name: j.bossName || '',
    city: j.cityName || '',
    district: [j.areaDistrict, j.businessDistrict].filter(Boolean).join('·'),
    labels: j.jobLabels || [],
    experience: j.jobExperience || '',
    degree: j.jobDegree || '',
    job_type: j.jobType,
    encrypt_job_id: j.encryptJobId || '',
    url: (j.encryptJobId ? '/job_detail/' + j.encryptJobId + '.html' : ''),
  }));
  return JSON.stringify({ok: true, count: jobs.length, hasMore: !!target.hasMore, jobs});
})()
"""


DETAIL_EXTRACT_JS = r"""
(() => {
  const $ = (s) => document.querySelector(s);
  const text = (el) => el ? el.innerText.replace(/\s+/g, ' ').trim() : '';
  const o = {};
  o.status = text($('.job-status span')) || text($('.job-status'));
  const nameEl = $('.job-primary .name');
  o.title = nameEl ? text(nameEl.querySelector('h1')) : '';
  o.salary = nameEl ? text(nameEl.querySelector('.salary')) : '';
  o.company = text($('.brand-name')).replace(/^代招公司[:：]?\s*/, '');
  o.city = text($('.text-city'));
  o.experience = text($('.text-experiece'));
  o.degree = text($('.text-degree'));
  o.description = text($('.job-sec-text'));
  const tags = new Set();
  ['.job-banner .job-tags', '.job-banner .tag-all', '.job-tags', '.job-tags .tag-all']
    .forEach(sel => {
      const el = $(sel);
      if (!el) return;
      el.querySelectorAll('span, li, em').forEach(x => {
        const t = x.innerText.trim();
        if (t && t.length <= 15 && !/感兴趣|立即沟通|在线简历|附件简历/.test(t)) tags.add(t);
      });
    });
  o.welfare = [...tags];
  const bi = $('.job-boss-info');
  if (bi) {
    o.boss_name = text(bi.querySelector('.name'));
    const attr = bi.querySelector('.boss-info-attr');
    const parts = attr ? attr.innerText.split('\u00b7').map(s => s.trim()) : [];
    o.boss_company = parts[0] || '';
    o.boss_title = parts.slice(1).join('\u00b7') || '';
    o.boss_avatar = (bi.querySelector('img') || {}).src || '';
  }
  const interest = $('.btn-interest');
  o.interest_url = interest ? (interest.getAttribute('data-url') || '') : '';
  const chat = $('.btn-startchat');
  o.chat_redirect = chat ? (chat.getAttribute('redirect-url') || '') : '';
  o.url = location.href;
  return JSON.stringify(o);
})()
"""


class CDP:
    def __init__(self, ws):
        self.ws = ws
        self.mid = 0
        self.waiters = []

    @classmethod
    async def connect(cls, port: int) -> "CDP":
        async with httpx.AsyncClient(timeout=10) as client:
            info = (await client.get(f"http://127.0.0.1:{port}/json/version")).json()
        ws = await websockets.connect(info["webSocketDebuggerUrl"], max_size=128 * 1024 * 1024)
        cdp = cls(ws)
        asyncio.create_task(cdp._reader())
        return cdp

    async def _reader(self):
        async for raw in self.ws:
            msg = json.loads(raw)
            if "id" in msg:
                for w in list(self.waiters):
                    if w[0] == msg["id"]:
                        w[1].set_result(msg)
                        self.waiters.remove(w)
                        break

    async def send(self, method, params=None, session_id=None, timeout=60):
        self.mid += 1
        msg = {"id": self.mid, "method": method, "params": params or {}}
        if session_id:
            msg["sessionId"] = session_id
        fut = asyncio.get_running_loop().create_future()
        self.waiters.append((self.mid, fut))
        await self.ws.send(json.dumps(msg))
        return await asyncio.wait_for(fut, timeout)

    async def eval_js(self, js, sid):
        r = await self.send("Runtime.evaluate", {"expression": js, "returnByValue": True}, sid)
        res = r.get("result") or {}
        if res.get("exceptionDetails"):
            desc = (res.get("exceptionDetails", {}).get("exception", {}).get("description", "") or "")
            raise RuntimeError(f"页面 JS 执行失败: {desc[:300]}")
        return res.get("result", {}).get("value")

    async def create_page(self):
        t = await self.send("Target.createTarget", {"url": "about:blank"})
        target_id = t["result"]["targetId"]
        a = await self.send("Target.attachToTarget", {"targetId": target_id, "flatten": True})
        sid = a["result"]["sessionId"]
        try:
            await self.send("Emulation.setFocusEmulationEnabled", {"enabled": True}, sid)
        except Exception:
            pass
        await self.send("Page.addScriptToEvaluateOnNewDocument", {"source": VISIBILITY_JS}, sid)
        return target_id, sid

    async def close_page(self, target_id):
        try:
            await self.send("Target.closeTarget", {"targetId": target_id})
        except Exception:
            pass
        try:
            await self.ws.close()
        except Exception:
            pass


def cdp_port_alive(port: int = DEFAULT_PORT) -> bool:
    try:
        r = httpx.get(f"http://127.0.0.1:{port}/json/version", timeout=0.4)
        if r.status_code != 200:
            return False
        data = r.json()
        return bool(data.get("webSocketDebuggerUrl") or data.get("Browser"))
    except Exception:
        return False


def _chrome_exe() -> Path | None:
    env = os.environ.get("CHROME_PATH")
    candidates = [
        Path(env) if env else None,
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe",
        Path("/usr/bin/google-chrome"),
        Path("/usr/bin/chromium"),
    ]
    for p in candidates:
        if p and p.exists():
            return p
    return None


def get_debug_port() -> int | None:
    """只探测明确的调试端口，避免扫一段区间时被占用端口拖死。"""
    candidates: list[int] = [DEFAULT_PORT]
    for base in (
        LOCAL_PROFILE,
        Path(r"D:\zhipin_chrome_profile"),
        Path.home() / "AppData/Local/Google/Chrome/User Data",
    ):
        f = Path(base) / "DevToolsActivePort"
        if f.exists():
            try:
                first = f.read_text(encoding="utf-8").strip().splitlines()[0]
                if first.strip().isdigit():
                    candidates.append(int(first.strip()))
            except Exception:
                pass
    seen: set[int] = set()
    for p in candidates:
        if p in seen:
            continue
        seen.add(p)
        if cdp_port_alive(p):
            return p
    return None


def launch_debug_chrome() -> dict:
    """启动带 9222 调试口的独立 Chrome，打开 BOSS 登录页。"""
    port = get_debug_port()
    if port is not None:
        return {
            "started": False,
            "already_running": True,
            "cdp_port": port,
            "message": "调试 Chrome 已在运行，请确认窗口里已登录 BOSS 直聘。",
        }
    chrome = _chrome_exe()
    if chrome is None:
        raise RuntimeError("未找到 chrome.exe，请先安装 Google Chrome。")
    LOCAL_PROFILE.mkdir(parents=True, exist_ok=True)
    args = [
        str(chrome),
        f"--remote-debugging-port={DEFAULT_PORT}",
        f"--user-data-dir={LOCAL_PROFILE}",
        "--disable-blink-features=AutomationControlled",
        f"{BASE_URL}/web/user/?ka=header-login",
    ]
    kwargs: dict = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if sys.platform == "win32":
        kwargs["creationflags"] = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(args, **kwargs)
    logger.info("已启动调试 Chrome profile=%s", LOCAL_PROFILE)
    return {
        "started": True,
        "already_running": False,
        "cdp_port": DEFAULT_PORT,
        "message": "已打开调试 Chrome，请在弹出窗口登录 BOSS 直聘，然后再点采集。",
    }



async def fetch_detail(cdp, sid, job: dict) -> dict:
    """导航到职位详情页，抓取描述/福利/招聘者等信息。"""
    url = job.get("url") or ""
    if not url:
        return job
    full = url if url.startswith("http") else f"{BASE_URL}{url}"
    try:
        await cdp.send("Page.navigate", {"url": full}, sid)
        for _ in range(40):
            await asyncio.sleep(1)
            raw = await cdp.eval_js(DETAIL_EXTRACT_JS, sid)
            try:
                d = json.loads(raw or "{}")
            except json.JSONDecodeError:
                d = {}
            if d.get("description") or d.get("title"):
                job["detail"] = d
                job["desc"] = d.get("description", "") or job.get("desc", "")
                job["welfare"] = d.get("welfare") or job.get("welfare", [])
                if d.get("salary"):
                    job["salary"] = d["salary"]
                return job
    except Exception as exc:  # noqa: BLE001
        logger.warning("BOSS 详情抓取失败 %s: %s", url, exc)
    job["desc"] = job.get("desc", "")
    return job


async def crawl_jobs(query: str, city_code: str, salary_code: str | None, max_pages: int, with_detail: bool = True, detail_max: int = 60) -> list[dict]:
    port = get_debug_port()
    if port is None:
        raise RuntimeError(
            "未检测到调试 Chrome。请先运行 crawlers/boss-zhipin/start_chrome.bat "
            "（chrome --remote-debugging-port=9222）并登录 BOSS 直聘后再采集。"
        )

    async with asyncio.timeout(900):
        cdp = await CDP.connect(port)
        tid, sid = await cdp.create_page()
        try:
            params = {"query": query, "city": city_code, "page": 1}
            if salary_code:
                params["salary"] = salary_code
            url = f"{BASE_URL}{SEARCH_PATH}?" + "&".join(f"{k}={v}" for k, v in params.items())
            logger.info("BOSS CDP 导航: %s", url)
            await cdp.send("Page.navigate", {"url": url}, sid)

            for _ in range(60):
                await asyncio.sleep(1)
                n = await cdp.eval_js("document.querySelectorAll('.job-card-box, .job-card-wrapper, .job-card-left').length", sid)
                if n and n > 0:
                    break
            else:
                body = await cdp.eval_js("(document.body ? document.body.innerText : '').slice(0, 200)", sid)
                raise RuntimeError(f"BOSS 页面未出现职位卡片，可能未登录或触发风控。正文: {body!r}")

            all_jobs: list[dict] = []
            seen: set[str] = set()
            prev_count = -1
            stall = 0

            for rnd in range(1, max(1, max_pages) + 1):
                for _ in range(random.randint(3, 6)):
                    delta = random.randint(300, 900)
                    await cdp.eval_js(f"window.scrollBy(0,{delta})", sid)
                    await asyncio.sleep(random.uniform(0.5, 1.2))
                await cdp.eval_js("window.scrollTo(0, document.body.scrollHeight)", sid)
                await asyncio.sleep(2)

                raw = await cdp.eval_js(EXTRACT_JS, sid)
                try:
                    data = json.loads(raw or "{}")
                except json.JSONDecodeError:
                    data = {"ok": False, "reason": "parse-fail"}
                if not data.get("ok"):
                    logger.warning("BOSS 提取失败: %s", data.get("reason"))
                    break

                jobs = data.get("jobs") or []
                for j in jobs:
                    key = j.get("encrypt_job_id") or j.get("url") or j.get("title")
                    if key and key not in seen:
                        seen.add(key)
                        all_jobs.append(j)

                logger.info("BOSS 第 %s 轮累计 %s 条", rnd, len(all_jobs))
                if not data.get("hasMore"):
                    break
                if len(jobs) == prev_count:
                    stall += 1
                    if stall >= 3:
                        break
                else:
                    stall = 0
                prev_count = len(jobs)
                if rnd < max_pages:
                    await asyncio.sleep(random.uniform(1.5, 3.0))
            if with_detail and all_jobs:
                todo = all_jobs[:max(1, detail_max)]
                logger.info("BOSS 抓取详情 %s/%s", len(todo), len(all_jobs))
                for i, job in enumerate(todo, 1):
                    await fetch_detail(cdp, sid, job)
                    if i < len(todo):
                        await asyncio.sleep(random.uniform(1.5, 3.0))
            return all_jobs
        finally:
            await cdp.close_page(tid)


def crawl_jobs_sync(query: str, city_code: str, salary_code: str | None, max_pages: int, with_detail: bool = True, detail_max: int = 60) -> list[dict]:
    """可在 FastAPI 已有事件循环的后台任务里调用。"""
    import concurrent.futures

    def _run():
        return asyncio.run(crawl_jobs(query, city_code, salary_code, max_pages, with_detail=with_detail, detail_max=detail_max))

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _run()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_run).result()
