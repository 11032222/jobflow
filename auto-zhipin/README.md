# auto-zhipin

通过[Playwright](https://github.com/microsoft/playwright-python)自动拉取Boss直聘的岗位信息，并结合求职者的简历进行智能筛选。然后根据岗位描述和简历生成个性化的沟通文案，并自动发起与招聘方的沟通。以便求职者更高效地与招聘方建立联系，提升求职效率。

## 安装

**1.** 拉取源码

```bash
git clone https://github.com/ufownl/auto-zhipin
```

**2.** 安装依赖项

```bash
cd auto-zhipin
uv sync
uv run playwright install
```

**3.** 参考[文档](https://fast-agent.ai/ref/config_file/)配置API\_KEY

```
# fastagent.secrets.yaml

google:
  api_key: "$YOUR_GEMINI_API_KEY"
```

## 使用

首先通过`query.py`筛选符合要求的职位:

```bash
$ uv run query.py --help
usage: query.py [-h] --resume RESUME [-q QUERY] [--city CITY] [--salary SALARY] [-n SCROLL_N] [--filter_tags FILTER_TAGS] [--ratings RATINGS] [--blacklist BLACKLIST] [-O OUTPUT]

查询匹配的岗位。

options:
  -h, --help            show this help message and exit
  --resume RESUME       简历文件路径 (目前只支持文本文件，推荐使用Markdown)
  -q, --query QUERY     查询关键字
  --city CITY           BOSS直聘城市代码 (默认: 100010000)
  --salary SALARY       BOSS直聘薪资代码
  -n, --scroll_n SCROLL_N
                        最大滚动次数 (默认: 8)
  --filter_tags FILTER_TAGS
                        需要过滤的岗位标签 (默认: 派遣,猎头)
  --ratings RATINGS     可接受的岗位评级 (默认: EXCELLENT,GOOD)
  --blacklist BLACKLIST
                        公司黑名单文件路径 (每行一个公司名称)
  -O, --output OUTPUT   岗位列表JSON文件输出路径 (默认: favor_jobs.json)
```

> [!NOTE]
> BOSS直聘城市代码及薪资代码可自行使用浏览器登录并选择相关查询条件后在地址栏通过URL参数查看。例如地区选择`全国`薪资待遇选择`5-10K`，则可在地址栏看到URL`https://www.zhipin.com/web/geek/jobs?city=100010000&salary=404`，通过URL参数`city`和`salary`可知城市代码为`100010000`薪资代码为`404`。

然后通过`apply.py`自动发起沟通:

```bash
$ uv run apply.py --help
usage: apply.py [-h] --resume RESUME --jobs JOBS

查询匹配的职位。

options:
  -h, --help       show this help message and exit
  --resume RESUME  简历文件路径 (目前只支持文本文件，推荐使用Markdown)
  --jobs JOBS      收藏岗位列表JSON文件路径
```

## 声明

本项目仅用于学习用途，尝试使用时请遵守相关法律法规及平台用户协议，否则后果自负。

## License

BSD-3-Clause license. See [LICENSE](https://github.com/ufownl/auto-zhipin?tab=BSD-3-Clause-1-ov-file)
