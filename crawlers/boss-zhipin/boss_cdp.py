"""BOSS直聘 CDP 爬虫 —— 真实 Chrome + 原生 CDP，从 Vue 状态读取明文薪资职位列表。

为什么可行（对比 Playwright）:
- Playwright/Selenium 会被 BOSS 反爬识别（navigator.webdriver、注入脚本等），页面被清空/跳转。
- 这里用原生 Chrome DevTools Protocol 连接真实已登录 Chrome，不注入任何自动化特征，页面正常加载。
- 职位数据从页面 Vue 组件状态读取，salaryDesc 为明文，绕开前端字体反爬。

用法（先启动调试 Chrome: start_chrome.bat）:
  python boss_cdp.py --query Python --city 100010000                 # 默认全国
  python boss_cdp.py --query Python --city 100010000 --salary 404    # 5-10K
  python boss_cdp.py --query Python --pages 3 -O jobs.json

城市/薪资代码: 浏览器登录后选择筛选条件，从地址栏 URL 参数获取。
"""
import argparse
import asyncio
import json
import random
import sys
import time
from pathlib import Path

import requests
import websockets

DEFAULT_PORT = 9222
BASE_URL = "https://www.zhipin.com"
# 搜索页（注意是复数 /jobs）
SEARCH_PATH = "/web/geek/jobs"

# 让后台标签页在页面看来“可见且有焦点”，保证无限滚动正常触发
VISIBILITY_JS = """
Object.defineProperty(document, 'hidden', {get: () => false});
Object.defineProperty(document, 'visibilityState', {get: () => 'visible'});
"""

