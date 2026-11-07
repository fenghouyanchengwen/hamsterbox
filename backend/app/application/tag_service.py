from app.application.errors import (
    SystemCategoryProtectedError,
    TagCategoryNameDuplicatedError,
    TagCategoryNotEmptyError,
    TagCategoryNotFoundError,
    TagInUseError,
    TagNameDuplicatedError,
    TagNotFoundError,
)
from app.application.ports import (
    EntryTagRepository,
    TagCategoryRepository,
    TagRepository,
)
from app.domain.tag import (
    TagCategoryCreate,
    TagCategoryRead,
    TagCategoryUpdate,
    TagCreate,
    TagRead,
    TagUpdate,
)


class TagService:
    def __init__(
        self,
        *,
        category_repository: TagCategoryRepository,
        tag_repository: TagRepository,
        entry_tag_repository: EntryTagRepository,
    ) -> None:
        self.category_repository = category_repository
        self.tag_repository = tag_repository
        self.entry_tag_repository = entry_tag_repository

    def list_categories(self) -> list[TagCategoryRead]:
        return [
            TagCategoryRead.model_validate(item)
            for item in self.category_repository.list_all()
        ]

    def create_category(
        self,
        payload: TagCategoryCreate,
    ) -> TagCategoryRead:
        if self.category_repository.find_by_name(payload.name) is not None:
            raise TagCategoryNameDuplicatedError("标签分类名称已存在")

        created = self.category_repository.create(
            name=payload.name,
            color=payload.color,
            sort_order=payload.sort_order,
        )
        return TagCategoryRead.model_validate(created)

    def update_category(
        self,
        category_id: int,
        payload: TagCategoryUpdate,
    ) -> TagCategoryRead:
        current = self._require_category(category_id)
        if current.system_key is not None:
            raise SystemCategoryProtectedError("系统标签分类不可修改")

        values = payload.model_dump(exclude_unset=True)
        if "name" in values:
            duplicate = self.category_repository.find_by_name(str(values["name"]))
            if duplicate is not None and duplicate.id != category_id:
                raise TagCategoryNameDuplicatedError("标签分类名称已存在")

        updated = self.category_repository.update(category_id, values)
        if updated is None:
            raise TagCategoryNotFoundError(f"标签分类 {category_id} 不存在")
        return TagCategoryRead.model_validate(updated)

    def delete_category(self, category_id: int) -> None:
        current = self._require_category(category_id)
        if current.system_key is not None:
            raise SystemCategoryProtectedError("系统标签分类不可删除")
        if self.category_repository.count_tags(category_id) > 0:
            raise TagCategoryNotEmptyError("标签分类仍包含标签")
        if not self.category_repository.delete(category_id):
            raise TagCategoryNotFoundError(f"标签分类 {category_id} 不存在")

    def list_tags(self, category_id: int | None = None) -> list[TagRead]:
        if category_id is None:
            records = self.tag_repository.list_all()
        else:
            self._require_category(category_id)
            records = self.tag_repository.list_by_category(category_id)
        return [TagRead.model_validate(item) for item in records]

    def create_tag(self, payload: TagCreate) -> TagRead:
        self._require_category(payload.category_id)
        if self.tag_repository.find(payload.category_id, payload.name) is not None:
            raise TagNameDuplicatedError("该分类中已存在同名标签")

        created = self.tag_repository.create(
            category_id=payload.category_id,
            name=payload.name,
        )
        return TagRead.model_validate(created)

    def update_tag(self, tag_id: int, payload: TagUpdate) -> TagRead:
        current = self._require_tag(tag_id)
        values = payload.model_dump(exclude_unset=True)
        target_category_id = int(values.get("category_id", current.category_id))
        target_name = str(values.get("name", current.name))
        self._require_category(target_category_id)

        duplicate = self.tag_repository.find(target_category_id, target_name)
        if duplicate is not None and duplicate.id != tag_id:
            raise TagNameDuplicatedError("该分类中已存在同名标签")

        updated = self.tag_repository.update(tag_id, values)
        if updated is None:
            raise TagNotFoundError(f"标签 {tag_id} 不存在")
        return TagRead.model_validate(updated)

    def delete_tag(self, tag_id: int) -> None:
        self._require_tag(tag_id)
        if self.entry_tag_repository.count_by_tag(tag_id) > 0:
            raise TagInUseError("标签仍被条目使用")
        if not self.tag_repository.delete(tag_id):
            raise TagNotFoundError(f"标签 {tag_id} 不存在")

    def _require_category(self, category_id: int):
        category = self.category_repository.get(category_id)
        if category is None:
            raise TagCategoryNotFoundError(f"标签分类 {category_id} 不存在")
        return category

    def _require_tag(self, tag_id: int):
        tag = self.tag_repository.get(tag_id)
        if tag is None:
            raise TagNotFoundError(f"标签 {tag_id} 不存在")
        return tag
