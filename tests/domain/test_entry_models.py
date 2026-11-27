from datetime import datetime

import pytest
from pydantic import ValidationError

from app.domain.entry import (
    EntryCreate,
    EntryRead,
    EntryType,
    EntryUpdate,
    LifecycleState,
    ResourceDeletePreviewRequest,
    ResourceDeleteRequest,
)


def test_entry_title_is_trimmed() -> None:
    entry = EntryCreate(title="  示例游戏  ", type=EntryType.GAME)

    assert entry.title == "示例游戏"


def test_empty_title_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EntryCreate(title="   ", type=EntryType.GAME)


def test_invalid_entry_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EntryCreate(title="示例", type="software")


def test_entry_type_uses_stable_english_value() -> None:
    entry = EntryCreate(title="示例", type="game")

    assert entry.type == EntryType.GAME
    assert entry.type.value == "game"


def test_entry_review_length_boundary() -> None:
    valid = EntryCreate(title="示例", type=EntryType.BOOK, review="评" * 10_000)
    assert len(valid.review or "") == 10_000

    with pytest.raises(ValidationError):
        EntryCreate(title="示例", type=EntryType.BOOK, review="评" * 10_001)


def test_entry_update_rejects_empty_payload_and_null_required_fields() -> None:
    with pytest.raises(ValidationError):
        EntryUpdate()

    with pytest.raises(ValidationError):
        EntryUpdate.model_validate({"title": None})

    with pytest.raises(ValidationError):
        EntryUpdate.model_validate({"type": None})

    cleared_review = EntryUpdate.model_validate({"review": None})
    assert cleared_review.review is None
    assert cleared_review.model_fields_set == {"review"}


def test_entry_read_normalizes_naive_utc_and_hides_cover_path() -> None:
    naive = datetime(2026, 11, 27, 9, 0, 0)
    read = EntryRead(
        id=1,
        share_id="share-1",
        title="示例",
        type=EntryType.GAME,
        description=None,
        review="很好玩",
        lifecycle_state=LifecycleState.LIBRARY,
        has_cover=True,
        created_at=naive,
        updated_at=naive,
    )

    dumped = read.model_dump(mode="json")
    assert "cover_path" not in dumped
    assert dumped["has_cover"] is True
    assert dumped["review"] == "很好玩"
    assert dumped["lifecycle_state"] == "library"
    assert dumped["created_at"].endswith("Z")
    assert dumped["updated_at"].endswith("Z")


@pytest.mark.parametrize("bad_ids", [[], [0], [-1], [True]])
def test_resource_delete_models_reject_invalid_ids(bad_ids: list[object]) -> None:
    with pytest.raises(ValidationError):
        ResourceDeletePreviewRequest.model_validate({"resource_ids": bad_ids})

    with pytest.raises(ValidationError):
        ResourceDeleteRequest.model_validate({"resource_ids": bad_ids, "confirmed": True})


def test_resource_delete_models_deduplicate_ids() -> None:
    req = ResourceDeleteRequest.model_validate(
        {"resource_ids": [3, 1, 3, 2], "confirmed": True}
    )
    assert req.resource_ids == [3, 1, 2]