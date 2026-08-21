"""数据库连接与会话管理。"""
import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings, BASE_DIR

logger = logging.getLogger(__name__)

# SQLite 开发库（MySQL 不可用时自动回退）
SQLITE_PATH = BASE_DIR / "jobflow_dev.db"


def _build_engine():
    try:
        engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )
        # 主动探测连接，避免懒连接掩盖错误
        with engine.connect():
            pass
        logger.info("数据库连接成功: MySQL(%s:%s/%s)", settings.DB_HOST, settings.DB_PORT, settings.DB_NAME)
        return engine
    except OperationalError as exc:
        logger.warning(
            "MySQL 连接失败(%s)，自动回退到 SQLite 开发库(%s)。请在 .env 中配置正确的数据库密码后重启。",
            exc,
            SQLITE_PATH,
        )
        return create_engine(
            f"sqlite:///{SQLITE_PATH}",
            connect_args={"check_same_thread": False},
        )


class Base(DeclarativeBase):
    pass


engine = _build_engine()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """FastAPI 依赖：每个请求一个会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_job_sources_columns() -> None:
    """给 job_sources 补齐新增列。"""
    insp = inspect(engine)
    if not insp.has_table("job_sources"):
        return
    cols = {c["name"] for c in insp.get_columns("job_sources")}
    alters = []
    if "salary_min" not in cols:
        alters.append("ALTER TABLE job_sources ADD COLUMN salary_min INTEGER")
    if "salary_max" not in cols:
        alters.append("ALTER TABLE job_sources ADD COLUMN salary_max INTEGER")
    if "pages" not in cols:
        alters.append("ALTER TABLE job_sources ADD COLUMN pages INTEGER DEFAULT 1")
    if "error_message" not in cols:
        alters.append("ALTER TABLE job_sources ADD COLUMN error_message VARCHAR(512)")
    if not alters:
        return
    with engine.begin() as conn:
        for stmt in alters:
            conn.execute(text(stmt))
    logger.info("已补齐 job_sources 列: %s", [s.split()[-2] for s in alters])


def _ensure_llm_config_columns() -> None:
    """给 user_llm_configs 补齐多配置字段，并去掉 user_id 唯一限制。"""
    insp = inspect(engine)
    if not insp.has_table("user_llm_configs"):
        return
    cols = {c["name"] for c in insp.get_columns("user_llm_configs")}
    alters = []
    if "name" not in cols:
        alters.append("ALTER TABLE user_llm_configs ADD COLUMN name VARCHAR(64) DEFAULT '模型配置'")
    if "provider" not in cols:
        alters.append("ALTER TABLE user_llm_configs ADD COLUMN provider VARCHAR(32)")
    if "is_active" not in cols:
        alters.append("ALTER TABLE user_llm_configs ADD COLUMN is_active BOOLEAN DEFAULT 0")
    if "created_at" not in cols:
        alters.append("ALTER TABLE user_llm_configs ADD COLUMN created_at DATETIME DEFAULT '2026-01-01 00:00:00'")
    if "asr_model" not in cols:
        alters.append("ALTER TABLE user_llm_configs ADD COLUMN asr_model VARCHAR(128)")
    with engine.begin() as conn:
        for stmt in alters:
            conn.execute(text(stmt))
        if engine.dialect.name == "sqlite":
            conn.execute(text("DROP INDEX IF EXISTS ix_user_llm_configs_user_id"))
        else:
            try:
                conn.execute(text("ALTER TABLE user_llm_configs DROP INDEX ix_user_llm_configs_user_id"))
            except Exception:  # noqa: BLE001
                pass

    # 保证每个用户有且只有一个“当前使用”的配置
    from app.models.system_config import UserLLMConfig

    db = SessionLocal()
    try:
        rows = db.query(UserLLMConfig).order_by(UserLLMConfig.user_id, UserLLMConfig.id).all()
        grouped: dict[int, list] = {}
        for row in rows:
            grouped.setdefault(row.user_id, []).append(row)
        changed = False
        for configs in grouped.values():
            if not any(c.is_active for c in configs):
                configs[0].is_active = True
                changed = True
        if changed:
            db.commit()
            logger.info("已为用户补齐默认 LLM 配置 active 标记")
    finally:
        db.close()


def _ensure_interviews_columns() -> None:
    """给 interviews 补齐面试官/面试结果/面试性质列，并迁移旧枚举值。"""
    insp = inspect(engine)
    if not insp.has_table("interviews"):
        return
    cols = {c["name"] for c in insp.get_columns("interviews")}
    alters = []
    if "interviewer" not in cols:
        alters.append("ALTER TABLE interviews ADD COLUMN interviewer VARCHAR(64)")
    if "result" not in cols:
        alters.append("ALTER TABLE interviews ADD COLUMN result VARCHAR(32)")
    if "round_type" not in cols:
        alters.append("ALTER TABLE interviews ADD COLUMN round_type VARCHAR(32)")
    if alters:
        with engine.begin() as conn:
            for stmt in alters:
                conn.execute(text(stmt))
        logger.info("已补齐 interviews 列: %s", [s.split()[-2] for s in alters])

    # 旧状态值迁移到文档 8.4 的状态机（DONE/PENDING 为历史前端写入值）
    status_migrations = [
        "UPDATE interviews SET status='COMPLETED' WHERE status='DONE'",
        "UPDATE interviews SET status='IN_PROGRESS' WHERE status='PENDING'",
    ]
    # 面试方式旧中文值迁移为英文码；「技术面」「笔试」原本混入的是面试性质，拆到 round_type
    type_migrations = [
        "UPDATE interviews SET interview_type='VIDEO' WHERE interview_type IN ('视频面试', '视频')",
        "UPDATE interviews SET interview_type='PHONE' WHERE interview_type IN ('电话面试', '电话')",
        "UPDATE interviews SET interview_type='ONSITE' WHERE interview_type IN ('现场面试', '现场')",
        "UPDATE interviews SET round_type='TECHNICAL', interview_type=NULL WHERE interview_type='技术面'",
        "UPDATE interviews SET round_type='WRITTEN', interview_type=NULL WHERE interview_type='笔试'",
    ]
    with engine.begin() as conn:
        migrated = 0
        for stmt in status_migrations + type_migrations:
            migrated += conn.execute(text(stmt)).rowcount or 0
    if migrated:
        logger.info("已迁移 interviews 旧枚举值: %s 行", migrated)


def _add_columns_if_missing(table: str, columns: dict[str, str]) -> None:
    """给指定表补齐缺失列。columns: {列名: '类型 DEFAULT 值'}，DDL 需兼容 SQLite/MySQL。"""
    insp = inspect(engine)
    if not insp.has_table(table):
        return
    cols = {c["name"] for c in insp.get_columns(table)}
    missing = [name for name in columns if name not in cols]
    if not missing:
        return
    with engine.begin() as conn:
        for name in missing:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {columns[name]}"))
    logger.info("已为 %s 补齐列: %s", table, missing)


def _encrypt_legacy_llm_keys() -> None:
    """把上版本遗留的明文 API Key 一次性加密（幂等，已加密的不动）。"""
    from app.core.crypto import encrypt_secret, is_encrypted
    from app.models.system_config import UserLLMConfig

    insp = inspect(engine)
    if not insp.has_table("user_llm_configs"):
        return
    db = SessionLocal()
    try:
        rows = db.query(UserLLMConfig).filter(UserLLMConfig.api_key.isnot(None)).all()
        changed = 0
        for row in rows:
            if row.api_key and not is_encrypted(row.api_key):
                row.api_key = encrypt_secret(row.api_key)
                changed += 1
        if changed:
            db.commit()
            logger.info("已加密 %s 条历史明文 LLM API Key", changed)
    finally:
        db.close()


def _ensure_resume_fail_reason() -> None:
    """给 resumes 补齐解析失败原因列。"""
    insp = inspect(engine)
    if not insp.has_table("resumes"):
        return
    cols = {c["name"] for c in insp.get_columns("resumes")}
    if "fail_reason" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE resumes ADD COLUMN fail_reason VARCHAR(512)"))
        logger.info("已补齐 resumes.fail_reason 列")


def _migrate_self_result_to_mastery() -> None:
    """interview_questions.self_result 改名为 mastery（SQLite/MySQL 双兼容，幂等）。"""
    insp = inspect(engine)
    if not insp.has_table("interview_questions"):
        return
    cols = {c["name"] for c in insp.get_columns("interview_questions")}
    if "self_result" not in cols or "mastery" in cols:
        return
    if engine.dialect.name == "sqlite":
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE interview_questions RENAME COLUMN self_result TO mastery"))
    else:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE interview_questions "
                    "CHANGE COLUMN self_result mastery VARCHAR(16) DEFAULT 'PARTIAL' NOT NULL"
                )
            )
    logger.info("已将 interview_questions.self_result 重命名为 mastery")


def _migrate_interview_session_columns() -> None:
    """让 interview_questions / interview_reviews 支持独立会话与合并后的模型字段。"""
    _add_columns_if_missing(
        "interview_questions",
        {
            "session_id": "INTEGER",
            "category": "VARCHAR(64)",
            "mastery": "VARCHAR(16) DEFAULT 'PARTIAL'",
            "knowledge_point": "VARCHAR(512)",
            "source": "VARCHAR(16) DEFAULT 'USER'",
            "sort_order": "INTEGER DEFAULT 0",
        },
    )
    _add_columns_if_missing(
        "interview_reviews",
        {
            "session_id": "INTEGER",
            "status": "VARCHAR(16) DEFAULT 'RUNNING'",
            "source": "VARCHAR(16)",
            "model_name": "VARCHAR(64)",
            "summary": "TEXT",
            "dimensions_json": "TEXT",
            "weak_points_json": "TEXT",
            "review_points_json": "TEXT",
            "knowledge_points_json": "TEXT",
            "review_advice": "TEXT",
            "error_message": "VARCHAR(512)",
            "duration_ms": "INTEGER",
            "is_latest": "BOOLEAN DEFAULT 1",
            "agent_task_id": "INTEGER",
            "finished_at": "DATETIME",
        },
    )

    # MySQL 才需要放宽 interview_id 非空约束；SQLite 历史表已按可空建，空表由 create_all 覆盖。
    if engine.dialect.name != "sqlite":
        for table_name in ("interview_questions", "interview_reviews"):
            if not inspect(engine).has_table(table_name):
                continue
            cols = {c["name"]: c for c in inspect(engine).get_columns(table_name)}
            interview_col = cols.get("interview_id")
            if interview_col is not None and interview_col.get("nullable") is False:
                with engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE {table_name} MODIFY COLUMN interview_id INTEGER NULL")
                    )
                logger.info("已放宽 %s.interview_id 为可空", table_name)


def ensure_schema() -> None:
    """给已有库补齐新增列（create_all 不会 ALTER）。"""
    _ensure_job_sources_columns()
    _ensure_interviews_columns()
    _ensure_llm_config_columns()
    _encrypt_legacy_llm_keys()
    _ensure_resume_fail_reason()
    _migrate_self_result_to_mastery()
    _migrate_interview_session_columns()
