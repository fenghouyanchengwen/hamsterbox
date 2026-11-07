from fastapi import APIRouter, Depends, Response

from app.api.dependencies import get_tag_service
from app.application.tag_service import TagService
from app.domain.tag import (
    TagCategoryCreate,
    TagCategoryRead,
    TagCategoryUpdate,
    TagCreate,
    TagRead,
    TagUpdate,
)


router = APIRouter(prefix="/tag-categories", tags=["tag-categories"])
tag_router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagCategoryRead])
def list_categories(
    service: TagService = Depends(get_tag_service),
) -> list[TagCategoryRead]:
    return service.list_categories()


@router.post("", response_model=TagCategoryRead, status_code=201)
def create_category(
    payload: TagCategoryCreate,
    service: TagService = Depends(get_tag_service),
) -> TagCategoryRead:
    return service.create_category(payload)


@router.patch("/{category_id}", response_model=TagCategoryRead)
def update_category(
    category_id: int,
    payload: TagCategoryUpdate,
    service: TagService = Depends(get_tag_service),
) -> TagCategoryRead:
    return service.update_category(category_id, payload)


@router.delete("/{category_id}", status_code=204, response_model=None)
def delete_category(
    category_id: int,
    service: TagService = Depends(get_tag_service),
) -> Response:
    service.delete_category(category_id)
    return Response(status_code=204)


@tag_router.get("", response_model=list[TagRead])
def list_tags(
    category_id: int | None = None,
    service: TagService = Depends(get_tag_service),
) -> list[TagRead]:
    return service.list_tags(category_id)


@tag_router.post("", response_model=TagRead, status_code=201)
def create_tag(
    payload: TagCreate,
    service: TagService = Depends(get_tag_service),
) -> TagRead:
    return service.create_tag(payload)


@tag_router.patch("/{tag_id}", response_model=TagRead)
def update_tag(
    tag_id: int,
    payload: TagUpdate,
    service: TagService = Depends(get_tag_service),
) -> TagRead:
    return service.update_tag(tag_id, payload)


@tag_router.delete("/{tag_id}", status_code=204, response_model=None)
def delete_tag(
    tag_id: int,
    service: TagService = Depends(get_tag_service),
) -> Response:
    service.delete_tag(tag_id)
    return Response(status_code=204)
