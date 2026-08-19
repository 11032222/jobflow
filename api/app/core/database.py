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


def ensure_schema() -> None:
    """给已有库补齐新增列（create_all 不会 ALTER）。"""
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

