"""应用设置的 SQLite 仓储（键值对）。

仓储不提交事务，由应用服务控制提交时机。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AppSettingModel
from app.db.records import AppSettingRecord


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SqliteAppSettingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[AppSettingRecord]:
        statement = select(AppSettingModel).order_by(AppSettingModel.key)
        return [self._to_record(model) for model in self.session.scalars(statement)]

    def get(self, key: str) -> AppSettingRecord | None:
        model = self.session.get(AppSettingModel, key)
        return None if model is None else self._to_record(model)

    def get_value(self, key: str, default: str | None = None) -> str | None:
        record = self.get(key)
        return default if record is None else record.value

    def set(
        self,
        key: str,
        value: str,
        now: datetime | None = None,
    ) -> AppSettingRecord:
        """写入或覆盖一个设置项。"""
        timestamp = now or _now()
        model = self.session.get(AppSettingModel, key)

        if model is None:
            model = AppSettingModel(key=key, value=value, updated_at=timestamp)
            self.session.add(model)
        else:
            model.value = value
            model.updated_at = timestamp

        self.session.flush()
        self.session.refresh(model)
        return self._to_record(model)

    def delete(self, key: str) -> bool:
        model = self.session.get(AppSettingModel, key)
        if model is None:
            return False

        self.session.delete(model)
        self.session.flush()
        return True

    @staticmethod
    def _to_record(model: AppSettingModel) -> AppSettingRecord:
        return AppSettingRecord(
            key=model.key,
            value=model.value,
            updated_at=model.updated_at,
        )
