"""求职偏好接口。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.preference import Preference
from app.models.user import User
from app.schemas.preference import PreferenceIn, PreferenceOut

router = APIRouter()


def _serialize(pref: Preference) -> PreferenceOut:
    import json

    out = PreferenceOut.model_validate(pref)
    for field in ("target_positions", "cities", "job_types", "industries", "company_types", "keywords"):
        raw = getattr(pref, field)
        try:
            setattr(out, field, json.loads(raw or "[]"))
        except (json.JSONDecodeError, TypeError):
            setattr(out, field, [])
    return out


@router.get("", response_model=PreferenceOut)
def get_preference(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pref = (
        db.query(Preference)
        .filter(Preference.user_id == current_user.id)
        .first()
    )
    if pref is None:
        raise HTTPException(status_code=404, detail="尚未设置求职偏好")
    return _serialize(pref)


@router.put("", response_model=PreferenceOut)
def upsert_preference(
    data: PreferenceIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import json

    pref = db.query(Preference).filter(Preference.user_id == current_user.id).first()
    if pref is None:
        pref = Preference(user_id=current_user.id)
        db.add(pref)
    pref.target_positions = json.dumps(data.target_positions, ensure_ascii=False)
    pref.cities = json.dumps(data.cities, ensure_ascii=False)
    pref.salary_min = data.salary_min
    pref.salary_max = data.salary_max
    pref.job_types = json.dumps(data.job_types, ensure_ascii=False)
    pref.industries = json.dumps(data.industries, ensure_ascii=False)
    pref.company_types = json.dumps(data.company_types, ensure_ascii=False)
    pref.keywords = json.dumps(data.keywords, ensure_ascii=False)
    pref.is_auto_match = data.is_auto_match
    db.commit()
    db.refresh(pref)
    return _serialize(pref)
