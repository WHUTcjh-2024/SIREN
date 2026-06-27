import json
import shutil
import tempfile
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

import cv2
import numpy as np

from backend.core.config import Settings
ProgressCallback = Callable[[str, dict], None]


class DiffractionAnalysisService:
    """Application service around the scientific pipeline.

    It owns file lifecycle and API serialization; the model remains independent
    from FastAPI, which makes it testable from the CLI and worker processes.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    def analyse(self, image_path: Path, progress: ProgressCallback | None = None) -> dict:
        # Heavy OCR/Torch dependencies are loaded only for an analysis request;
        # health checks and Agent endpoints stay fast and independently usable.
        from main import DiffractionAnalysisPipeline

        run_id = uuid.uuid4().hex
        run_dir = self.settings.output_dir / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        pipeline = DiffractionAnalysisPipeline(str(image_path), progress_callback=progress)
        pipeline.run(save_dir=str(run_dir))
        system = pipeline.system
        peaks = system.three_peaks
        if not peaks:
            raise ValueError("未检测到有效衍射峰")

        center_px = float(peaks["center"]["pixel"])
        pos_px = float(peaks["pos"]["pixel"])
        neg_px = float(peaks["neg"]["pixel"])
        dx1_px, dx2_px = abs(pos_px - center_px), abs(center_px - neg_px)
        mapping = system.ruler_mapping
        if mapping:
            slope = abs(float(mapping["slope"]))
            h0 = float(mapping["slope"]) * center_px + float(mapping["intercept"])
            dx1_cm, dx2_cm = slope * dx1_px, slope * dx2_px
            px_per_cm = 1 / slope if slope > 1e-12 else None
        else:
            h0 = dx1_cm = dx2_cm = px_per_cm = None

        annotated = run_dir / "annotated.png"
        profile_image = run_dir / "intensity_profile.png"
        gray_image = run_dir / "gray_image.png"
        self._annotate(image_path, annotated, peaks)
        self._plot_profile(system.full_profile, system.x_coords, peaks, profile_image)
        self._write_image(gray_image, system.gray_image)
        combined = run_dir / "combined_result.png"
        return {
            "grayImage": self._url(gray_image),
            "intensityProfile": self._url(profile_image),
            "annotatedImage": self._url(annotated),
            "surface3d": None,
            "combinedImage": self._url(combined) if combined.exists() else None,
            "H0": round(h0, 4) if h0 is not None else None,
            "deltaX1": round(dx1_cm, 4) if dx1_cm is not None else None,
            "deltaX2": round(dx2_cm, 4) if dx2_cm is not None else None,
            "avgDeltaX": round((dx1_cm + dx2_cm) / 2, 4) if dx1_cm is not None else None,
            "deltaX1_px": round(dx1_px, 2),
            "deltaX2_px": round(dx2_px, 2),
            "pxPerCm": round(px_per_cm, 2) if px_per_cm is not None else None,
            "centerPx": round(center_px, 2),
            "rulerMapping": {"slope": mapping["slope"], "intercept": mapping["intercept"]} if mapping else None,
            "runId": run_id,
        }

    def stream(self, image_path: Path) -> Iterator[str]:
        events: list[dict] = []

        def progress(event: str, data: dict) -> None:
            events.append({"event": event, "data": data})

        try:
            result = self.analyse(image_path, progress)
            for event in events:
                yield json.dumps(event, ensure_ascii=False) + "\n"
            yield json.dumps({"event": "result", "data": {"success": True, "data": result}}, ensure_ascii=False) + "\n"
        except Exception as exc:
            yield json.dumps({"event": "error", "data": {"message": f"分析失败: {exc}"}}, ensure_ascii=False) + "\n"

    def _url(self, path: Path) -> str:
        relative = path.relative_to(self.settings.output_dir).as_posix()
        return f"/output/{relative}?t={uuid.uuid4().hex[:8]}"

    @staticmethod
    def _write_image(path: Path, image: np.ndarray | None) -> None:
        if image is None:
            return
        ok, buffer = cv2.imencode(".png", image)
        if not ok:
            raise ValueError("图像编码失败")
        buffer.tofile(path)

    def _annotate(self, source: Path, target: Path, peaks: dict) -> None:
        raw = np.fromfile(source, dtype=np.uint8)
        image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("无法读取上传图像")
        colors = {"center": (0, 0, 255), "neg": (0, 210, 0), "pos": (0, 210, 0)}
        labels = {"center": "0", "neg": "-1", "pos": "+1"}
        for key in ("center", "neg", "pos"):
            y = int(round(float(peaks[key]["pixel"])))
            cv2.line(image, (0, y), (image.shape[1], y), colors[key], 2)
            cv2.putText(image, labels[key], (12, max(24, y - 8)), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, colors[key], 2, cv2.LINE_AA)
        self._write_image(target, image)

    @staticmethod
    def _plot_profile(profile: np.ndarray, x_coords: np.ndarray, peaks: dict, target: Path) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(12, 5.5))
        ax.plot(x_coords, profile, color="#4F46E5", linewidth=1.6)
        for key, color in (("center", "#EF4444"), ("neg", "#22C55E"), ("pos", "#22C55E")):
            ax.axvline(float(peaks[key]["pixel"]), color=color, linestyle="--", linewidth=1.5)
        ax.set_xlabel("像素坐标")
        ax.set_ylabel("光强")
        ax.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(target, dpi=180, bbox_inches="tight")
        plt.close(fig)
