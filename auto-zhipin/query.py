import json
import asyncio
import argparse
from boss_zhipin import BossZhipin
from job_eval import spawn_workflow


if __name__ == "__main__":
    cliparser = argparse.ArgumentParser(description="查询匹配的岗位。")
    cliparser.add_argument("--resume", help="简历文件路径 (目前只支持文本文件，推荐使用Markdown)", type=str, required=True)
    cliparser.add_argument("-q", "--query", help="查询关键字", type=str, default="")
    cliparser.add_argument("--city", help="BOSS直聘城市代码 (默认: 100010000)", type=str, default="100010000")
    cliparser.add_argument("--salary", help="BOSS直聘薪资代码", type=str)
    cliparser.add_argument("-n", "--scroll_n", help="最大滚动次数 (默认: 8)", type=int, default=8)
    cliparser.add_argument("--filter_tags", help="需要过滤的岗位标签 (默认: 派遣,猎头)", type=str, default="派遣,猎头")
    cliparser.add_argument("--ratings", help="可接受的岗位评级 (默认: EXCELLENT,GOOD)", type=str, default="EXCELLENT,GOOD")
    cliparser.add_argument("--blacklist", help="公司黑名单文件路径 (每行一个公司名称)", type=str)
    cliparser.add_argument("-O", "--output", help="岗位列表JSON文件输出路径 (默认: favor_jobs.json)", type=str, default="favor_jobs.json")
    args, _ = cliparser.parse_known_args()

    async def main() -> None:
        filter_tags = set(t.strip() for t in args.filter_tags.split(","))
        ratings = set(r.strip() for r in args.ratings.split(","))
        with open(args.resume, "r") as f:
            resume = f.read()
        if args.blacklist:
            with open(args.blacklist, "r") as f:
                blacklist = set(company.strip() for company in f.readlines())
        else:
            blacklist = None
        favor_jobs = []
        zhipin = BossZhipin()
        async for job in zhipin.query_jobs(
            query = args.query,
            city = args.city,
            salary = args.salary,
            scroll_n = args.scroll_n,
            filter_tags = filter_tags,
            blacklist = blacklist
        ):
            workflow = spawn_workflow()
            result = json.loads(await workflow(resume, job.description()))
            if result["rating"] in ratings:
                await job.favor()
                favor_jobs.append(job.model_dump())
        if len(favor_jobs) > 0:
            with open(args.output, "w") as f:
                json.dump(favor_jobs, f)

    asyncio.run(main())
