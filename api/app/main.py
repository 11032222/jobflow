"""JobFlow API 应用入口。"""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(
    title="JobFlow API",
    description="智能求职辅助系统后端接口",
    version="0.1.0",
)

# 允许本地前端(Vite/Electron)跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "file://",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
def on_startup() -> None:
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    # 本地开发便捷：启动时自动建表（正式迁移仍走 Alembic）
    from app.core.database import Base, engine
    from app import models  # noqa: F401  确保模型已注册

    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "jobflow-api"}
