from fastapi import APIRouter
from pydantic import BaseModel
from db import SessionLocal
from shared.models.system_setting import SystemSetting

router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingUpdate(BaseModel):
    value: str


@router.get("/{key}")
def get_setting(key: str):
    db = SessionLocal()
    try:
        setting = (
            db.query(SystemSetting)
            .filter(SystemSetting.key == key)
            .first()
        )

        return {
            "code": 200,
            "data": {
                "key": key,
                "value": setting.value if setting else None
            }
        }
    finally:
        db.close()


@router.put("/{key}")
def update_setting(key: str, data: SettingUpdate):
    db = SessionLocal()
    try:
        setting = (
            db.query(SystemSetting)
            .filter(SystemSetting.key == key)
            .first()
        )

        if setting:
            setting.value = data.value
        else:
            setting = SystemSetting(
                key=key,
                value=data.value
            )
            db.add(setting)

        db.commit()
        db.refresh(setting)

        return {
            "code": 200,
            "data": {
                "key": setting.key,
                "value": setting.value
            }
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()