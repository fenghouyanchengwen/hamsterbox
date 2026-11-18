"""分享包 HTTP 接口。"""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.api.dependencies import get_share_export_repository, get_share_import_repository
from app.application.share_export import (
    create_share_manifest,
    encode_share_manifest,
    export_share_package,
    snapshot_share_entries,
)
from app.application.share_import import import_package, preview_import
from app.application.share_preview import MAX_ARCHIVE_BYTES, SharePreviewError
from app.db.share_export_repository import ShareExportRepository
from app.db.share_import_repository import ShareImportRepository


router = APIRouter(prefix="/share", tags=["share"])
SHARE_MEDIA_TYPE = "application/octet-stream"


class ShareSelection(BaseModel):
    entry_ids: list[Annotated[int, Field(strict=True, gt=0)]] = Field(min_length=1, max_length=200, strict=True)


@router.post("/export/preview")
def preview_export(
    selection: ShareSelection,
    request: Request,
    response: Response,
    repository: ShareExportRepository = Depends(get_share_export_repository),
) -> dict:
    entries = snapshot_share_entries(repository, selection.entry_ids)
    encode_share_manifest(create_share_manifest(entries, str(uuid4()), request.app.version))
    response.headers["Cache-Control"] = "no-store"
    return {"entries": entries}


@router.post(
    "/export",
    response_class=Response,
    responses={200: {"content": {SHARE_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}}}},
)
def export_package(
    selection: ShareSelection,
    request: Request,
    repository: ShareExportRepository = Depends(get_share_export_repository),
) -> Response:
    return Response(
        export_share_package(repository, selection.entry_ids, app_version=request.app.version),
        media_type=SHARE_MEDIA_TYPE,
        headers={
            "Content-Disposition": 'attachment; filename="hamsterbox.hbox"',
            "Cache-Control": "no-store",
        },
    )


SHARE_UPLOAD_BODY = {
    "requestBody": {
        "required": True,
        "content": {SHARE_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}},
    }
}


async def read_share_upload(request: Request) -> bytes:
    media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type != SHARE_MEDIA_TYPE:
        raise SharePreviewError("请用 application/octet-stream 上传分享包")
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > MAX_ARCHIVE_BYTES:
            raise SharePreviewError("分享包超过大小限制")
        data.extend(chunk)
    return bytes(data)


@router.post("/import/preview", openapi_extra=SHARE_UPLOAD_BODY)
async def preview_package_import(
    response: Response,
    data: bytes = Depends(read_share_upload),
    tag_category: list[str] = Query(default_factory=list),
    repository: ShareImportRepository = Depends(get_share_import_repository),
) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return await run_in_threadpool(preview_import, repository, data, tag_category)


@router.post("/import", openapi_extra=SHARE_UPLOAD_BODY)
async def commit_package_import(
    response: Response,
    preview_sha256: str = Query(pattern=r"^[0-9a-f]{64}$"),
    entry_share_id: list[UUID] = Query(default_factory=list),
    tag_category: list[str] = Query(default_factory=list),
    data: bytes = Depends(read_share_upload),
    repository: ShareImportRepository = Depends(get_share_import_repository),
) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return await run_in_threadpool(
        import_package, repository, data, preview_sha256, entry_share_id, tag_category,
    )
