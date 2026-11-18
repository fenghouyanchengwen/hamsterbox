"""分享包 HTTP 接口。"""

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from app.api.dependencies import get_share_export_repository
from app.application.share_export import (
    create_share_manifest,
    encode_share_manifest,
    export_share_package,
    snapshot_share_entries,
)
from app.db.share_export_repository import ShareExportRepository


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
