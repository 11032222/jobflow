import json
import asyncio
import argparse
from boss_zhipin import BossZhipin
from job_writer import spawn_workflow


if __name__ == "__main__":
    cliparser = argparse.ArgumentParser(description="查询匹配的职位。")
    cliparser.add_argument("--resume", help="简历文件路径 (目前只支持文本文件，推荐使用Markdown)", type=str, required=True)
    cliparser.add_argument("--jobs", help="收藏岗位列表JSON文件路径", type=str, required=True)
    args, _ = cliparser.parse_known_args()

    async def main() -> None:
        with open(args.resume, "r") as f:
            resume = f.read()
        with open(args.jobs, "r") as f:
            jobs = json.load(f)
        zhipin = BossZhipin()
        async for hr in zhipin.apply_jobs(jobs):
            workflow = spawn_workflow(resume, hr.description())
            await hr.send(await workflow(3))

    asyncio.run(main())
