# JobFlow 智能求职辅助系统

前后端分离的桌面端求职辅助系统：简历 → 求职画像 → 岗位发现 → 匹配推荐 → 邮件投递 → 状态跟踪 → 面试复盘 → 能力沉淀。

- **前端**：Vue3 + Element Plus + Pinia + Electron（Vite 开发端口 5174）
- **后端**：FastAPI + SQLAlchemy 2.0 + JWT（端口 8000）
- **数据库**：MySQL（未配置时自动回退 SQLite 开发库 `api/jobflow_dev.db`）
- **投递演示**：SMTP 邮件投递（投递简历邮件发送到演示收件箱）

## 当前版本 v1.1.0

- 接入 **BOSS 直聘** 采集（HTTP 接口优先，失败自动回退 CDP 调试浏览器）
- 支持 **智联招聘 + BOSS 直聘 + 模拟数据** 多平台岗位采集
- 跨平台按「公司 + 职位 + 城市」去重；同一来源按 `(source, source_job_id)` 去重
- 可按求职画像/偏好（关键词、城市、薪资区间）一键从多平台同时采集

## 目录结构

```text
.
├── api/                 # FastAPI 后端
│   ├── app/
│   │   ├── core/        # 配置(.env)、数据库、JWT
│   │   ├── models/      # ORM 表
│   │   ├── schemas/     # Pydantic 模型
│   │   ├── api/v1/      # REST 路由
│   │   ├── agents/      # LLM Service / Resume Agent / Matching Agent
│   │   ├── collectors/  # 平台适配器（zhaopin / zhipin / mock）
│   │   └── services/    # 邮件投递 / 状态机 / 匹配引擎 / 采集导入 / 简历解析
│   ├── scripts/seed.py  # 模拟数据填充脚本（演示账号 admin / 123456）
│   ├── scripts/seed_interviews.py  # 面试问题/复盘演示数据（不删除已有数据）
│   └── .env             # 环境变量（不提交）
├── web/                 # Vue3 + Electron 前端
│   ├── electron/        # Electron 主进程
│   └── src/             # 页面 / 路由 / 状态 / API 封装
├── crawlers/boss-zhipin/ # BOSS 直聘爬虫源码
└── auto-zhipin/          # BOSS 直聘运行时（.venv / chrome_profile）
```

## 快速启动

### 0. 一键脚本（推荐）

项目根目录双击即可，无需敲命令：

- `start-jobflow.bat`：启动后端 + 前端 + 桌面窗口（已在运行的服务会自动跳过）
- `stop-jobflow.bat`：一键关闭所有 JobFlow 服务与窗口

> 启动脚本只起服务，不填数据。首次使用请先跑一次 `python api/scripts/seed.py` 填充演示数据。

### 1. 后端

```bash
cd api
pip install -r requirements.txt        # 安装依赖（含 websockets）
uvicorn app.main:app --port 8000       # 启动后端
```

> 若 MySQL 连不上，系统会自动回退到 `api/jobflow_dev.db`（SQLite），无需额外配置即可跑通演示；启动时会自动补齐新增表列。

### 2. 前端（浏览器模式）

```bash
cd web
npm install
npm run dev                             # http://localhost:5174
```

### 3. 桌面端（Electron）

先启动后端与 Vite dev server，再执行：

```bash
cd web
npm run dev                             # 终端 1：Vite（5174）
npm run electron:dev                    # 终端 2：Electron 窗口（开发模式）
```

打包 Windows 安装包（生产模式加载 dist）：

```bash
cd web
npm run electron:build                  # 生成 release/ 下的安装程序
```

## 演示账号

| 账号 | 密码 |
|---|---|
| admin | 123456 |

## 演示数据

```bash
cd api
python scripts/seed.py        # 一键填充演示数据（用户/岗位/简历/投递/面试/复盘全套）
```

> 注意：`seed.py` 会先清空岗位、投递、面试等业务数据再重新填充（用户保留）。
> 如果你已经采集了自己的岗位数据不想被清掉，可以只跑 `python scripts/seed_interviews.py`，
> 它只给已有面试补充问题与复盘，不删任何数据。

## 核心功能

