from datetime import date
from pydantic import BaseModel
from typing import Callable, Awaitable
from mcp_agent.core.fastagent import FastAgent
from mcp_agent.core.request_params import RequestParams
from utils import remove_json_fences


class Evaluator(BaseModel):
    name: str = "eval"
    instruction: str = """你是一位非常专业的职业导师，请根据以下标准评判岗位是否对求职者来说是一份优质工作:

1. 技能匹配度: 岗位要求的技术或经验与求职者简历中的技能是否高度匹配？
2. 工作内容与职业目标契合度: 岗位的工作职责是否符合求职者的职业发展方向？求职者是否对该职位的工作内容感兴趣，并愿意在此领域深耕？
3. 薪资福利匹配: 岗位提供的薪资是否符合求职者的预期或市场标准？是否有良好的福利待遇，如医疗、年假、员工培训等？
4. 职业成长空间: 该岗位是否提供了职业晋升的机会或职业发展的空间？是否有相关的培训资源或发展支持？
5. 公司文化与工作环境: 公司文化是否符合求职者的价值观和工作风格？求职者是否能够融入公司环境？
6. 工作与生活平衡: 岗位是否提供足够的工作与生活平衡，避免过度加班或高压环境？求职者是否可以在该岗位上保持健康的工作节奏？

请针对每项标准提供评级 (EXCELLENT, GOOD, FAIR, or POOR)。"""

    @staticmethod
    def request_params() -> RequestParams:
        return RequestParams(maxTokens=8192, temperature=0.4)

    @staticmethod
    def prompt(resume: str, job_description: str) -> str:
        today = str(date.today())
        return f"""<bio-resume>
{resume}
</bio-resume>

<job-description>
{job_description}
</job-description>

今天是{today}，请评判该岗位是否对求职者来说是一份优质工作。"""


class EvalSummary(BaseModel):
    name: str = "eval_summary"
    instruction: str = """Summarize the evaluation as a structured response with the overall rating.

Your response MUST be valid JSON matching this exact format (no other text, markdown, or explanation):

{"rating":"RATING"}

Where:

- RATING: Must be one of: "EXCELLENT", "GOOD", "FAIR", or "POOR"
- EXCELLENT: It's a perfect job
- GOOD: This job is just OK
- FAIR: This job doesn't look good
- POOR: This job is complete shit

IMPORTANT: Your response should be ONLY the JSON object without any code fences, explanations, or other text."""
    use_history: bool = False

    @staticmethod
    def request_params() -> RequestParams:
        return RequestParams(
            maxTokens = 8192,
            temperature = 0.4,
            use_history = False
        )


def spawn_workflow() -> Callable[[str, str], Awaitable[str]]:
    fast = FastAgent("job-eval", parse_cli_args=False)

    @fast.agent(**Evaluator().model_dump(), request_params=Evaluator.request_params())
    @fast.agent(**EvalSummary().model_dump(), request_params=EvalSummary.request_params())
    async def workflow(resume: str, job_description: str) -> str:
        async with fast.run() as agent:
            evaluation = await agent.eval(Evaluator.prompt(resume, job_description))
            return remove_json_fences(await agent.eval_summary(evaluation))

    return workflow


if __name__ == "__main__":
    import sys
    import asyncio
    import argparse

    cliparser = argparse.ArgumentParser(description="评判岗位是否为优质工作。")
    cliparser.add_argument("--resume", help="简历文件路径 (目前只支持文本文件，推荐使用Markdown)", type=str, required=True)
    args, _ = cliparser.parse_known_args()

    async def main() -> None:
        with open(args.resume, "r") as f:
            resume = f.read()
        job_description = sys.stdin.read()
        workflow = spawn_workflow()
        await workflow(resume, job_description)

    asyncio.run(main())
