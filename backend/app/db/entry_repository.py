from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import EntryModel
from app.domain.entry import EntryRead, EntryType, LifecycleState


class SqliteEntryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        share_id: str,
        title: str,
        entry_type: EntryType,
        description: str | None,
        cover_path: str | None,
        created_at: datetime,
        updated_at: datetime,
        review: str | None = None,
        lifecycle_state: LifecycleState | str = LifecycleState.LIBRARY,
    ) -> EntryRead:
        state_value = (
            lifecycle_state.value
            if isinstance(lifecycle_state, LifecycleState)
            else str(lifecycle_state)
        )
        model = EntryModel(
            share_id=share_id,
            title=title,
            type=entry_type.value,
            description=description,
            review=review,
            lifecycle_state=state_value,
            cover_path=cover_path,
            created_at=created_at,
            updated_at=updated_at,
        )

        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)

        return self._to_read(model)

    def get(self, entry_id: int) -> EntryRead | None:
        model = self.session.get(EntryModel, entry_id)

        if model is None:
            return None

        return self._to_read(model)

    def get_cover_path(self, entry_id: int) -> str | None:
        model = self.session.get(EntryModel, entry_id)
        return None if model is None else model.cover_path

    def update(
        self,
        entry_id: int,
        values: dict[str, object],
    ) -> EntryRead | None:
        model = self.session.get(EntryModel, entry_id)

        if model is None:
            return None

        for field, value in values.items():
            if field == "type" and isinstance(value, EntryType):
                value = value.value
            elif field == "lifecycle_state" and isinstance(value, LifecycleState):
                value = value.value

            setattr(model, field, value)

        self.session.commit()
        self.session.refresh(model)

        return self._to_read(model)

    def delete(self, entry_id: int) -> bool:
        model = self.session.get(EntryModel, entry_id)

        if model is None:
            return False

        self.session.delete(model)
        self.session.commit()
        return True

    @staticmethod
    def _to_read(model: EntryModel) -> EntryRead:
        return EntryRead(
            id=model.id,
            share_id=model.share_id,
            title=model.title,
            type=EntryType(model.type),
            description=model.description,
            review=model.review,
            lifecycle_state=LifecycleState(model.lifecycle_state),
            has_cover=bool(model.cover_path),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )