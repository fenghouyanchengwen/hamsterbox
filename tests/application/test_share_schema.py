"""分享包格式示例及边界校验；语义引用关系需另行校验。"""

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker


DOCS = Path(__file__).resolve().parents[2] / "docs"


@pytest.fixture
def validator():
    schema = json.loads((DOCS / "share-package-v1.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


@pytest.fixture
def manifest():
    return json.loads((DOCS / "examples/share-package-v1/single-entry.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["single-entry.json", "multi-entry.json"])
def test_examples_match_schema(validator, name):
    sample = json.loads((DOCS / "examples/share-package-v1" / name).read_text(encoding="utf-8"))
    validator.validate(sample)


@pytest.mark.parametrize("rating,valid", [(None, True), (1, True), (10, True),
                                          (0, False), (11, False), (9.5, False), (True, False)])
def test_rating_boundaries(validator, manifest, rating, valid):
    manifest["entries"][0]["entry_tags"][0]["rating"] = rating
    assert validator.is_valid(manifest) is valid


@pytest.mark.parametrize("change", ["type", "review_mode", "tag_color", "tag_id", "tag_review"])
def test_rejects_conflicts_with_frozen_contract(validator, manifest, change):
    entry = deepcopy(manifest["entries"][0])
    if change == "type":
        entry["type"] = "游戏"
    elif change == "review_mode":
        entry["share_review"] = "原评价模式不允许分享评价"
    elif change == "tag_color":
        entry["tags"][0]["color"] = "#123456"
    elif change == "tag_id":
        entry["tags"][0]["share_id"] = entry["tags"][0]["tag_ref"]
    else:
        entry["entry_tags"][0]["review"] = "标签不能带评价"
    manifest["entries"][0] = entry
    assert not validator.is_valid(manifest)
