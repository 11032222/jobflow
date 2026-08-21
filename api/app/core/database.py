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


def _normalize_legacy_interview_statuses() -> None:
    """把旧版面试状态统一到新状态机：PENDING→IN_PROGRESS，DONE→COMPLETED。"""
    from app.models.interview import Interview

    db = SessionLocal()
    try:
        changes = 0
        for old, new in (("PENDING", "IN_PROGRESS"), ("DONE", "COMPLETED")):
            rows = db.query(Interview).filter(Interview.status == old).all()
            for row in rows:
                row.status = new
                changes += 1
        if changes:
            db.commit()
            logger.info("已归一化 %s 条历史面试状态", changes)
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


def _migrate_interview_session_columns() -> None:
    """让 interview_questions / interview_reviews 支持独立会话：
    - 新增可空 session_id 列
    - interview_id 改为可空（会话可独立于面试日程存在）
    """
    insp = inspect(engine)
    for table_name in ("interview_questions", "interview_reviews"):
        if not insp.has_table(table_name):
            continue
        cols = {c["name"]: c for c in insp.get_columns(table_name)}
        need_session_id = "session_id" not in cols
        interview_col = cols.get("interview_id")
        need_nullable = interview_col is not None and interview_col.get("nullable") is False
        if not need_session_id and not need_nullable:
            continue

        with engine.connect() as conn:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()

        table_obj = Base.metadata.tables.get(table_name)
        if table_obj is None:
            continue

        if count == 0:
            # 空表直接按新模型重建，避免 SQLite 改列复杂
            table_obj.drop(bind=engine, checkfirst=True)
            table_obj.create(bind=engine)
            logger.info("已重建空表 %s 以适配会话模型", table_name)
            continue

        if engine.dialect.name == "sqlite":
            # 非空 SQLite：rename -> create -> copy -> drop
            backup = f"{table_name}_backup"
            with engine.begin() as conn:
                conn.execute(text(f"PRAGMA foreign_keys=OFF"))
                conn.execute(text(f"ALTER TABLE {table_name} RENAME TO {backup}"))
                table_obj.create(bind=conn)
                backup_cols = {c["name"] for c in inspect(engine).get_columns(backup)}
                new_cols = {c.name for c in table_obj.columns}
                common = [c for c in new_cols if c in backup_cols]
                col_list = ", ".join(common)
                conn.execute(text(f"INSERT INTO {table_name} ({col_list}) SELECT {col_list} FROM {backup}"))
                conn.execute(text(f"DROP TABLE {backup}"))
                conn.execute(text(f"PRAGMA foreign_keys=ON"))
            logger.info("已迁移 SQLite 表 %s 为会话模型", table_name)
        else:
            with engine.begin() as conn:
                if need_session_id:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN session_id INTEGER NULL"))
                if need_nullable:
                    conn.execute(text(f"ALTER TABLE {table_name} MODIFY COLUMN interview_id INTEGER NULL"))
            logger.info("已迁移 MySQL 表 %s 为会话模型", table_name)


def ensure_schema() -> None:
    """给已有库补齐新增列（create_all 不会 ALTER）。"""
    _ensure_job_sources_columns()
    _ensure_llm_config_columns()
    _encrypt_legacy_llm_keys()
    _normalize_legacy_interview_statuses()
    _ensure_resume_fail_reason()
    _migrate_interview_session_columns()
