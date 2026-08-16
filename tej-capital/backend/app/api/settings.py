from datetime import date

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.domain.settings import Settings as SettingsModel
from app.schemas.settings import SettingsRead, SettingsUpdate

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
