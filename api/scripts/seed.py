"""JobFlow 模拟数据填充脚本。

用法：在 api/ 目录下执行  python scripts/seed.py
可重复执行：清空业务数据后重新插入（保留 users 表）。
"""
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.agent_task import AgentLog, AgentTask  # noqa: E402
from app.models.application import Application, ApplicationEvent  # noqa: E402
from app.models.company import Company  # noqa: E402
from app.models.favorite import Favorite  # noqa: E402
from app.models.interview import Interview  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.job_source import JobSource  # noqa: E402
from app.models.match_result import MatchResult  # noqa: E402
from app.models.preference import Preference  # noqa: E402
from app.models.profile import CandidateProfile, ProfileExperience, ProfileSkill  # noqa: E402
from app.models.resume import Resume  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.recommendation_service import compute_match  # noqa: E402

DEMO_PASSWORD = "123456"

COMPANIES = [
    {"name": "字节跳动", "industry": "互联网", "company_type": "民营", "scale": "10000人以上", "city": "北京"},
    {"name": "阿里巴巴", "industry": "互联网", "company_type": "民营", "scale": "10000人以上", "city": "杭州"},
    {"name": "腾讯", "industry": "互联网", "company_type": "民营", "scale": "10000人以上", "city": "深圳"},
    {"name": "美团", "industry": "互联网", "company_type": "民营", "scale": "10000人以上", "city": "北京"},
    {"name": "小米集团", "industry": "智能硬件", "company_type": "民营", "scale": "10000人以上", "city": "北京"},
    {"name": "哔哩哔哩", "industry": "互联网", "company_type": "民营", "scale": "1000-9999人", "city": "上海"},
    {"name": "拼多多", "industry": "电商", "company_type": "民营", "scale": "1000-9999人", "city": "上海"},
    {"name": "网易", "industry": "互联网", "company_type": "民营", "scale": "10000人以上", "city": "杭州"},
    {"name": "京东集团", "industry": "电商", "company_type": "民营", "scale": "10000人以上", "city": "北京"},
    {"name": "百度", "industry": "互联网", "company_type": "民营", "scale": "10000人以上", "city": "北京"},
]

