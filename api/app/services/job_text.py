"""岗位文本整理：状态识别、职责/要求拆分、学历归一。"""
from __future__ import annotations

import json
import re

CLOSED_PATTERNS = (
    "停止招聘",
    "职位已关闭",
    "职位已下线",
    "已下线",
    "结束招聘",
    "该职位已失效",
    "岗位已关闭",
    "招聘已结束",
    "暂不招聘",
    "已招满",
)
OPEN_PATTERNS = ("立即投递", "立即沟通", "继续沟通", "招聘中", "热招")

EDU_LEVELS = [
    ("博士", 5),
    ("硕士", 4),
    ("研究生", 4),
    ("本科", 3),
    ("大专", 2),
    ("专科", 2),
    ("高职", 2),
    ("中专", 1),
    ("高中", 1),
    ("初中", 0),
]

_HEAD_RESP = (
    "岗位职责", "工作职责", "职位描述", "职责描述", "主要职责",
    "你需要做", "你将负责", "工作内容",
)
_HEAD_REQ = (
    "任职要求", "岗位要求", "任职资格", "工作要求", "职位要求",
    "我们需要你", "希望你具备", "任职条件",
)


def format_job_text(text: str | None) -> str:
    """把爬到的一整段描述整理成接近招聘页的换行排版。"""
    if not text:
        return ""
    text = str(text).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 同一行里的「岗位职责: xxx 任职要求:」切开
    for head in _HEAD_RESP + _HEAD_REQ:
        text = re.sub(rf"(?<!^)(?<!\n)({re.escape(head)}\s*[:：]?)", r"\n\n\1\n", text)
    # 编号条目换行：1. / 1、 / - / ·
    text = re.sub(r"(?:(?<=\n)|(?<=[:：]))\s*(?=(?:\d{1,2}[\.、．]|\- |\· ))", "\n", text)
    text = re.sub(r"\s+([1-9]\d{0,1}[\.、．]\s*)", r"\n\1", text)
    lines = [ln.strip() for ln in text.split("\n")]
    out: list[str] = []
    for ln in lines:
        if not ln:
            if out and out[-1] != "":
                out.append("")
            continue
        out.append(ln)
    return "\n".join(out).strip()


def split_job_description(text: str | None) -> tuple[str | None, str | None]:
    """拆成岗位职责 / 任职要求。"""
    formatted = format_job_text(text)
    if not formatted:
        return None, None
    pattern = "(" + "|".join(map(re.escape, _HEAD_RESP + _HEAD_REQ)) + r")\s*[:：]?"
    parts = re.split(pattern, formatted)
    resp: list[str] = []
    req: list[str] = []
    current: str | None = None
    for part in parts:
        key = part.strip()
        if not key:
            continue
        if key in _HEAD_RESP:
            current = "resp"
            continue
        if key in _HEAD_REQ:
            current = "req"
            continue
        if current == "resp":
            resp.append(key.lstrip(":：").strip())
        elif current == "req":
            req.append(key.lstrip(":：").strip())
    resp_text = "\n".join(x for x in resp if x).strip() or None
    req_text = "\n".join(x for x in req if x).strip() or None
    return resp_text, req_text


def parse_job_status(*texts: str | None) -> str:
    """从详情页文案判断岗位是否仍在招。返回 ACTIVE / CLOSED。"""
    blob = " ".join(t for t in texts if t)
    if not blob:
        return "ACTIVE"
    if any(p in blob for p in CLOSED_PATTERNS):
        if any(p in blob for p in OPEN_PATTERNS) and not any(
            p in blob for p in ("停止招聘", "职位已关闭", "已下线", "结束招聘", "已失效")
        ):
            return "ACTIVE"
        return "CLOSED"
    return "ACTIVE"


def education_rank(text: str | None) -> tuple[str, int]:
    """学历归一：(标签, 等级)。不限为 0。"""
    raw = (text or "").strip()
    if not raw or any(x in raw for x in ("不限", "无要求", "学历不限")):
        return "不限", 0
    for name, level in EDU_LEVELS:
        if name in raw:
            return name, level
    return raw[:8] or "不限", 0


def experience_years_required(text: str | None) -> int:
    """岗位最低工作年限。不限/应届返回 0。"""
    raw = (text or "").strip()
    if not raw or "不限" in raw or "应届" in raw or "在校" in raw or "无经验" in raw:
        return 0
    nums = [int(n) for n in re.findall(r"\d+", raw)]
    if not nums:
        return 0
    return nums[0]


def dumps(value) -> str | None:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return None
