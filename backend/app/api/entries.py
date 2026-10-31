from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.application.entry_service import EntryService
from app.application.errors import NotFoundError
from app.domain.entry import EntryCreate, EntryRead, EntryUpdate

from app.api.dependencies import get_entry_service


router = APIRouter(
    prefix="/entries",
    tags=["entries"],
)


def not_found_response(entry_id: int) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "code": "ENTRY_NOT_FOUND",
            "message": f"条目 {entry_id} 不存在",
            "details": {
                "entry_id": entry_id,
            },
        },
    )


@router.post("", response_model=EntryRead, status_code=201)
def create_entry(
    payload: EntryCreate,
    service: EntryService = Depends(get_entry_service),
) -> EntryRead:
    return service.create_entry(payload)


@router.get("/{entry_id}", response_model=EntryRead)
def get_entry(
    entry_id: int,
    service: EntryService = Depends(get_entry_service),
) -> EntryRead | JSONResponse:
    try:
        return service.get_entry(entry_id)
    except NotFoundError:
        return not_found_response(entry_id)


@router.patch("/{entry_id}", response_model=EntryRead)
def update_entry(
    entry_id: int,
    payload: EntryUpdate,
    service: EntryService = Depends(get_entry_service),
) -> EntryRead | JSONResponse:
    try:
        return service.update_entry(entry_id, payload)
    except NotFoundError:
        return not_found_response(entry_id)


@router.delete("/{entry_id}", status_code=204, response_model=None)
def remove_entry(
    entry_id: int,
    service: EntryService = Depends(get_entry_service),
) -> Response:
    try:
        service.remove_entry(entry_id)
    except NotFoundError:
        return not_found_response(entry_id)

    return Response(status_code=204)
