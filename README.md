# JobFlow 智能求职辅助系统

前后端分离的桌面端求职辅助系统：简历 → 画像 → 岗位发现 → 匹配推荐 → 邮箱投递 → 状态跟踪 → 面试管理。

- **前端**：Vue3 + Element Plus + Pinia + Electron
- **后端**：FastAPI + SQLAlchemy 2.0 + JWT
- **数据库**：MySQL（未配置时自动回退 SQLite 开发库）
- **投递演示**：SMTP 邮件投递（投递简历邮件发送到演示收件箱）

## 目录结构

```text
.
├── api/                 # FastAPI 后端
│   ├── app/
│   │   ├── core/        # 配置(.env)、数据库、JWT、依赖
│   │   ├── models/      # 17 张 ORM 表
│   │   ├── schemas/     # Pydantic 模型
│   │   ├── api/v1/      # REST 路由
│   │   ├── agents/      # LLM Service / Resume Agent / Matching Agent
│   │   ├── collectors/  # 平台适配器（zhaopin / mock / 预留）
│   │   ├── services/    # 邮件投递 / 状态机 / 匹配引擎 / 采集导入 / 简历解析
│   │   └── main.py      # 应用入口
│   ├── scripts/seed.py  # 模拟数据填充脚本
│   └── .env             # 环境变量（不提交）
└── web/                 # Vue3 + Electron 前端
    ├── electron/        # Electron 主进程
    └── src/
        ├── api/         # axios 封装
        ├── router/      # 页面路由
        ├── stores/      # Pinia
        └── views/       # 10 个业务页面
```

## 快速启动

### 1. 后端

```bash
cd api
pip install -r requirements.txt        # 安装依赖
cp .env.example .env                    # 首次复制环境变量，填入 MySQL 密码 / SMTP 授权码
python scripts/seed.py                  # 建表 + 填充模拟数据（演示账号 admin / 123456）
uvicorn app.main:app --port 8000        # 启动后端
```

> 若 MySQL 连不上，系统会自动回退到 `api/jobflow_dev.db`（SQLite），无需任何额外配置即可跑通演示。

### 2. 前端（浏览器模式）

```bash
cd web
npm install
npm run dev                             # http://localhost:5173
```

### 3. 桌面端（Electron）

先启动后端与 Vite dev server，再执行：

```bash
cd web
npm run dev                             # 终端 1：Vite
npm run electron:dev                    # 终端 2：Electron 窗口
```

## 演示账号

| 账号 | 密码 |
|---|---|
| admin | 123456 |

## 核心功能

- **简历管理**：上传 PDF/DOCX/TXT/图片简历；一键**解析**（Resume Agent：LLM 或规则引擎提取基本信息/技能/教育/工作/项目经历）；维护求职画像与求职偏好
- **平台岗位采集**：`岗位库 → 从平台导入岗位`，通过智联 Adapter（SSR 解析）异步采集真实岗位，自动标准化、`(source, source_job_id)` 去重、`dedup_hash` 跨源去重，任务进度可在岗位库查看
- **岗位库**：关键词/城市/学历/经验/类型多条件筛选，来源可追溯（智联真实岗位）
- **智能推荐**：基于画像与偏好的多维度匹配（技能/经历/学历/偏好），输出匹配分、推荐等级（S/A/B/C/D）与推荐理由；配置 LLM 后由 **Matching Agent** 生成可解释推荐理由与优劣势
- **投递看板**：状态机 PENDING → SUBMITTING → SUBMITTED → WAITING → TEST/INTERVIEW/OFFER/REJECTED/CLOSED，全程事件审计；邮件投递后可在收件箱验证
- **面试管理**：面试日程、轮次、状态、反馈
- **任务中心**：Agent 任务状态展示（RESUME_PARSE / JOB_SEARCH / JOB_MATCH / COMPANY_ANALYZE / JOB_APPLY）

## LLM Agent（可选增强）

在 `.env` 配置后重启后端即可启用（未配置时自动走规则引擎，功能完整可用）：

```ini
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1   # 通义千问 OpenAI 兼容
LLM_MODEL=qwen-plus
```

| Agent | 能力 | 无 Key fallback |
|---|---|---|
| Resume Agent | 简历文本 → 结构化画像（基本信息/技能/经历 JSON） | 正则规则提取（姓名/电话/邮箱/学校/技能） |
| Matching Agent | 生成可解释推荐理由、优势、不足 | 规则引擎四维评分 + 模板理由 |

## 平台采集（P2）

- Adapter 架构（`collectors/`）：`search_jobs()` / `get_company_info()` 统一接口，新增平台只需实现 Adapter 并在 `registry.py` 注册
- 智联 Adapter：解析 `sou.zhaopin.com` SSR 页面的 `__INITIAL_STATE__`，支持关键词 + 城市（北京/上海/深圳/杭州等）
- 采集任务异步执行，`job_sources` 表记录每次采集的关键词/城市/发现数/导入数/状态

## 邮件投递演示（如何证明投递功能做好了）

设置页 / `api/.env` 配置 `MAIL_MODE=smtp` 与 QQ 邮箱授权码后：

1. 在岗位详情点击 **投递** → 选择简历 → 确认
2. 系统后台生成求职邮件（岗位信息 + 求职信 + 简历 PDF 附件）并通过 SMTP 发送
3. 投递状态自动流转 `PENDING → SUBMITTING → SUBMITTED`，事件写入 `application_events`
4. 打开你的演示收件箱（`.env` 的 `DEMO_INBOX`），即可看到真实投递邮件与简历附件
5. 后续状态（笔试/面试/Offer/拒绝）在投递看板手动流转，形成完整跟踪闭环

> 安全提醒：SMTP 授权码等价于邮箱发信权限，仅写入 `.env`（已加入 `.gitignore`），切勿提交到 git。

## 配置项说明（api/.env）

| 变量 | 说明 |
|---|---|
| DB_HOST/PORT/USER/PASSWORD/NAME | MySQL 连接（密码请填正式值） |
| MAIL_MODE | `smtp`(真实邮箱) / `mailhog`(本地模拟) / `mock`(纯模拟) |
| SMTP_HOST/PORT/USER/PASSWORD | SMTP 服务器与授权码 |
| DEMO_INBOX | 所有投递邮件的收件箱 |
| LLM_API_KEY/BASE_URL/MODEL | 可选：配置后匹配/解析走 LLM，留空走规则引擎 |
