"""资源关联和状态检测接口。"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.api.dependencies import get_resource_service
from app.application.errors import (
    ConflictError,
    NotFoundError,
    ResourceAccessDeniedError,
    ResourceAlreadyLinkedError,
    ResourceFileMissingError,
    ResourceLinkNotFoundError,
    ResourceNotFileError,
    ResourceNotFoundError,
    ResourceOpenFailedError,
    ResourcePathNotAbsoluteError,
    ValidationError,
)
from app.application.resource_service import ResourceService
from app.domain.entry import ResourceCreate, ResourceList, ResourceRead, ResourceRecheck


entry_resource_router = APIRouter(prefix="/entries", tags=["resources"])
resource_router = APIRouter(prefix="/resources", tags=["resources"])


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "details": details or {},
        },
    )


def _resource_error(exc: Exception, *, entry_id: int | None = None) -> JSONResponse:
    details = {"entry_id": entry_id} if entry_id is not None else {}

    if isinstance(exc, ResourceAlreadyLinkedError):
        return _error_response(409, "RESOURCE_ALREADY_LINKED", str(exc), details)
    if isinstance(exc, ResourceLinkNotFoundError):
        return _error_response(404, "RESOURCE_LINK_NOT_FOUND", str(exc), details)
    if isinstance(exc, ResourceNotFoundError):
        return _error_response(404, "RESOURCE_NOT_FOUND", str(exc), details)
    if isinstance(exc, ResourceFileMissingError):
        return _error_response(409, "RESOURCE_FILE_MISSING", str(exc), details)
    if isinstance(exc, ResourceAccessDeniedError):
        return _error_response(409, "RESOURCE_ACCESS_DENIED", str(exc), details)
    if isinstance(exc, ResourceOpenFailedError):
        return _error_response(409, "RESOURCE_OPEN_FAILED", str(exc), details)
    if isinstance(exc, ResourceNotFileError):
        return _error_response(422, "RESOURCE_NOT_FILE", str(exc), details)
    if isinstance(exc, ResourcePathNotAbsoluteError):
        return _error_response(422, "RESOURCE_PATH_NOT_ABSOLUTE", str(exc), details)
    if isinstance(exc, NotFoundError):
        return _error_response(404, "ENTRY_NOT_FOUND", str(exc), details)
    if isinstance(exc, ConflictError):
        return _error_response(409, "RESOURCE_CONFLICT", str(exc), details)
    if isinstance(exc, ValidationError):
        return _error_response(422, "RESOURCE_VALIDATION_FAILED", str(exc), details)

    raise exc


@entry_resource_router.post(
    "/{entry_id}/resources",
    response_model=ResourceRead,
    status_code=201,
)
def attach_resource(
    entry_id: int,
    payload: ResourceCreate,
    service: ResourceService = Depends(get_resource_service),
) -> ResourceRead | JSONResponse:
    try:
        return service.attach_resource(entry_id, payload)
    except (NotFoundError, ConflictError, ValidationError) as exc:
        return _resource_error(exc, entry_id=entry_id)


@entry_resource_router.get(
    "/{entry_id}/resources",
    response_model=ResourceList,
)
def list_resources(
    entry_id: int,
    service: ResourceService = Depends(get_resource_service),
) -> ResourceList | JSONResponse:
    try:
        items = service.list_resources(entry_id)
        return ResourceList(items=items, total=len(items))
    except (NotFoundError, ConflictError, ValidationError) as exc:
        return _resource_error(exc, entry_id=entry_id)


@entry_resource_router.delete(
    "/{entry_id}/resources/{resource_id}",
    status_code=204,
    response_model=None,
)
def detach_resource(
    entry_id: int,
    resource_id: int,
    service: ResourceService = Depends(get_resource_service),
) -> Response:
    try:
        service.detach_resource(entry_id, resource_id)
    except (NotFoundError, ConflictError, ValidationError) as exc:
        return _resource_error(exc, entry_id=entry_id)

    return Response(status_code=204)


@resource_router.post(
    "/{resource_id}/recheck",
    response_model=ResourceRecheck,
)
def recheck_resource(
    resource_id: int,
    service: ResourceService = Depends(get_resource_service),
) -> ResourceRecheck | JSONResponse:
    try:
        resource, changed = service.recheck_resource(resource_id)
        return ResourceRecheck(**resource.model_dump(), changed=changed)
    except (NotFoundError, ConflictError, ValidationError) as exc:
        return _resource_error(exc)
