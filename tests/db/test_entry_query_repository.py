"""条目检索仓储测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.db.entry_query_repository import SqliteEntryQueryRepository
from app.db.models import EntryModel, EntryTagModel, TagCategoryModel, TagModel

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def library(session: Session) -> dict[str, object]:
    category = TagCategoryModel(
        name="类型",
        created_at=NOW,
        updated_at=NOW,
    )
    session.add(category)
    session.flush()

    action = TagModel(
        category_id=category.id,
        name="动作",
        normalized_name="动作",
        created_at=NOW,
        updated_at=NOW,
    )
    story = TagModel(
        category_id=category.id,
        name="剧情",
        normalized_name="剧情",
        created_at=NOW,
        updated_at=NOW,
    )
    session.add_all([action, story])
    session.flush()

    def add_entry(title, *, entry_type="game", description=None, minutes=0, state="library"):
        entry = EntryModel(
            share_id=f"share-{title}",
            title=title,
            type=entry_type,
            description=description,
            lifecycle_state=state,
            created_at=NOW + timedelta(minutes=minutes),
            updated_at=NOW + timedelta(minutes=minutes),
        )
        session.add(entry)
        session.flush()
        return entry

    zelda = add_entry("塞尔达传说", description="开放世界冒险", minutes=3)
    hades = add_entry("Hades", description="动作 roguelike", minutes=1)
    dune = add_entry("Dune 小说", entry_type="book", minutes=2)
    add_entry("临时条目", entry_type="other", state="temporary", minutes=4)

    session.add_all(
        [
            EntryTagModel(entry_id=zelda.id, tag_id=action.id, rating=9, created_at=NOW, updated_at=NOW),
            EntryTagModel(entry_id=zelda.id, tag_id=story.id, rating=4, created_at=NOW, updated_at=NOW),
            EntryTagModel(entry_id=hades.id, tag_id=action.id, rating=5, created_at=NOW, updated_at=NOW),
            EntryTagModel(entry_id=dune.id, tag_id=story.id, rating=None, created_at=NOW, updated_at=NOW),
        ]
    )
    session.commit()

    return {
        "zelda": zelda.id,
        "hades": hades.id,
        "dune": dune.id,
        "action": action.id,
        "story": story.id,
    }


def search(repository: SqliteEntryQueryRepository, **overrides) -> list:
    params = {
        "keyword": None,
        "types": (),
        "tag_ids": (),
        "match_all_tags": True,
        "rating_min": None,
        "rating_max": None,
        "sort": "updated_desc",
        "limit": 50,
        "offset": 0,
    }
    params.update(overrides)
    return repository.search(**params)


def titles(rows) -> list[str]:
    return [row.title for row in rows]


def test_keyword_matches_title_and_description(session: Session, library) -> None:
    repository = SqliteEntryQueryRepository(session)

    assert titles(search(repository, keyword="塞尔")) == ["塞尔达传说"]
    assert titles(search(repository, keyword="roguelike")) == ["Hades"]
    assert search(repository, keyword="不存在的关键词") == []


def test_keyword_escapes_like_wildcards(session: Session, library) -> None:
    repository = SqliteEntryQueryRepository(session)

    assert search(repository, keyword="%") == []
    assert search(repository, keyword="_") == []


def test_single_tag_and_multi_tag_modes(session: Session, library) -> None:
    repository = SqliteEntryQueryRepository(session)

    by_action = search(repository, tag_ids=(library["action"],))
    assert set(titles(by_action)) == {"塞尔达传说", "Hades"}

    both = search(repository, tag_ids=(library["action"], library["story"]))
    assert titles(both) == ["塞尔达传说"]

    either = search(
        repository,
        tag_ids=(library["action"], library["story"]),
        match_all_tags=False,
    )
    assert set(titles(either)) == {"塞尔达传说", "Hades", "Dune 小说"}


def test_rating_range_uses_any_scored_tag(session: Session, library) -> None:
    repository = SqliteEntryQueryRepository(session)

    assert titles(search(repository, rating_min=8)) == ["塞尔达传说"]
    assert set(titles(search(repository, rating_max=4))) == {"塞尔达传说"}
    assert titles(search(repository, rating_min=6, rating_max=10)) == ["塞尔达传说"]


def test_type_filter_and_temporary_entries_hidden(session: Session, library) -> None:
    repository = SqliteEntryQueryRepository(session)

    assert titles(search(repository, types=("book",))) == ["Dune 小说"]
    assert "临时条目" not in titles(search(repository))


def test_sort_orders(session: Session, library) -> None:
    repository = SqliteEntryQueryRepository(session)

    assert titles(search(repository, sort="updated_desc")) == [
        "塞尔达传说",
        "Dune 小说",
        "Hades",
    ]
    assert titles(search(repository, sort="title_asc")) == [
        "Dune 小说",
        "Hades",
        "塞尔达传说",
    ]
    assert titles(search(repository, sort="rating_desc")) == [
        "塞尔达传说",
        "Hades",
        "Dune 小说",
    ]


def test_pagination_is_stable_and_does_not_repeat(session: Session, library) -> None:
    repository = SqliteEntryQueryRepository(session)

    first = search(repository, limit=2, offset=0)
    second = search(repository, limit=2, offset=2)

    assert len(first) == 2
    assert len(second) == 1
    assert set(titles(first)) & set(titles(second)) == set()
    assert set(titles(first)) | set(titles(second)) == {"塞尔达传说", "Dune 小说", "Hades"}


def test_offset_beyond_last_page_returns_empty(session: Session, library) -> None:
    repository = SqliteEntryQueryRepository(session)

    assert search(repository, limit=10, offset=100) == []
    assert repository.count(
        keyword=None,
        types=(),
        tag_ids=(),
        match_all_tags=True,
        rating_min=None,
        rating_max=None,
    ) == 3


def test_tag_ids_are_returned_with_rows(session: Session, library) -> None:
    repository = SqliteEntryQueryRepository(session)

    rows = {row.title: row for row in search(repository)}

    assert set(rows["塞尔达传说"].tag_ids) == {library["action"], library["story"]}
    assert rows["Dune 小说"].tag_ids == (library["story"],)
