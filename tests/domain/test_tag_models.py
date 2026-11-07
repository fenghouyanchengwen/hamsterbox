import pytest
from pydantic import ValidationError

from app.domain.tag import (
    EntryTagUpsert,
    TagCategoryCreate,
    TagCategoryUpdate,
    TagCreate,
)


def test_category_name_is_trimmed() -> None:
    category = TagCategoryCreate(name="  题材  ", color="#5B8FF9")

    assert category.name == "题材"


def test_category_rejects_invalid_color() -> None:
    with pytest.raises(ValidationError):
        TagCategoryCreate(name="题材", color="blue")


@pytest.mark.parametrize("name", ["", "   ", "x" * 33])
def test_category_rejects_invalid_name(name: str) -> None:
    with pytest.raises(ValidationError):
        TagCategoryCreate(name=name)


def test_category_update_allows_clearing_color() -> None:
    update = TagCategoryUpdate(color=None)

    assert update.model_dump(exclude_unset=True) == {"color": None}


def test_tag_name_is_trimmed() -> None:
    tag = TagCreate(category_id=1, name="  科幻  ")

    assert tag.name == "科幻"


@pytest.mark.parametrize("name", ["", "   ", "x" * 33])
def test_tag_rejects_invalid_name(name: str) -> None:
    with pytest.raises(ValidationError):
        TagCreate(category_id=1, name=name)


@pytest.mark.parametrize("rating", [None, 1, 10])
def test_entry_tag_accepts_valid_rating(rating: int | None) -> None:
    payload = EntryTagUpsert(rating=rating)

    assert payload.rating == rating


@pytest.mark.parametrize("rating", [0, 11, 9.5, True])
def test_entry_tag_rejects_invalid_rating(rating: object) -> None:
    with pytest.raises(ValidationError):
        EntryTagUpsert(rating=rating)
