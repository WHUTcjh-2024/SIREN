import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from backend.core.config import get_settings
from backend.services.analysis import DiffractionAnalysisService

router = APIRouter(tags=["analysis"])
ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


async def _save_upload(upload: UploadFile) -> tuple[Path, Path]:
    settings = get_settings()
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="不支持的图像格式")
    directory = Path(tempfile.mkdtemp(prefix="siren-"))
    target = directory / f"input{suffix}"
    size = 0
    with target.open("wb") as stream:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_bytes:
                shutil.rmtree(directory, ignore_errors=True)
                raise HTTPException(status_code=413, detail="图像超过上传大小限制")
            stream.write(chunk)
    return target, directory


@router.post("/laser-diffraction")
async def analyse(images: list[UploadFile] = File(...)) -> dict:
    if not images:
        raise HTTPException(status_code=400, detail="请先上传图像")
    path, directory = await _save_upload(images[0])
    try:
        result = await run_in_threadpool(DiffractionAnalysisService(get_settings()).analyse, path)
        return {"success": True, "data": result}
    finally:
        shutil.rmtree(directory, ignore_errors=True)


@router.post("/laser-diffraction-stream")
async def analyse_stream(images: list[UploadFile] = File(...)) -> StreamingResponse:
    if not images:
        raise HTTPException(status_code=400, detail="请先上传图像")
    path, directory = await _save_upload(images[0])
    service = DiffractionAnalysisService(get_settings())

    def generate():
        try:
            yield from service.stream(path)
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    return StreamingResponse(generate(), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