# (标题, 公司index, 城市, 薪资min, 薪资max, 薪资文本, 学历, 经验, 类型, 技能tags, 职责, 要求)
JOBS = [
    ("Java后端开发工程师", 0, "北京", 20000, 40000, "2-4万·16薪", "本科", "3-5年", "全职",
     ["Java", "Spring", "MySQL", "Redis"], "负责核心业务系统后端研发", "熟悉Java、Spring Boot，有分布式经验"),
    ("Java开发工程师（搜索方向）", 0, "北京", 25000, 50000, "2.5-5万·15薪", "本科", "3-5年", "全职",
     ["Java", "Elasticsearch", "MySQL", "Kafka"], "负责搜索相关系统研发", "熟悉搜索引擎相关技术栈优先"),
    ("后端开发工程师（Java）", 1, "杭州", 20000, 40000, "2-4万·16薪", "本科", "3-5年", "全职",
     ["Java", "Spring Cloud", "MySQL", "Redis"], "参与电商核心交易链路研发", "有高并发系统经验者优先"),
    ("Java后端开发实习生", 1, "杭州", 200, 300, "200-300元/天", "本科", "经验不限", "实习",
     ["Java", "Spring", "MySQL"], "参与后端功能开发与测试", "计算机相关专业，每周实习4天以上"),
    ("Java高级开发工程师", 2, "深圳", 30000, 60000, "3-6万·14薪", "本科", "5-10年", "全职",
     ["Java", "分布式", "MySQL", "Redis", "消息队列"], "负责核心服务架构设计与研发", "有大规模分布式系统经验"),
    ("后端开发工程师（Java）", 2, "深圳", 25000, 45000, "2.5-4.5万·14薪", "本科", "3-5年", "全职",
     ["Java", "Spring", "MySQL", "Redis"], "负责游戏后端逻辑研发", "熟悉网络编程优先"),
    ("Java开发工程师", 3, "北京", 18000, 35000, "1.8-3.5万·15薪", "本科", "3-5年", "全职",
     ["Java", "Spring Boot", "MySQL", "Redis"], "负责到店业务系统研发", "熟悉微服务架构"),
    ("后端开发工程师", 3, "北京", 20000, 40000, "2-4万·16薪", "本科", "3-5年", "全职",
     ["Java", "Go", "MySQL", "Kafka"], "负责交易系统研发", "扎实的计算机基础"),
    ("Java开发工程师（供应链）", 4, "北京", 20000, 40000, "2-4万·16薪", "本科", "3-5年", "全职",
     ["Java", "Spring Cloud", "MySQL", "Redis", "RabbitMQ"], "负责供应链系统研发", "有供应链/ERP经验优先"),
    ("Java开发实习生", 4, "北京", 250, 350, "250-350元/天", "本科", "经验不限", "实习",
     ["Java", "Spring Boot", "MySQL"], "协助完成业务功能开发", "2026届及以后毕业优先"),
    ("Java后端开发工程师", 5, "上海", 20000, 40000, "2-4万·16薪", "本科", "3-5年", "全职",
     ["Java", "Spring Boot", "MySQL", "Redis", "Elasticsearch"], "负责视频平台后端研发", "熟悉高并发架构"),
    ("后端开发工程师（Java）", 5, "上海", 18000, 35000, "1.8-3.5万·15薪", "本科", "1-3年", "全职",
     ["Java", "Spring", "MySQL"], "参与社区业务后端开发", "学习能力强"),
    ("Java开发工程师", 6, "上海", 20000, 40000, "2-4万·16薪", "本科", "3-5年", "全职",
     ["Java", "Spring Cloud", "MySQL", "Redis"], "负责电商系统研发", "有大规模分布式经验优先"),
    ("后端开发工程师（Java）", 6, "上海", 15000, 30000, "1.5-3万·15薪", "本科", "1-3年", "全职",
     ["Java", "Spring Boot", "MySQL"], "负责交易链路开发", "熟悉电商业务优先"),
    ("Java后端开发工程师", 7, "杭州", 18000, 35000, "1.8-3.5万·16薪", "本科", "3-5年", "全职",
     ["Java", "Spring", "MySQL", "Redis"], "负责内容平台后端研发", "有分布式经验优先"),
    ("后端开发工程师", 7, "杭州", 20000, 40000, "2-4万·16薪", "本科", "3-5年", "全职",
     ["Java", "Python", "MySQL", "Kafka"], "负责数据平台研发", "熟悉大数据生态优先"),
    ("Java开发工程师（物流）", 8, "北京", 20000, 40000, "2-4万·15薪", "本科", "3-5年", "全职",
     ["Java", "Spring", "MySQL", "Redis"], "负责物流系统研发", "有物流系统经验优先"),
    ("Java后端开发工程师", 8, "北京", 15000, 30000, "1.5-3万·15薪", "大专", "1-3年", "全职",
     ["Java", "Spring Boot", "MySQL"], "参与商城系统后端开发", "能独立完成模块开发"),
    ("Java开发工程师（推荐）", 9, "北京", 25000, 50000, "2.5-5万·16薪", "本科", "3-5年", "全职",
     ["Java", "推荐系统", "MySQL", "Redis"], "负责推荐系统研发", "有推荐/搜索经验优先"),
    ("后端开发工程师", 9, "北京", 20000, 40000, "2-4万·16薪", "本科", "3-5年", "全职",
     ["Java", "Go", "MySQL", "Redis"], "负责 AI 平台后端研发", "熟悉大模型应用开发优先"),
    ("Python开发工程师", 0, "北京", 20000, 40000, "2-4万·16薪", "本科", "3-5年", "全职",
     ["Python", "Django", "MySQL"], "负责工具平台研发", "熟悉 Python 生态"),
    ("Python后端开发工程师", 1, "杭州", 20000, 40000, "2-4万·16薪", "本科", "3-5年", "全职",
     ["Python", "Flask", "MySQL", "Redis"], "负责数据服务研发", "有数据处理经验优先"),
    ("Python开发实习生", 2, "深圳", 250, 350, "250-350元/天", "本科", "经验不限", "实习",
     ["Python", "FastAPI", "MySQL"], "参与内部工具开发", "计算机相关专业"),
    ("前端开发工程师（Vue）", 3, "北京", 18000, 35000, "1.8-3.5万·15薪", "本科", "3-5年", "全职",
     ["Vue.js", "JavaScript", "TypeScript", "Element Plus"], "负责商家后台前端研发", "熟悉 Vue 3 生态"),
    ("前端开发工程师", 5, "上海", 18000, 35000, "1.8-3.5万·16薪", "本科", "3-5年", "全职",
     ["Vue.js", "React", "TypeScript", "Webpack"], "负责播放器相关前端研发", "熟悉视频播放技术优先"),
    ("前端开发实习生", 6, "上海", 200, 300, "200-300元/天", "本科", "经验不限", "实习",
     ["Vue.js", "JavaScript", "CSS"], "协助完成前端页面开发", "热爱前端技术"),
    ("测试开发工程师", 0, "北京", 20000, 40000, "2-4万·16薪", "本科", "3-5年", "全职",
     ["Python", "Selenium", "接口测试"], "负责自动化测试平台建设", "熟悉测试框架"),
    ("测试开发工程师", 7, "杭州", 18000, 35000, "1.8-3.5万·16薪", "本科", "3-5年", "全职",
     ["Python", "自动化测试", "MySQL"], "负责质量保障体系建设", "有性能测试经验优先"),
    ("产品经理（B端）", 0, "北京", 25000, 45000, "2.5-4.5万·15薪", "本科", "3-5年", "全职",
     ["产品设计", "Axure", "数据分析"], "负责企业服务产品规划", "有 B 端产品经验"),
    ("产品经理", 3, "北京", 20000, 40000, "2-4万·15薪", "本科", "3-5年", "全职",
     ["产品设计", "用户研究"], "负责商家产品规划", "逻辑清晰，沟通能力强"),
    ("数据分析师", 1, "杭州", 18000, 35000, "1.8-3.5万·16薪", "本科", "1-3年", "全职",
     ["SQL", "Python", "Tableau", "数据分析"], "负责业务数据分析", "熟悉统计知识"),
    ("数据分析师（实习）", 4, "北京", 250, 350, "250-350元/天", "本科", "经验不限", "实习",
     ["SQL", "Python", "Excel"], "协助完成数据报表开发", "统计学/数学专业优先"),
    ("大数据开发工程师", 8, "北京", 25000, 50000, "2.5-5万·16薪", "本科", "3-5年", "全职",
     ["Hadoop", "Spark", "Hive", "Kafka"], "负责数据仓库建设", "熟悉大数据生态"),
    ("大数据开发工程师", 2, "深圳", 25000, 45000, "2.5-4.5万·14薪", "本科", "3-5年", "全职",
     ["Spark", "Flink", "Hadoop", "Kafka"], "负责实时计算平台研发", "有实时数仓经验优先"),
    ("算法工程师（推荐）", 0, "北京", 30000, 60000, "3-6万·16薪", "硕士", "3-5年", "全职",
     ["Python", "推荐算法", "深度学习"], "负责推荐算法优化", "有顶会论文优先"),
    ("算法工程师（NLP）", 9, "北京", 30000, 60000, "3-6万·16薪", "硕士", "3-5年", "全职",
     ["Python", "NLP", "大模型", "PyTorch"], "负责大模型应用研发", "熟悉 Transformer 架构"),
    ("Golang开发工程师", 2, "深圳", 25000, 50000, "2.5-5万·14薪", "本科", "3-5年", "全职",
     ["Go", "MySQL", "Redis", "gRPC"], "负责 IM 系统研发", "熟悉高并发网络编程"),
    ("Golang开发工程师", 0, "北京", 25000, 50000, "2.5-5万·15薪", "本科", "3-5年", "全职",
     ["Go", "Kubernetes", "MySQL", "Redis"], "负责基础设施研发", "熟悉云原生技术"),
    ("全栈开发工程师", 5, "上海", 18000, 35000, "1.8-3.5万·15薪", "本科", "1-3年", "全职",
     ["Java", "Vue.js", "MySQL", "Redis"], "负责内部工具全栈开发", "前后端都能独立完成"),
    ("系统运维工程师（SRE）", 0, "北京", 20000, 40000, "2-4万·15薪", "本科", "3-5年", "全职",
     ["Linux", "Docker", "Kubernetes", "Shell"], "负责线上稳定性保障", "熟悉容器化技术"),
    ("前端架构师", 1, "杭州", 35000, 60000, "3.5-6万·16薪", "本科", "5-10年", "全职",
     ["JavaScript", "TypeScript", "架构设计"], "负责前端架构设计", "有大型前端项目经验"),
]