# 在页面里找 Vue 根组件并提取职位列表（含明文薪资）
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
    // 兜底：遍历所有带 __vue__ 的元素
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
    boss_title: j.bossTitle || '',
    boss_online: !!j.bossOnline,
    city: j.cityName || '',
    district: [j.areaDistrict, j.businessDistrict].filter(Boolean).join('·'),
    labels: (j.jobLabels || []).join(' | '),
    experience: j.jobExperience || '',
    degree: j.jobDegree || '',
    job_type: j.jobType,
    valid: j.jobValidStatus,
    encrypt_job_id: j.encryptJobId || '',
    lid: j.lid || '',
    security_id: j.securityId || '',
    url: (j.encryptJobId ? '/job_detail/' + j.encryptJobId + '.html' : ''),
  }));
  return JSON.stringify({ok: true, count: jobs.length, hasMore: !!target.hasMore, page: (target.pageVo||{}).page, jobs});
})()
"""


class CDP:
    """极简 CDP 客户端（websockets，不带任何浏览器自动化特征）。"""

    def __init__(self, ws):
        self.ws = ws
        self.mid = 0
        self.events = []
        self.waiters = []

    @classmethod
    async def connect(cls, port):
        info = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=10).json()
        ws = await websockets.connect(
            info["webSocketDebuggerUrl"], max_size=128 * 1024 * 1024
        )
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
            else:
                self.events.append(msg)

    async def send(self, method, params=None, session_id=None, timeout=60):
        self.mid += 1
        msg = {"id": self.mid, "method": method, "params": params or {}}
        if session_id:
            msg["sessionId"] = session_id
        fut = asyncio.get_event_loop().create_future()
        self.waiters.append((self.mid, fut))
        await self.ws.send(json.dumps(msg))
        return await asyncio.wait_for(fut, timeout)

    async def eval_js(self, js, sid):
        r = await self.send(
            "Runtime.evaluate", {"expression": js, "returnByValue": True}, sid
        )
        res = r.get("result") or {}
        if res.get("exceptionDetails"):
            desc = (res.get("exceptionDetails", {}).get("exception", {}).get("description", "") or "")
            raise RuntimeError(f"页面 JS 执行失败: {desc[:300]}")
        return res.get("result", {}).get("value")

    async def create_page(self):
        """创建后台标签页并附加会话；模拟可见性以保证滚动加载。"""
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
        await self.ws.close()


def _port_alive(port: int) -> bool:
    try:
        requests.get(f"http://127.0.0.1:{port}/json/version", timeout=1.5)
        return True
    except Exception:
        return False


def get_debug_port() -> int:
    """探测活跃的 CDP 端口：优先常见固定端口，再回退 DevToolsActivePort。"""
    candidates: list[int] = []
    for base in (r"D:\zhipin_chrome_profile", Path.home() / "AppData/Local/Google/Chrome/User Data"):
        f = Path(base) / "DevToolsActivePort"
        if f.exists():
            try:
                first = f.read_text(encoding="utf-8").strip().splitlines()[0]
                if first.strip().isdigit():
                    candidates.append(int(first.strip()))
            except Exception:
                pass
    # 去重，常见端口优先
    ordered = [DEFAULT_PORT] + [p for p in candidates if p != DEFAULT_PORT]
    for p in ordered:
        if _port_alive(p):
            return p
    # 再扫一段常见范围
    for p in range(9222, 9240):
        if p not in ordered and _port_alive(p):
            return p
    return DEFAULT_PORT


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


async def fetch_detail(cdp, sid, job: dict) -> dict:
    """导航到职位详情页，抓取完整信息（描述/福利/招聘者/沟通链接等）。"""
    url = job.get("url", "")
    if not url:
        return job
    await cdp.send("Page.navigate", {"url": f"{BASE_URL}{url}"}, sid)
    for _ in range(40):
        await asyncio.sleep(1)
        raw = await cdp.eval_js(DETAIL_EXTRACT_JS, sid)
        try:
            d = json.loads(raw or "{}")
        except json.JSONDecodeError:
            d = {}
        if d.get("description") or d.get("title"):
            job["detail"] = d
            job["desc"] = d.get("description", "")
            if d.get("salary"):
                job["salary"] = d["salary"]
            return job
    job["desc"] = ""
    return job


async def get_job_detail(url: str, port: int) -> dict:
    """查看单个岗位的完整信息：python boss_cdp.py --job <详情页URL>"""
    async with asyncio.timeout(90):
        cdp = await CDP.connect(port)
        tid, sid = await cdp.create_page()
        await cdp.send("Page.navigate", {"url": url}, sid)
        for _ in range(40):
            await asyncio.sleep(1)
            raw = await cdp.eval_js(DETAIL_EXTRACT_JS, sid)
            try:
                d = json.loads(raw or "{}")
            except json.JSONDecodeError:
                d = {}
            if d.get("title") or d.get("description"):
                await cdp.close_page(tid)
                return d
        await cdp.close_page(tid)
        return {"error": "提取失败（可能未登录或页面结构变化）", "url": url}


async def crawl(query: str, city: str, salary: str | None, max_pages: int,
                output: str | None, port: int, with_detail: bool = False,
                detail_max: int = 10) -> list[dict]:
    async with asyncio.timeout(900):
        cdp = await CDP.connect(port)
        tid, sid = await cdp.create_page()

        params = {"query": query, "city": city, "page": 1}
        if salary:
            params["salary"] = salary
        url = f"{BASE_URL}{SEARCH_PATH}?" + "&".join(f"{k}={v}" for k, v in params.items())
        print("导航:", url)
        await cdp.send("Page.navigate", {"url": url}, sid)

        # 等待职位卡片出现（轮询 DOM）
        for _ in range(60):
            await asyncio.sleep(1)
            n = await cdp.eval_js("document.querySelectorAll('.job-card-box').length", sid)
            if n and n > 0:
                break
        else:
            # 未出现：可能是未登录/风控/页面结构变化
            body = await cdp.eval_js("(document.body ? document.body.innerText : '').slice(0, 300)", sid)
            print("页面未出现职位卡片。当前正文:", repr(body))
            await cdp.close_page(tid)
            return []

        all_jobs: list[dict] = []
        seen = set()
        prev_count = -1
        stall = 0

        for rnd in range(1, max_pages + 1):
            # 人类化滚动，触发页面自身的无限滚动加载
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
                print("  提取失败:", data.get("reason"))
                break

            jobs = data["jobs"]
            new = 0
            for j in jobs:
                key = j["url"] or j["title"]
                if key not in seen:
                    seen.add(key)
                    all_jobs.append(j)
                    new += 1
            print(f"  第 {rnd} 轮: 组件内 {len(jobs)} 条 / 累计 {len(all_jobs)} 条"
                  f" (新增 {new}, hasMore={data.get('hasMore')})")

            if not data.get("hasMore"):
                print("  hasMore=false，结束")
                break
            if len(jobs) == prev_count:
                stall += 1
                if stall >= 3:
                    print("  列表不再增长，结束")
                    break
            else:
                stall = 0
            prev_count = len(jobs)

            if rnd < max_pages:
                await asyncio.sleep(random.uniform(2, 4))

        # 可选：抓取职位描述（详情页）
        if with_detail and all_jobs:
            todo = all_jobs[:detail_max]
            print(f"\n=== 抓取详情（{len(todo)} 个）===")
            for i, job in enumerate(todo, 1):
                await fetch_detail(cdp, sid, job)
                ok = len(job.get("desc", "")) > 0
                print(f"  [{i}/{len(todo)}] {job['title'][:30]} | desc={'OK('+str(len(job.get('desc','')))+'字)' if ok else '空'}")
                if i < len(todo):
                    await asyncio.sleep(random.uniform(2, 5))

        await cdp.close_page(tid)

    if output:
        out = Path(output)
        out.write_text(json.dumps(all_jobs, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n已保存 {len(all_jobs)} 条 -> {out}")
    return all_jobs


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    p = argparse.ArgumentParser(description="BOSS直聘 CDP 爬虫（真实 Chrome，明文薪资）")
    p.add_argument("--query", default="Python", help="搜索关键词")
    p.add_argument("--city", default="100010000", help="城市代码（默认全国 100010000）")
    p.add_argument("--salary", default=None, help="薪资代码，如 404=5-10K")
    p.add_argument("--pages", type=int, default=3, help="最大滚动页数（默认 3）")
    p.add_argument("-O", "--output", default=None, help="输出 JSON 文件路径")
    p.add_argument("--port", type=int, default=None, help="CDP 端口（默认自动探测）")
    p.add_argument("--job", default=None, help="查看单个岗位完整信息（传详情页 URL）")
    p.add_argument("--detail", action="store_true", help="同时抓取职位描述（详情页）")
    p.add_argument("--detail-max", type=int, default=10, help="抓取描述的最大职位数（默认 10）")
    args = p.parse_args()

    port = args.port or get_debug_port()
    print(f"使用 CDP 端口: {port}")
    try:
        if args.job:
            d = asyncio.run(get_job_detail(args.job, port))
            print(json.dumps(d, ensure_ascii=False, indent=2))
            return 0
        jobs = asyncio.run(crawl(args.query, args.city, args.salary, args.pages, args.output, port,
                                 with_detail=args.detail, detail_max=args.detail_max))
    except Exception as e:
        print(f"失败: {type(e).__name__}: {e}")
        print("请先启动调试 Chrome（start_chrome.bat 或 --remote-debugging-port=9222），并登录 BOSS直聘。")
        return 1

    for j in jobs[:10]:
        print(f"  - {j['title']} | {j['salary']} | {j['company'] or j['boss_name']} | {j['city']} {j['district']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())





