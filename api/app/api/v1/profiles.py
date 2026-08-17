"""求职画像接口。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.profile import CandidateProfile, ProfileExperience, ProfileSkill
from app.models.user import User
from app.schemas.profile import ExperienceIn, ProfileIn, ProfileOut, SkillIn

router = APIRouter()


def _load_experiences(db: Session, profile_id: int) -> list[ProfileExperience]:
    return (
        db.query(ProfileExperience)
        .filter(ProfileExperience.profile_id == profile_id)
        .order_by(ProfileExperience.sort_order)
        .all()
    )


def _load_skills(db: Session, profile_id: int) -> list[ProfileSkill]:
    return (
        db.query(ProfileSkill).filter(ProfileSkill.profile_id == profile_id).all()
    )


def _to_out(profile: CandidateProfile, db: Session) -> ProfileOut:
    out = ProfileOut.model_validate(profile)
    out.experiences = _load_experiences(db, profile.id)
    out.skills = _load_skills(db, profile.id)
    return out


@router.get("", response_model=list[ProfileOut])
def list_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profiles = (
        db.query(CandidateProfile)
        .filter(CandidateProfile.user_id == current_user.id)
        .order_by(CandidateProfile.created_at.desc())
        .all()
    )
    return [_to_out(p, db) for p in profiles]


@router.get("/current", response_model=ProfileOut)
def get_current_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = (
        db.query(CandidateProfile)
        .filter(
            CandidateProfile.user_id == current_user.id,
            CandidateProfile.is_current.is_(True),
        )
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="尚未建立求职画像，请先创建或解析简历")
    return _to_out(profile, db)


@router.post("", response_model=ProfileOut)
def create_profile(
    data: ProfileIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    has_current = (
        db.query(CandidateProfile)
        .filter(
            CandidateProfile.user_id == current_user.id,
            CandidateProfile.is_current.is_(True),
        )
        .first()
        is not None
    )
    profile = CandidateProfile(user_id=current_user.id, **data.model_dump())
    profile.is_current = not has_current
    profile.source = "MANUAL"
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _to_out(profile, db)


@router.put("/{profile_id}", response_model=ProfileOut)
def update_profile(
    profile_id: int,
    data: ProfileIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.get(CandidateProfile, profile_id)
    if profile is None or profile.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="画像不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return _to_out(profile, db)


@router.get("/{profile_id}", response_model=ProfileOut)
def get_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.get(CandidateProfile, profile_id)
    if profile is None or profile.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="画像不存在")
    return _to_out(profile, db)
@router.post("/{profile_id}/set-current", response_model=ProfileOut)
def set_current_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.get(CandidateProfile, profile_id)
    if profile is None or profile.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="画像不存在")
    db.query(CandidateProfile).filter(
        CandidateProfile.user_id == current_user.id
    ).update({"is_current": False})
    profile.is_current = True
    profile.status = "CONFIRMED"
    db.commit()
    db.refresh(profile)
    return _to_out(profile, db)


@router.post("/{profile_id}/experiences", response_model=ProfileOut)
def add_experience(
    profile_id: int,
    data: ExperienceIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.get(CandidateProfile, profile_id)
    if profile is None or profile.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="画像不存在")
    db.add(ProfileExperience(profile_id=profile_id, **data.model_dump()))
    db.commit()
    return _to_out(profile, db)


@router.put("/{profile_id}/experiences/{exp_id}", response_model=ProfileOut)
def update_experience(
    profile_id: int,
    exp_id: int,
    data: ExperienceIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exp = db.get(ProfileExperience, exp_id)
    if exp is None or exp.profile_id != profile_id:
        raise HTTPException(status_code=404, detail="经历不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(exp, field, value)
    db.commit()
    return _to_out(db.get(CandidateProfile, profile_id), db)


@router.delete("/{profile_id}/experiences/{exp_id}", response_model=ProfileOut)
def delete_experience(
    profile_id: int,
    exp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exp = db.get(ProfileExperience, exp_id)
    if exp is None or exp.profile_id != profile_id:
        raise HTTPException(status_code=404, detail="经历不存在")
    db.delete(exp)
    db.commit()
    return _to_out(db.get(CandidateProfile, profile_id), db)


@router.post("/{profile_id}/skills", response_model=ProfileOut)
def add_skill(
    profile_id: int,
    data: SkillIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.get(CandidateProfile, profile_id)
    if profile is None or profile.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="画像不存在")
    db.add(ProfileSkill(profile_id=profile_id, **data.model_dump()))
    db.commit()
    return _to_out(profile, db)


@router.delete("/{profile_id}/skills/{skill_id}", response_model=ProfileOut)
def delete_skill(
    profile_id: int,
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = db.get(ProfileSkill, skill_id)
    if skill is None or skill.profile_id != profile_id:
        raise HTTPException(status_code=404, detail="技能不存在")
    db.delete(skill)
    db.commit()
    return _to_out(db.get(CandidateProfile, profile_id), db)

