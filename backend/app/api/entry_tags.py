from fastapi import APIRouter, Depends, Response

from app.api.dependencies import get_rating_service
from app.application.rating_service import RatingService
from app.domain.tag import EntryTagRead, EntryTagUpsert


router = APIRouter(
    prefix="/entries/{entry_id}/tags",
    tags=["entry-tags"],
)


@router.get("", response_model=list[EntryTagRead])
def list_entry_tags(
    entry_id: int,
    service: RatingService = Depends(get_rating_service),
) -> list[EntryTagRead]:
    return service.list_entry_tags(entry_id)


@router.put("/{tag_id}", response_model=EntryTagRead)
def upsert_entry_tag(
    entry_id: int,
    tag_id: int,
    payload: EntryTagUpsert,
    service: RatingService = Depends(get_rating_service),
) -> EntryTagRead:
    return service.upsert_entry_tag(entry_id, tag_id, payload)


@router.delete("/{tag_id}", status_code=204, response_model=None)
def remove_entry_tag(
    entry_id: int,
    tag_id: int,
    service: RatingService = Depends(get_rating_service),
) -> Response:
    service.remove_entry_tag(entry_id, tag_id)
    return Response(status_code=204)