DEMO_PROFILE = {
    "name": "张小明",
    "title": "Java后端开发工程师",
    "phone": "13800001234",
    "email": "zhangxiaoming@example.com",
    "gender": "男",
    "city": "上海",
    "years_of_experience": 2,
    "education_level": "本科",
    "school": "上海大学",
    "major": "计算机科学与技术",
    "summary": (
        "2年Java后端开发经验，熟悉Spring Boot、MySQL、Redis等主流技术栈，"
        "参与过电商与内容平台的核心业务开发，具备良好的工程实践与团队协作能力，"
        "期望在互联网公司从事Java后端开发工作。"
    ),
    "skills": [
        {"name": "Java", "level": "advanced", "years": 2},
        {"name": "Spring Boot", "level": "advanced", "years": 2},
        {"name": "MySQL", "level": "intermediate", "years": 2},
        {"name": "Redis", "level": "intermediate", "years": 1},
        {"name": "Vue.js", "level": "intermediate", "years": 1},
        {"name": "Git", "level": "advanced", "years": 2},
        {"name": "Linux", "level": "intermediate", "years": 1},
        {"name": "Docker", "level": "intermediate", "years": 1},
    ],
    "experiences": [
        {
            "type": "education",
            "school_or_company": "上海大学",
            "degree": "本科",
            "major": "计算机科学与技术",
            "start_date": date(2019, 9, 1),
            "end_date": date(2023, 6, 30),
            "description": "主修课程：数据结构、操作系统、计算机网络、数据库原理",
        },
        {
            "type": "work",
            "school_or_company": "上海某互联网科技公司",
            "title": "Java开发工程师",
            "start_date": date(2023, 7, 1),
            "end_date": date(2025, 6, 30),
            "description": "负责订单系统与用户中心后端研发，主导库存扣减服务重构，QPS提升30%",
        },
        {
            "type": "project",
            "school_or_company": "JobFlow 求职辅助系统",
            "title": "后端开发 / 项目负责人",
            "start_date": date(2025, 7, 1),
            "end_date": None,
            "description": "基于 FastAPI + Vue3 构建简历投递闭环系统，负责数据库设计、岗位采集与匹配推荐模块",
        },
    ],
}

