"""应用配置：从 .env 读取环境变量。"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# api 目录（config.py 所在层级向上两级为 api/）
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# 项目根目录（小组项目/）
PROJECT_DIR = BASE_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # 优先读取根目录 .env，其次 api/.env（后加载的覆盖先加载的）
        env_file=(BASE_DIR / ".env", PROJECT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 数据库
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "123456"
    DB_NAME: str = "jobflow"

    # JWT
    JWT_SECRET: str = "jobflow-dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # Redis（可选增强）
    REDIS_URL: str = "redis://localhost:6379/0"

    # 邮箱投递
    MAIL_MODE: str = "smtp"  # smtp | mailhog | mock
    SMTP_HOST: str = "smtp.qq.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_FROM_NAME: str = "JobFlow求职助手"
    DEMO_INBOX: str = ""

    # LLM（可选）
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = ""

    # 服务
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000

    # 本地文件存储
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def smtp_configured(self) -> bool:
        return bool(self.SMTP_HOST and self.SMTP_USER and self.SMTP_PASSWORD)


settings = Settings()
