from multiprocessing import context
import re
import json
import random
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode, quote
from typing import AsyncGenerator
from playwright.async_api import BrowserContext, Page, Locator, async_playwright, expect
from pydantic import BaseModel


base_url = "https://www.zhipin.com"
salary_mapping = {
    chr(0xE031): "0",
    chr(0xE032): "1",
    chr(0xE033): "2",
    chr(0xE034): "3",
    chr(0xE035): "4",
    chr(0xE036): "5",
    chr(0xE037): "6",
    chr(0xE038): "7",
    chr(0xE039): "8",
    chr(0xE03a): "9",
}


async def load_cookies(context: BrowserContext, cookies_path: Path) -> None:
    if cookies_path.exists():
        with open(cookies_path, "r") as f:
            data = json.load(f)
        await context.add_cookies(data["cookies"])


async def dump_cookies(context: BrowserContext, cookies_path: Path) -> None:
    cookies = await context.cookies()
    with open(cookies_path, "w") as f:
        json.dump({"cookies": cookies}, f)


async def login(context: BrowserContext, page: Page, cookies_path: Path, headless_cb: Callable[[str], None] | None = None) -> bool:
    await load_cookies(context, cookies_path)
    await page.goto(f"{base_url}/web/user/?ka=header-login", wait_until="networkidle")
    figure = page.locator(".nav-figure")
    for _ in range(300):
        if await figure.is_visible():
            await dump_cookies(context, cookies_path)
            return True
        try:
            if headless_cb:
                wx_btn = page.locator(".wx-login-btn")
                if await wx_btn.is_visible():
                    await wx_btn.click(delay=random.randint(32, 512))
                    qrcode = page.locator(".mini-qrcode")
                    await expect(qrcode).to_be_visible()
                    headless_cb(await qrcode.get_attribute("src"))
            await expect(figure).to_be_visible(timeout=1000)
        except AssertionError:
            pass
    return False


def decode_salary(salary: str) -> str:
    return "".join(salary_mapping[c] if c in salary_mapping else c for c in salary)


class Job:
    class Info(BaseModel):
        company: str
        title: str
        salary: str
        desc: str
        url: str

        def description(self) -> str:
            return f"<company>{self.company}</company>\n<title>{self.title}</title>\n<salary>{self.salary}</salary>\n<description>\n{self.desc}\n</description>"

    _info: Info
    _jd: Locator
    _favor: Locator

    def __init__(self, info: Info, jd: Locator, favor: Locator):
        self._info = info
        self._jd = jd
        self._favor = favor

    def description(self) -> str:
        return self._info.description()

    def model_dump(self) -> dict[str, str]:
        return self._info.model_dump()

    async def favor(self) -> None:
        await self._favor.click(delay=random.randint(32, 512))
        await expect(self._jd.locator(".op-btn.op-btn-like.active")).to_be_visible()
        await self._jd.page.wait_for_timeout(random.randint(1024, 2048))


class HrDialog:
    _info: Job.Info
    _dialog: Locator

    def __init__(self, info: Job.Info, dialog: Locator):
        self._info = info
        self._dialog = dialog

    def description(self) -> str:
        return self._info.description()

    async def send(self, letter: str) -> None:
        await self._dialog.locator(".input-area").fill(letter)
        send = self._dialog.locator(".send-message:not(.disable)")
        await expect(send).to_be_visible()
        await self._dialog.page.wait_for_timeout(random.randint(128, 8192))
        await send.click(delay=random.randint(32, 512))
        await expect(self._dialog.locator(".send-message.disable")).to_be_visible()


class BossZhipin:
    _cookies_path: Path

    def __init__(self, cookies_path: str = "cookies.json", headless_cb: Callable[[str], None] | None = None):
        self._cookies_path = Path(cookies_path).resolve()
        self._headless_cb = headless_cb

    async def query_jobs(self, query: str, city: str, salary: str | None = None, scroll_n: int = 8, filter_tags: set[str] | None = None, blacklist: set[str] | None = None) -> AsyncGenerator[Job, None]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless = True if self._headless_cb else False,
                args = ["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 720},
                locale="zh-CN",
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            page = await context.new_page()
            if not await login(context, page, self._cookies_path, self._headless_cb):
                return
            params = dict(query=query, city=city)
            if salary:
                params["salary"] = salary
            await page.goto(f"{base_url}/web/geek/jobs?{urlencode(params, quote_via=quote)}")
            prev_h = 0
            container = page.locator(".job-list-container")
            await expect(container).to_be_visible()
            await container.hover()
            for _ in range(scroll_n):
                bbox = await container.bounding_box()
                await page.mouse.wheel(0, bbox["height"] - prev_h)
                loading = container.locator(".loading-wait")
                try:
                    await expect(loading).to_be_visible()
                    await expect(loading).to_be_hidden()
                    if bbox["height"] > prev_h:
                        prev_h = bbox["height"]
                    else:
                        break
                except AssertionError:
                    break
            jobs = await container.locator(".job-card-box").all()
            for job in jobs:
                if filter_tags:
                    tag = job.locator(".job-tag-icon")
                    if await tag.is_visible() and await tag.get_attribute("alt") in filter_tags:
                        continue
                company = job.locator(".boss-name")
                await job.click(delay=random.randint(32, 512))
                jd = page.locator(".job-detail-box")
                favor = jd.locator(".op-btn.op-btn-like:not(.active)")
                title = jd.locator(".job-name")
                salary = jd.locator(".job-salary")
                desc = jd.locator(".desc")
                boss = jd.locator(".job-boss-info")
                await expect(desc).to_be_visible()
                await expect(boss).to_be_visible()
                active = boss.locator(".boss-active-time")
                if await active.is_visible() and re.search(r"[周月年]", await active.inner_text()):
                    continue
                if await favor.is_visible():
                    company_name = await company.inner_text()
                    if not blacklist or company_name not in blacklist:
                        yield Job(Job.Info(
                            company = company_name,
                            title = await title.inner_text(),
                            salary = decode_salary(await salary.inner_text()),
                            desc = await desc.inner_text(),
                            url = await job.locator(".job-name").get_attribute("href"),
                        ), jd, favor)

    async def apply_jobs(self, jobs: list[dict[str, str]]) -> AsyncGenerator[HrDialog, None]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless = True if self._headless_cb else False,
                args = ["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 720},
                locale="zh-CN",
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            page = await context.new_page()
            if not await login(context, page, self._cookies_path, self._headless_cb):
                return
            for job in jobs:
                job_info = Job.Info.model_validate(job)
                await page.goto(f"{base_url}{job_info.url}", wait_until="networkidle")
                primary = page.locator(".info-primary")
                await expect(primary).to_be_visible()
                apply = primary.get_by_role("link", name="立即沟通")
                if await apply.is_visible():
                    await apply.click(delay=random.randint(32, 512))
                    dialog = page.locator(".dialog-container")
                    await expect(dialog).to_be_visible()
                    yield HrDialog(job_info, dialog)
