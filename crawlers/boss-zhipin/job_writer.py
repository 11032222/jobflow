import json
from pydantic import BaseModel
from typing import Callable, Awaitable
from mcp_agent.core.fastagent import FastAgent
from mcp_agent.core.request_params import RequestParams
from utils import remove_json_fences


class Writer(BaseModel):
    name: str = "writer"
    model: str = "google.gemini-2.5-flash"
    instruction: str

    def __init__(self, resume: str, job_description: str) -> None:
        super().__init__(instruction=f"""你是一位专注于求职信写作的职业导师，你的任务是根求职者简历代入求职者的角色针对给定职位发布撰写一段用于“BOSS直聘”、“脉脉”等求职平台初次沟通的文案。

注意事项:

1. 请严格根据简历内容针对职位要求扬长避短，不要过度夸大，不要编造简历中未提及的内容；
2. 该文案用于“BOSS直聘”、“脉脉”等平台的初次沟通，请尽量简短以适应即时聊天的交流方式；
3. 如“BOSS直聘”、“脉脉”等这类求职平台均为实名注册，不需要自报姓名；
4. 请仅回复文案正文，不要添加任何描述、解释或其他内容。

<bio-resume>
{resume}
</bio-resume>

<job-description>
{job_description}
</job-description>""")

    @staticmethod
    def request_params() -> RequestParams:
        return RequestParams(maxTokens=8192, temperature=0.7)

    @staticmethod
    def prompt() -> str:
        return "请撰写初稿。"

    @staticmethod
    def refine(eval_summary: str, eval_content: str, version: int) -> str | None:
        res = json.loads(remove_json_fences(eval_summary))
        if not res["needs_improvement"]:
            return None
        return f"""<expert-feedbacks>
<rating>{res["rating"]}</rating>
<feedback>{res["feedback"]}</feedback>
<focus-areas>{",".join(res["focus_areas"])}</focus-areas>
<details>
{eval_content}
</details>
</expert-feedbacks>

请根据专家反馈对文案内容作出第{version + 1}次修改:

1. 直击反馈中的每个要点
2. 重点关注需要改进的具体领域
3. 保留上一版中的所有优点
4. 保持对求职者能力描述的准确性并与职位要求相关

提供完整的改进版文案内容，无需解释或评论。"""


class Evaluator(BaseModel):
    name: str = "eval"
    instruction: str

    def __init__(self, resume: str, job_description: str) -> None:
        super().__init__(instruction=f"""你是一位专注于求职信评审的职业导师，请根据以下标准对文案内容作出评价:

1. 清晰度：语言是否清晰、简洁且语法正确？
2. 具体性：是否包含与职位描述相关的具体细节？
3. 相关性：是否与简历内容相符，并避免了不必要的信息？
4. 真实性：是否过度夸大，编造了简历中未提及的内容？
5. 语气和风格：语气是否专业且适合当时的语境？
6. 说服力：是否有效地凸显了求职者的价值？
7. 表达方式：是否足够简短且符合“BOSS直聘”、“脉脉”等平台即时聊天的交流方式？
8. 反馈一致性：是否解决了之前迭代中的反馈？

针对每项标准：

- 提供评级 (EXCELLENT, GOOD, FAIR, or POOR)。
- 提供具体的反馈或改进建议。

<bio-resume>
{resume}
</bio-resume>

<job-description>
{job_description}
</job-description>""")

    @staticmethod
    def request_params() -> RequestParams:
        return RequestParams(maxTokens=8192, temperature=0.4)

    @staticmethod
    def prompt(letter: str, version: int) -> str:
        version_prompt = "初稿" if version == 0 else f"第{version}次修订稿"
        return f"""<content version="{version_prompt}">
{letter}
</content>

请对文案{version_prompt}作出评价并提出可行的修改建议。"""


class EvalSummary(BaseModel):
    name: str = "eval_summary"
    instruction: str = """Summarize the evaluation as a structured response with:

- Overall quality rating.
- Specific feedback and areas for improvement (in Chinese).

Your response MUST be valid JSON matching this exact format (no other text, markdown, or explanation):

{
  "rating": "RATING",
  "feedback": "DETAILED FEEDBACK",
  "needs_improvement": BOOLEAN,
  "focus_areas": ["FOCUS_AREA_1", "FOCUS_AREA_2", "FOCUS_AREA_3"]
}

Where:

- RATING: Must be one of: "EXCELLENT", "GOOD", "FAIR", or "POOR"
- EXCELLENT: No improvements needed
- GOOD: Only minor improvements possible
- FAIR: Several improvements needed
- POOR: Major improvements needed
- DETAILED FEEDBACK: Specific, actionable feedback (as a single string)
- BOOLEAN: true or false (lowercase, no quotes) indicating if further improvement is needed
- FOCUS_AREAS: Array of 1-3 specific areas to focus on (empty array if no improvement needed)

Example of valid response (DO NOT include the triple backticks in your response):

{
  "rating": "GOOD",
  "feedback": "The response is clear but could use more supporting evidence.",
  "needs_improvement": true,
  "focus_areas": ["Add more examples", "Include data points"]
}

IMPORTANT: Your response should be ONLY the JSON object without any code fences, explanations, or other text."""
    use_history: bool = False

    @staticmethod
    def request_params() -> RequestParams:
        return RequestParams(
            maxTokens = 8192,
            temperature = 0.4,
            use_history = False
        )


def spawn_workflow(resume: str, job_description: str) -> Callable[[int], Awaitable[str]]:
    fast = FastAgent("job-writer", parse_cli_args=False)

    @fast.agent(**Writer(resume, job_description).model_dump(), request_params=Writer.request_params())
    @fast.agent(**Evaluator(resume, job_description).model_dump(), request_params=Evaluator.request_params())
    @fast.agent(**EvalSummary().model_dump(), request_params=EvalSummary.request_params())
    async def workflow(n: int) -> str:
        async with fast.run() as agent:
            letter = await agent.writer(Writer.prompt())
            for i in range(n):
                evaluation = await agent.eval(Evaluator.prompt(letter, i))
                prompt = Writer.refine(await agent.eval_summary(evaluation), evaluation, i)
                if prompt is None:
                    break
                letter = await agent.writer(prompt)
        return letter

    return workflow


if __name__ == "__main__":
    import sys
    import asyncio
    import argparse

    cliparser = argparse.ArgumentParser(description="针对岗位撰写沟通文案。")
    cliparser.add_argument("--resume", help="简历文件路径 (目前只支持文本文件，推荐使用Markdown)", type=str, required=True)
    cliparser.add_argument("-O", "--output", help="输出文件路径 (默认: output.md)", type=str, default="output.md")
    args, _ = cliparser.parse_known_args()

    async def main() -> None:
        with open(args.resume, "r") as f:
            resume = f.read()
        job_description = sys.stdin.read()
        workflow = spawn_workflow(resume, job_description)
        letter = await workflow(3)
        with open(args.output, "w") as f:
            print(letter, file=f)

    asyncio.run(main())