- **简历管理**：上传 PDF / DOCX / TXT 简历；一键**解析**（Resume Agent：LLM 或规则引擎提取基本信息、技能、教育/工作经历）；维护求职画像与求职偏好
- **多平台岗位采集**：岗位库 → 从平台导入岗位；智联 Adapter（SSR 解析）+ BOSS Adapter（HTTP / CDP）+ 模拟数据；自动标准化、去重，任务进度可在岗位库查看
- **岗位库**：关键词/城市/学历/经验/类型/平台多条件筛选，来源可追溯，收藏、详情
- **智能推荐**：基于画像与偏好的多维度匹配（技能/经历/学历/偏好），输出匹配分、推荐等级（S/A/B/C/D）与推荐理由；配置 LLM 后由 **Matching Agent** 生成可解释推荐理由与优劣势
- **投递看板**：状态机 PENDING → SUBMITTING → SUBMITTED → WAITING → TEST/INTERVIEW/OFFER/REJECTED/CLOSED，全程事件记录；邮件投递后可在演示收件箱验证
- **面试管理与复盘**：面试日程与状态机 SCHEDULED → IN_PROGRESS → COMPLETED → REVIEWED（含 CANCELLED），全程事件记录；面试详情页录入**面试问题 / 我的回答 / 自评**（已掌握 / 回答不完整 / 完全不会）；面试完成后自动触发 **Interview Agent** 复盘，输出考察方向、掌握度星级、薄弱项与需复习知识点；未配置 LLM 时自动降级规则引擎，功能不中断
- **面试知识库**：跨面试聚合个人能力画像（分类 × 掌握度星级），标记薄弱方向，并按面试时间前后期对比给出**进步 / 退步趋势**
- **任务中心**：Agent 任务状态展示（RESUME_PARSE / JOB_SEARCH / JOB_MATCH / COMPANY_ANALYZE / JOB_APPLY / INTERVIEW_REVIEW）
- **大模型配置**：设置页填写 OpenAI 兼容服务（通义千问 / 智谱 GLM / DeepSeek / OpenAI 预设），支持测试连接；未配置时自动走规则引擎

## 平台采集说明

- Adapter 架构（`collectors/`）：`search_jobs()` / `get_company_info()` 统一接口，新增平台只需实现 Adapter 并在 `registry.py` 注册
- **智联**：解析 `sou.zhaopin.com` SSR 页面的 `__INITIAL_STATE__`，支持关键词 + 城市（北京/上海/深圳/杭州等）
- **BOSS 直聘**：`zhipin.py` HTTP 公开接口优先，失败回退 `zhipin_cdp.py` CDP 采集（复用 `crawlers/boss-zhipin/boss_cdp.py` 思路）；需先点击岗位库的「启动调试 Chrome」（9222 调试端口）并在弹出窗口登录 BOSS 直聘，也可双击 `crawlers/boss-zhipin/start_chrome.bat`
- 采集任务异步执行，`job_sources` 表记录每次采集的关键词/城市/薪资/页数/发现数/导入数/状态

## 邮件投递演示

在设置页 / `api/.env` 配置 `MAIL_MODE=smtp` 与 QQ 邮箱授权码后：

1. 在岗位详情点击 **投递** → 选择简历 → 确认
2. 系统后台生成求职邮件（岗位信息 + 求职信 + 简历 PDF 附件）并通过 SMTP 发送
3. 投递状态自动流转 `PENDING → SUBMITTING → SUBMITTED`，事件写入 `application_events`
4. 打开演示收件箱（`.env` 的 `DEMO_INBOX`）即可看到真实投递邮件与简历附件
5. 后续状态（笔试/面试/Offer/拒绝）在投递看板手动流转，形成完整跟踪闭环

> 安全提醒：SMTP 授权码等同于邮箱发信权限，仅写入 `.env`（已加入 `.gitignore`），切勿提交到 git。

## 配置项说明（api/.env）

| 变量 | 说明 |
|---|---|
| DB_HOST/PORT/USER/PASSWORD/NAME | MySQL 连接（密码请填正确值） |
| MAIL_MODE | `smtp`(真实邮件) / `mailhog`(本地模拟) / `mock`(纯模拟) |
| SMTP_HOST/PORT/USER/PASSWORD | SMTP 服务器与授权码 |
| DEMO_INBOX | 所有投递邮件的收件箱 |
| LLM_API_KEY/BASE_URL/MODEL | 可选：配置后匹配/解析走 LLM，留空走规则引擎 |