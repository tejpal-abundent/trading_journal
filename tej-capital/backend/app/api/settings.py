import uuid
from datetime import date

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import SessionDep
from app.domain.settings import Settings as SettingsModel, Target
from app.schemas.settings import SettingsRead, SettingsUpdate, TargetCreate, TargetRead

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def _get_or_create(db: SessionDep) -> SettingsModel:
    row = await db.get(SettingsModel, 1)
    if not row:
        row = SettingsModel(id=1, record_start_date=date.today())
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


@router.get("", response_model=SettingsRead)
async def read_settings(db: SessionDep):
    return SettingsRead.model_validate(await _get_or_create(db))


@router.patch("", response_model=SettingsRead)
async def update_settings(payload: SettingsUpdate, db: SessionDep):
    row = await _get_or_create(db)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return SettingsRead.model_validate(row)


@router.get("/targets", response_model=list[TargetRead])
async def list_targets(db: SessionDep):
    rows = (await db.execute(select(Target).order_by(Target.metric_name))).scalars().all()
    return [TargetRead.model_validate(r) for r in rows]


@router.post("/targets", response_model=TargetRead, status_code=200)
async def upsert_target(payload: TargetCreate, db: SessionDep):
    """Upsert by metric_name (unique) — one call handles both create and edit,
    matching the Settings page's single 'save target' action."""
    row = (await db.execute(
        select(Target).where(Target.metric_name == payload.metric_name)
    )).scalar_one_or_none()
    if row is None:
        row = Target(id=uuid.uuid4(), metric_name=payload.metric_name,
                      target_value=payload.target_value, unit=payload.unit)
        db.add(row)
    else:
        row.target_value = payload.target_value
        row.unit = payload.unit
    await db.commit()
    await db.refresh(row)
    return TargetRead.model_validate(row)
