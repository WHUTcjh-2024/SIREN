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
        # Heavy OCR/Torch dependencies are loaded only for an analysis request.
        # The improved estimator uses a dimensionless SIREN coordinate and PINN
        # regularisation centred on the optical axis.
        from modules.high_precision import HighPrecisionDiffractionAnalyzer

        run_id = uuid.uuid4().hex
        run_dir = self.settings.output_dir / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        measurement = HighPrecisionDiffractionAnalyzer().analyse(image_path, progress)
        fitted = measurement["peaks"]
        center_px = float(fitted.center)
        neg_px = float(fitted.negative)
        pos_px = float(fitted.positive)
        dx_pos_px = float(fitted.positive_distance)
        dx_neg_px = float(fitted.negative_distance)
        peaks = {
            "center": {"pixel": center_px},
            "neg": {"pixel": neg_px},
            "pos": {"pixel": pos_px},
        }

        annotated = run_dir / "annotated.png"
        profile_image = run_dir / "intensity_profile.png"
        gray_image = run_dir / "gray_image.png"
        self._annotate(image_path, annotated, peaks, measurement)
        self._plot_profile(
            measurement["profile"], np.arange(len(measurement["profile"])), peaks, profile_image
        )
        self._write_image(gray_image, cv2.cvtColor(measurement["image"], cv2.COLOR_BGR2GRAY))
        combined = run_dir / "combined_result.png"
        return {
            "grayImage": self._url(gray_image),
            "intensityProfile": self._url(profile_image),
            "annotatedImage": self._url(annotated),
            "surface3d": None,
            "combinedImage": self._url(combined) if combined.exists() else None,
            "H0": round(float(measurement["centerHeightCm"]), 4),
            # Δx1 is the lower-image (+1) order; Δx2 is the upper (-1) order.
            "deltaX1": round(float(measurement["positiveDistanceCm"]), 4),
            "deltaX2": round(float(measurement["negativeDistanceCm"]), 4),
            "avgDeltaX": round(float(measurement["averageDistanceCm"]), 4),
            "deltaX1_px": round(dx_pos_px, 3),
            "deltaX2_px": round(dx_neg_px, 3),
            "pxPerCm": round(float(measurement["pixelsPerCm"]), 4),
            "centerPx": round(center_px, 2),
            "negativePeakPx": round(neg_px, 3),
            "positivePeakPx": round(pos_px, 3),
            "rulerMapping": {
                "slope": float(measurement["rulerMapping"]["slope"]),
                "intercept": float(measurement["rulerMapping"]["intercept"]),
                "rSquared": float(measurement["rulerMapping"]["r_squared"]),
                "anchors": measurement["rulerDetections"],
                "rejectedAnchors": measurement["rejectedRulerDetections"],
            },
            "quality": {
                "sirenFitRmse": round(float(measurement["sirenFitRmse"]), 6),
                "calibrationRmseCm": round(float(measurement["calibrationRmseCm"]), 6),
                "method": "dimensionless-siren-pinn-v2",
            },
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

    def _annotate(self, source: Path, target: Path, peaks: dict, measurement: dict | None = None) -> None:
        raw = np.fromfile(source, dtype=np.uint8)
        image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("无法读取上传图像")
        colors = {"center": (0, 0, 255), "neg": (0, 210, 0), "pos": (0, 210, 0)}
        labels = {"center": "0", "neg": "-1", "pos": "+1"}
        if measurement:
            labels = {
                "center": f"0  H0={measurement['centerHeightCm']:.4f}cm",
                "neg": f"-1  dx={measurement['negativeDistanceCm']:.4f}cm",
                "pos": f"+1  dx={measurement['positiveDistanceCm']:.4f}cm",
            }
        font_scale = max(0.55, image.shape[1] / 2200)
        thickness = max(1, round(image.shape[1] / 900))

        # Draw OCR ruler anchors as amber dashed lines before the diffraction
        # orders. Keeping the two annotation layers visually distinct makes it
        # possible to verify both the pixel-to-centimetre calibration and the
        # fringe localisation from a single result image.
        if measurement:
            ruler_color = (0, 190, 255)
            anchors = sorted(
                measurement.get("rulerDetections", []),
                key=lambda item: item["value"],
                reverse=True,
            )
            for anchor in anchors:
                y = int(round(float(anchor["orig_y"])))
                if not 0 <= y < image.shape[0]:
                    continue
                for x0 in range(0, image.shape[1], 28):
                    x1 = min(x0 + 16, image.shape[1] - 1)
                    cv2.line(image, (x0, y), (x1, y), ruler_color, thickness)
                cv2.putText(
                    image,
                    f"{int(anchor['value'])} cm",
                    (12, max(24, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale,
                    ruler_color,
                    thickness,
                    cv2.LINE_AA,
                )

        for key in ("center", "neg", "pos"):
            y = int(round(float(peaks[key]["pixel"])))
            cv2.line(image, (0, y), (image.shape[1], y), colors[key], 2)
            cv2.putText(image, labels[key], (12, max(24, y - 8)), cv2.FONT_HERSHEY_SIMPLEX,
                        font_scale, colors[key], thickness, cv2.LINE_AA)
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
