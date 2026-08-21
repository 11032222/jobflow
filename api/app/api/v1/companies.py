"""公司接口。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyOut

router = APIRouter()


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="公司不存在")
    return company


@router.post("/{company_id}/research", response_model=CompanyOut)
def research_company_api(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """联网搜索并生成公司简介。"""
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="公司不存在")
    from app.services.company_research_service import research_company

    try:
        return research_company(db, company, user_id=current_user.id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"公司信息检索失败：{exc}") from exc
