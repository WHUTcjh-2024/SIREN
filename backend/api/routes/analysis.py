import shutil
import tempfile
import threading
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from backend.core.config import get_settings
from backend.services.analysis import DiffractionAnalysisService

router = APIRouter(tags=["analysis"])
ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
_ANALYSIS_SLOTS = threading.BoundedSemaphore(get_settings().max_concurrent_analyses)


def _reserve_analysis_slot() -> None:
    if not _ANALYSIS_SLOTS.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="分析服务繁忙，请稍后重试")


def _validate_image(path: Path) -> None:
    settings = get_settings()
    try:
        with Image.open(path) as image:
            width, height = image.size
            if width <= 0 or height <= 0 or width * height > settings.max_image_pixels:
                raise HTTPException(status_code=413, detail="图像像素数量超过限制")
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=415, detail="上传内容不是有效图像") from exc


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
    if size == 0:
        shutil.rmtree(directory, ignore_errors=True)
        raise HTTPException(status_code=400, detail="上传图像为空")
    try:
        _validate_image(target)
    except HTTPException:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    return target, directory


@router.post("/laser-diffraction")
async def analyse(images: list[UploadFile] = File(...)) -> dict:
    if len(images) != 1:
        raise HTTPException(status_code=400, detail="每次必须且只能上传一张图像")
    _reserve_analysis_slot()
    try:
        path, directory = await _save_upload(images[0])
    except Exception:
        _ANALYSIS_SLOTS.release()
        raise
    try:
        result = await run_in_threadpool(DiffractionAnalysisService(get_settings()).analyse, path)
        return {"success": True, "data": result}
    finally:
        shutil.rmtree(directory, ignore_errors=True)
        _ANALYSIS_SLOTS.release()


@router.post("/laser-diffraction-stream")
async def analyse_stream(images: list[UploadFile] = File(...)) -> StreamingResponse:
    if len(images) != 1:
        raise HTTPException(status_code=400, detail="每次必须且只能上传一张图像")
    _reserve_analysis_slot()
    try:
        path, directory = await _save_upload(images[0])
    except Exception:
        _ANALYSIS_SLOTS.release()
        raise
    service = DiffractionAnalysisService(get_settings())

    def generate():
        try:
            yield from service.stream(path)
        finally:
            shutil.rmtree(directory, ignore_errors=True)
            _ANALYSIS_SLOTS.release()

    return StreamingResponse(generate(), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
