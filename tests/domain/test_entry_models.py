import pytest
from pydantic import ValidationError

from app.domain.entry import EntryCreate, EntryType


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