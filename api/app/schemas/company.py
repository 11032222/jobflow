"""公司模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    logo_url: str | None = None
    industry: str | None = None
    company_type: str | None = None
    scale: str | None = None
    address: str | None = None
    website: str | None = None
    description: str | None = None
    risk_level: str
    risk_reasons: str | None = None
    profile_status: str
    profile_updated_at: datetime | None = None
