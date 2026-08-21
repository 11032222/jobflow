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


def ensure_schema() -> None:
    """给已有库补齐新增列（create_all 不会 ALTER）。"""
    _ensure_job_sources_columns()
    _ensure_llm_config_columns()