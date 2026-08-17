"""Agent 任务模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    task_type: str
    status: str
    progress: int
    output_json: str | None = None
    error_message: str | None = None
    retry_count: int
    user_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
