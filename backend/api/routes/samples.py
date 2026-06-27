from pathlib import Path

from fastapi import APIRouter

from backend.core.config import ROOT_DIR

router = APIRouter(tags=["samples"])


@router.get("/samples")
def samples() -> dict:
    root = ROOT_DIR / "static" / "samples"
    labels = {
        "image1.png": "单缝衍射", "image2.png": "圆孔衍射",
        "image3.png": "光栅衍射", "image4.png": "矩孔衍射",
    }
    files = [] if not root.exists() else sorted(
        item for item in root.iterdir() if item.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}
    )
    return {
        "code": 200,
        "msg": "获取示例图片成功",
        "data": {"images": [
            {"src": f"/samples/{item.name}", "name": labels.get(item.name, item.stem)} for item in files
        ]},
    }
