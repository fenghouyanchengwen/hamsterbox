"""资源 SQLite 仓储。"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ResourceModel
from app.application.ports import StoredResource
from app.domain.entry import ResourceRead


class SqliteResourceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        share_id: str,
        entry_id: int,
        path: str,
        file_name: str,
        extension: str,
        size_bytes: int,
        mtime_ns: int,
        sha256: str,
        availability: str,
        created_at: datetime,
    ) -> StoredResource:
        model = ResourceModel(
            share_id=share_id,
            entry_id=entry_id,
            path=path,
            file_name=file_name,
            extension=extension,
            size_bytes=size_bytes,
            mtime_ns=mtime_ns,
            sha256=sha256,
            availability=availability,
            created_at=created_at,
        )
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_stored(model)

    def get(self, resource_id: int) -> StoredResource | None:
        model = self.session.get(ResourceModel, resource_id)
        return None if model is None else self._to_stored(model)

    def list_by_entry(self, entry_id: int) -> list[ResourceRead]:
        statement = (
            select(ResourceModel)
            .where(ResourceModel.entry_id == entry_id)
            .order_by(ResourceModel.id)
        )
        models = self.session.scalars(statement).all()
        return [self._to_read(model) for model in models]

    def find_by_entry_path(self, entry_id: int, path: str) -> ResourceRead | None:
        statement = select(ResourceModel).where(
            ResourceModel.entry_id == entry_id,
            ResourceModel.path == path,
        )
        model = self.session.scalar(statement)
        return None if model is None else self._to_read(model)

    def update(
        self,
        resource_id: int,
        values: dict[str, object],
    ) -> StoredResource | None:
        model = self.session.get(ResourceModel, resource_id)
        if model is None:
            return None

        for field, value in values.items():
            setattr(model, field, value)

        self.session.commit()
        self.session.refresh(model)
        return self._to_stored(model)

    def delete(self, entry_id: int, resource_id: int) -> bool:
        statement = select(ResourceModel).where(
            ResourceModel.id == resource_id,
            ResourceModel.entry_id == entry_id,
        )
        model = self.session.scalar(statement)
        if model is None:
            return False

        self.session.delete(model)
        self.session.commit()
        return True

    @classmethod
    def _to_stored(cls, model: ResourceModel) -> StoredResource:
        return StoredResource(path=model.path, data=cls._to_read(model))

    @staticmethod
    def _to_read(model: ResourceModel) -> ResourceRead:
        return ResourceRead(
            id=model.id,
            share_id=model.share_id,
            entry_id=model.entry_id,
            file_name=model.file_name,
            extension=model.extension,
            size_bytes=model.size_bytes,
            mtime_ns=model.mtime_ns,
            sha256=model.sha256,
            availability=model.availability,
        )