DEMO_PREFERENCE = {
    "target_positions": ["Java后端开发", "后端开发"],
    "cities": ["上海", "杭州"],
    "salary_min": 15000,
    "salary_max": 35000,
    "job_types": ["全职", "实习"],
    "industries": ["互联网"],
    "company_types": ["民营"],
    "keywords": ["Java"],
}


def make_resume_pdf(path: Path, profile: dict) -> None:
    """用 reportlab 生成一份中文简历 PDF。"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

    title_style = ParagraphStyle(
        "title", fontName="STSong-Light", fontSize=20, leading=26, alignment=1
    )
    head_style = ParagraphStyle(
        "head", fontName="STSong-Light", fontSize=13, leading=20, textColor=colors.HexColor("#1a56db")
    )
    body_style = ParagraphStyle(
        "body", fontName="STSong-Light", fontSize=11, leading=18
    )

    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=48, bottomMargin=48)
    story = [
        Paragraph(f"个人简历", title_style),
        Spacer(1, 18),
        Paragraph("基本信息", head_style),
        Spacer(1, 6),
    ]
    rows = [
        ("姓名", profile["name"], "求职意向", profile["title"]),
        ("电话", profile["phone"], "邮箱", profile["email"]),
        ("学历", profile["education_level"], "学校", profile["school"]),
        ("专业", profile["major"], "所在城市", profile["city"]),
        ("工作年限", f"{profile['years_of_experience']} 年", "", ""),
    ]
    data = []
    for row in rows:
        cells = []
        for pair_index in range(0, len(row), 2):
            k, v = row[pair_index], row[pair_index + 1]
            if k:
                cells.append(Paragraph(f"<b>{k}</b>", body_style))
                cells.append(Paragraph(v, body_style))
        data.append(cells)
    table = Table(data, colWidths=[90, 210, 90, 210])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 18))

    story.append(Paragraph("个人简介", head_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(profile["summary"], body_style))
    story.append(Spacer(1, 18))

    story.append(Paragraph("技能", head_style))
    story.append(Spacer(1, 6))
    skill_text = "、".join(f"{s['name']}" for s in profile["skills"])
    story.append(Paragraph(skill_text, body_style))
    story.append(Spacer(1, 18))

    story.append(Paragraph("教育 / 工作 / 项目经历", head_style))
    story.append(Spacer(1, 6))
    for exp in profile["experiences"]:
        period = f"{exp.get('start_date') or ''} ~ {exp.get('end_date') or '至今'}"
        if exp["type"] == "education":
            head = f"{exp['school_or_company']}｜{exp.get('degree')}｜{exp.get('major')}"
        elif exp["type"] == "work":
            head = f"{exp['school_or_company']}｜{exp.get('title')}"
        else:
            head = f"{exp['school_or_company']}｜{exp.get('title')}"
        story.append(Paragraph(f"<b>{head}</b>（{period}）", body_style))
        story.append(Paragraph(exp.get("description") or "", body_style))
        story.append(Spacer(1, 8))

    doc.build(story)


def create_demo_user(db) -> User:
    user = db.query(User).filter(User.username == "admin").first()
    if user:
        return user
    user = User(
        username="admin",
        password_hash=hash_password(DEMO_PASSWORD),
        email=DEMO_PROFILE["email"],
        phone=DEMO_PROFILE["phone"],
        real_name=DEMO_PROFILE["name"],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_companies(db) -> dict[str, Company]:
    mapping = {}
    for item in COMPANIES:
        company = db.query(Company).filter(Company.name == item["name"]).first()
        if company is None:
            company = Company(
                name=item["name"],
                industry=item["industry"],
                company_type=item["company_type"],
                scale=item["scale"],
                address=f"{item['city']}市",
                description=f"{item['name']}是一家{item['industry']}领域企业，",
                profile_status="NOT_ANALYZED",
            )
            db.add(company)
            db.flush()
        mapping[item["name"]] = company
    db.commit()
    return mapping


def create_jobs(db, companies: dict[str, Company]) -> list[Job]:
    jobs = []
    now = datetime.now()
    for idx, (title, comp_idx, city, salary_min, salary_max, salary_text,
              education, experience, job_type, tags, resp, req) in enumerate(JOBS):
        company = companies[COMPANIES[comp_idx]["name"]]
        job = (
            db.query(Job)
            .filter(Job.title == title, Job.company_id == company.id)
            .first()
        )
        if job is None:
            job = Job(
                title=title,
                company_id=company.id,
                city=city,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_text=salary_text,
                education=education,
                experience=experience,
                job_type=job_type,
                industry=company.industry,
                tags=json.dumps(tags, ensure_ascii=False),
                responsibilities=resp,
                requirements=req,
                publish_time=now - timedelta(days=idx % 20, hours=idx % 24),
                source="mock",
                source_job_id=f"mock-{idx}",
                source_url="",
                status="ACTIVE",
            )
            db.add(job)
            db.flush()
        jobs.append(job)
    db.commit()
    return jobs


def create_resume(db, user: User) -> Resume:
    resume = (
        db.query(Resume)
        .filter(Resume.user_id == user.id, Resume.file_name.like("%张小明%"))
        .first()
    )
    if resume:
        return resume
    upload_dir = Path(settings.UPLOAD_DIR) / str(user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = upload_dir / "张小明-后端开发-简历.pdf"
    if not pdf_path.exists():
        make_resume_pdf(pdf_path, DEMO_PROFILE)
    resume = Resume(
        user_id=user.id,
        file_name="张小明-后端开发-简历.pdf",
        file_path=str(pdf_path),
        file_type="pdf",
        file_size=pdf_path.stat().st_size,
        parse_status="SUCCESS",
        version=1,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def create_profile(db, user: User, resume: Resume) -> CandidateProfile:
    profile = (
        db.query(CandidateProfile)
        .filter(CandidateProfile.user_id == user.id, CandidateProfile.is_current.is_(True))
        .first()
    )
    if profile:
        return profile
    profile = CandidateProfile(
        user_id=user.id,
        resume_id=resume.id,
        name=DEMO_PROFILE["name"],
        title=DEMO_PROFILE["title"],
        phone=DEMO_PROFILE["phone"],
        email=DEMO_PROFILE["email"],
        gender=DEMO_PROFILE["gender"],
        city=DEMO_PROFILE["city"],
        years_of_experience=DEMO_PROFILE["years_of_experience"],
        education_level=DEMO_PROFILE["education_level"],
        school=DEMO_PROFILE["school"],
        major=DEMO_PROFILE["major"],
        summary=DEMO_PROFILE["summary"],
        source="RULE",
        status="CONFIRMED",
        is_current=True,
    )
    db.add(profile)
    db.flush()
    for exp in DEMO_PROFILE["experiences"]:
        db.add(ProfileExperience(profile_id=profile.id, **exp))
    for skill in DEMO_PROFILE["skills"]:
        db.add(ProfileSkill(profile_id=profile.id, **skill))
    db.commit()
    db.refresh(profile)
    return profile


def create_preference(db, user: User) -> Preference:
    pref = db.query(Preference).filter(Preference.user_id == user.id).first()
    if pref:
        return pref
    pref = Preference(
        user_id=user.id,
        target_positions=json.dumps(DEMO_PREFERENCE["target_positions"], ensure_ascii=False),
        cities=json.dumps(DEMO_PREFERENCE["cities"], ensure_ascii=False),
        salary_min=DEMO_PREFERENCE["salary_min"],
        salary_max=DEMO_PREFERENCE["salary_max"],
        job_types=json.dumps(DEMO_PREFERENCE["job_types"], ensure_ascii=False),
        industries=json.dumps(DEMO_PREFERENCE["industries"], ensure_ascii=False),
        company_types=json.dumps(DEMO_PREFERENCE["company_types"], ensure_ascii=False),
        keywords=json.dumps(DEMO_PREFERENCE["keywords"], ensure_ascii=False),
        is_auto_match=True,
    )
    db.add(pref)
    db.commit()
    db.refresh(pref)
    return pref


def create_match(db, user: User, profile: CandidateProfile, pref: Preference, jobs: list[Job]) -> None:
    for job in jobs:
        compute_match(db, user.id, profile, job, pref)


def create_applications(db, user: User, jobs: list[Job]) -> list[Application]:
    """创建几条不同状态的投递记录。"""
    apps = []
    status_seq = [
        ("INTERVIEW", "已进入面试环节"),
        ("TEST", "收到笔试邀请"),
        ("WAITING", "等待HR反馈"),
        ("SUBMITTED", "邮件已发送至演示收件箱"),
        ("OFFER", "收到录用意向"),
        ("REJECTED", "岗位已关闭"),
    ]
    for idx, (status, note) in enumerate(status_seq[:6]):
        job = jobs[idx]
        exists = (
            db.query(Application)
            .filter(Application.user_id == user.id, Application.job_id == job.id)
            .first()
        )
        if exists:
            apps.append(exists)
            continue
        app = Application(
            user_id=user.id,
            job_id=job.id,
            status=status,
            channel="EMAIL",
            email_to=settings.DEMO_INBOX,
            sent_at=datetime.now() - timedelta(days=idx + 1),
        )
        db.add(app)
        db.flush()
        from_status = None
        for s in ("PENDING", "SUBMITTING", "SUBMITTED", "WAITING", "TEST", "INTERVIEW", "OFFER"):
            if s == status:
                break
            from_status = s
        db.add(
            ApplicationEvent(
                application_id=app.id,
                from_status=from_status,
                to_status=status,
                operator="SYSTEM",
                comment=note,
            )
        )
        apps.append(app)
    db.commit()
    return apps


def create_interviews(db, user: User, apps: list[Application]) -> None:
    if not apps:
        return
    targets = [a for a in apps if a.status in ("INTERVIEW", "TEST", "WAITING")]
    for i, app in enumerate(targets[:3]):
        job = db.get(Job, app.job_id)
        if job is None:
            continue
        exists = (
            db.query(Interview)
            .filter(Interview.user_id == user.id, Interview.application_id == app.id)
            .first()
        )
        if exists:
            continue
        interview = Interview(
            user_id=user.id,
            application_id=app.id,
            company_id=job.company_id,
            job_id=job.id,
            interview_type="视频面试" if i % 2 == 0 else "技术面",
            round_no=1,
            scheduled_at=datetime.now() + timedelta(days=2 + i * 3, hours=10),
            status="SCHEDULED",
            meeting_url="https://meeting.example.com/jobflow-demo" if i == 0 else None,
            notes="准备项目经历与技术栈问题",
        )
        db.add(interview)
    db.commit()


def seed_all() -> None:
    print("=== JobFlow 模拟数据填充开始 ===")
    # 确保数据表存在（与 main.py startup 行为一致）
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 清空业务数据（保留 users 以保持登录状态）
        for model in (
            Interview, ApplicationEvent, Application, MatchResult, Favorite,
            JobSource, AgentLog, AgentTask, Job, Preference,
            ProfileExperience, ProfileSkill, CandidateProfile, Resume,
        ):
            db.query(model).delete()
        db.commit()

        user = create_demo_user(db)
        print(f"[1/7] 演示用户: {user.username} / {DEMO_PASSWORD}")

        companies = create_companies(db)
        print(f"[2/7] 公司: {len(companies)} 家")

        jobs = create_jobs(db, companies)
        print(f"[3/7] 岗位: {len(jobs)} 条")

        resume = create_resume(db, user)
        print(f"[4/7] 简历: {resume.file_name}")

        profile = create_profile(db, user, resume)
        print(f"[5/7] 求职画像: {profile.name}（{profile.title}）")

        pref = create_preference(db, user)
        print("[6/7] 求职偏好已设置")

        create_match(db, user, profile, pref, jobs)
        apps = create_applications(db, user, jobs)
        create_interviews(db, user, apps)
        print(f"[7/7] 匹配/投递({len(apps)}条)/面试数据完成")

        print("=== 填充完成 ===")
        print("  登录账号: admin / 123456")
        print("  投递演示收件箱: %s" % settings.DEMO_INBOX)
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()





