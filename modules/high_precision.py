"""High-precision SIREN/PINN fringe and ruler measurement.

The estimator keeps the neural implicit representation, but fixes the coordinate
system used by the original pipeline: the local fringe coordinate is centred on
the optical axis and scaled by the first-order spacing.  PINN regularisation is
therefore applied to a physically meaningful, dimensionless coordinate.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
import torch
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

from calibration.ruler import RulerReader
from models.siren import NeuralImplicitField
from training.loss import Trainer


ProgressCallback = Callable[[str, dict], None]


@dataclass(frozen=True)
class FringePositions:
    negative: float
    center: float
    positive: float

    @property
    def negative_distance(self) -> float:
        return self.center - self.negative

    @property
    def positive_distance(self) -> float:
        return self.positive - self.center


class HighPrecisionDiffractionAnalyzer:
    """Joint continuous fringe fitting and ruler calibration."""

    def __init__(self, device: str | None = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

    @staticmethod
    def _load(path: str | Path) -> np.ndarray:
        raw = np.fromfile(str(path), dtype=np.uint8)
        image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("无法读取实验图像")
        return image

    @staticmethod
    def _profile(image: np.ndarray) -> tuple[np.ndarray, tuple[int, int]]:
        """Build a robust vertical profile from the white/magenta laser field."""
        height, width = image.shape[:2]
        blue, green, red = cv2.split(image.astype(np.float64))
        # The bright fringes are close to white, while the surrounding field is
        # magenta. Combining both makes the three principal orders dominate and
        # suppresses the patterned curtain and the steel ruler.
        white = np.minimum(np.minimum(red, green), blue)
        magenta = np.clip(0.65 * red + 0.35 * blue - 0.30 * green, 0, None)
        response = white + 0.18 * magenta

        x0, x1 = int(round(width * 0.25)), int(round(width * 0.58))
        roi = response[:, x0:x1]
        if roi.shape[1] < 20:
            raise ValueError("衍射区域宽度不足")
        profile = np.percentile(roi, 80, axis=1)
        profile += 0.20 * np.mean(roi, axis=1)
        return profile.astype(np.float64), (x0, x1)

    @staticmethod
    def _initial_triplet(profile: np.ndarray) -> FringePositions:
        height = len(profile)
        sigma = max(0.65, height / 1500.0)
        smooth = gaussian_filter1d(profile, sigma=sigma)
        baseline = gaussian_filter1d(smooth, sigma=max(12.0, height * 0.035))
        signal = smooth - baseline
        lo, hi = int(height * 0.28), int(height * 0.66)
        local = signal[lo:hi]
        peaks, props = find_peaks(
            local,
            distance=max(5, int(round(height * 0.011))),
            prominence=max(1.0, float(np.ptp(local)) * 0.025),
        )
        peaks = peaks + lo
        if len(peaks) < 3:
            raise ValueError("未检测到中央及正负一级亮条纹")

        prominences = props["prominences"]
        keep = np.argsort(prominences)[::-1][: min(16, len(peaks))]
        candidates = sorted((int(peaks[i]), float(prominences[i])) for i in keep)
        pmax = max(value for _, value in candidates)
        best: tuple[float, tuple[int, int, int]] | None = None
        for i in range(len(candidates) - 2):
            for j in range(i + 1, len(candidates) - 1):
                for k in range(j + 1, len(candidates)):
                    y0, p0 = candidates[i]
                    yc, pc = candidates[j]
                    y1, p1 = candidates[k]
                    d0, d1 = yc - y0, y1 - yc
                    mean_d = (d0 + d1) / 2
                    if not height * 0.010 <= mean_d <= height * 0.075:
                        continue
                    asymmetry = abs(d0 - d1) / max(mean_d, 1e-9)
                    if asymmetry > 0.34:
                        continue
                    strength = (p0 + pc + p1) / (3 * pmax)
                    centre_strength = signal[yc] / max(float(np.max(signal)), 1e-9)
                    score = strength + 0.35 * centre_strength - 2.2 * asymmetry
                    if best is None or score > best[0]:
                        best = (score, (y0, yc, y1))
        if best is None:
            top = sorted(y for y, _ in sorted(candidates, key=lambda item: item[1], reverse=True)[:3])
            best = (0.0, (top[0], top[1], top[2]))
        y0, yc, y1 = best[1]
        return FringePositions(float(y0), float(yc), float(y1))

    def _siren_refine(
        self,
        profile: np.ndarray,
        initial: FringePositions,
        progress: ProgressCallback | None,
    ) -> tuple[FringePositions, float]:
        spacing = (initial.negative_distance + initial.positive_distance) / 2
        midpoint = (initial.negative + initial.positive) / 2
        lo = max(0, int(np.floor(initial.negative - 0.75 * spacing)))
        hi = min(len(profile), int(np.ceil(initial.positive + 0.75 * spacing)) + 1)
        pixels = np.arange(lo, hi, dtype=np.float64)

        smooth = gaussian_filter1d(profile, sigma=max(0.55, len(profile) / 1800.0))
        baseline = gaussian_filter1d(smooth, sigma=max(10.0, len(profile) * 0.028))
        observed = np.clip(smooth[lo:hi] - baseline[lo:hi], 0, None)
        observed -= observed.min()
        observed /= max(float(observed.max()), 1e-9)
        coords = (pixels - midpoint) / spacing

        torch.manual_seed(20260628)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(20260628)
        model = NeuralImplicitField(input_dim=1, hidden_dim=72, num_layers=3, freq_0=8.0).to(self.device)
        config = {
            "learning_rate": 1.2e-3,
            "weight_decay": 1e-7,
            # Smooth optical intensity and weak bilateral symmetry are the PINN
            # constraints. The weak symmetry weight does not force equal sides.
            "pinn_weight": 2.0e-5,
            "symmetry_weight": 8.0e-4,
            "early_stopping_patience": 90,
            "early_stopping_min_delta": 2e-7,
        }
        trainer = Trainer(model, config, device=self.device)
        x_tensor = torch.tensor(coords, dtype=torch.float32, device=self.device).unsqueeze(1)
        y_tensor = torch.tensor(observed, dtype=torch.float32, device=self.device).unsqueeze(1)

        def train_progress(epoch: int, total: int, losses: dict) -> None:
            if progress and (epoch == 1 or epoch % 25 == 0 or epoch == total):
                progress("train", {
                    "step": 3,
                    "epoch": epoch,
                    "total": total,
                    "loss": losses["total_loss"],
                    "mse": losses["loss_mse"],
                })

        trainer.train(x_tensor, y_tensor, epochs=420, verbose=False, progress_callback=train_progress)
        model.eval()
        dense_pixels = np.linspace(lo, hi - 1, max(6000, (hi - lo) * 80))
        dense_coords = (dense_pixels - midpoint) / spacing
        chunks = []
        with torch.no_grad():
            for part in np.array_split(dense_coords, max(1, len(dense_coords) // 12000 + 1)):
                values = model(torch.tensor(part, dtype=torch.float32, device=self.device).unsqueeze(1))
                chunks.append(values.squeeze(1).cpu().numpy())
        prediction = np.concatenate(chunks)

        def local_max(seed: float) -> float:
            radius = spacing * 0.32
            mask = (dense_pixels >= seed - radius) & (dense_pixels <= seed + radius)
            indices = np.flatnonzero(mask)
            if not len(indices):
                return seed
            idx = indices[int(np.argmax(prediction[mask]))]
            if 0 < idx < len(prediction) - 1:
                ym, y0, yp = prediction[idx - 1:idx + 2]
                denom = ym - 2 * y0 + yp
                if abs(denom) > 1e-12:
                    offset = 0.5 * (ym - yp) / denom
                    return float(dense_pixels[idx] + offset * (dense_pixels[1] - dense_pixels[0]))
            return float(dense_pixels[idx])

        refined = FringePositions(
            local_max(initial.negative),
            local_max(initial.center),
            local_max(initial.positive),
        )
        # Guard against a neural local maximum jumping to a neighbouring order.
        max_shift = max(1.2, spacing * 0.22)
        values = []
        for neural, seed in zip(
            (refined.negative, refined.center, refined.positive),
            (initial.negative, initial.center, initial.positive),
        ):
            values.append(neural if abs(neural - seed) <= max_shift else seed)
        refined = FringePositions(*values)
        residual = float(np.sqrt(np.mean((model(x_tensor).detach().cpu().numpy().ravel() - observed) ** 2)))
        return refined, residual

    def analyse(self, image_path: str | Path, progress: ProgressCallback | None = None) -> dict:
        if progress:
            progress("step", {"step": 0, "status": "start", "message": "提取激光条纹感兴趣区域"})
        image = self._load(image_path)
        profile, roi = self._profile(image)
        initial = self._initial_triplet(profile)
        if progress:
            progress("step", {"step": 0, "status": "done"})
            progress("step", {"step": 1, "status": "start", "message": "多尺度 OCR 标尺标定"})
        reader = RulerReader(gpu=False)
        detections = reader.detect_ruler_numbers(str(image_path))
        mapping = reader.build_ruler_mapping(detections)
        if mapping is None:
            raise ValueError("右侧刻度尺标定失败：至少需要识别两个整十厘米标记")
        if progress:
            progress("step", {"step": 1, "status": "done"})
            progress("step", {"step": 2, "status": "start", "message": "构建稳健垂直光强剖面"})
            progress("step", {"step": 2, "status": "done"})
            progress("step", {"step": 3, "status": "start", "message": "SIREN 连续光强场拟合"})
        peaks, fit_rmse = self._siren_refine(profile, initial, progress)
        if progress:
            progress("step", {"step": 3, "status": "done"})
            progress("step", {"step": 4, "status": "start", "message": "PINN 约束与亚像素极值定位"})
        if progress:
            progress("step", {"step": 4, "status": "done"})
            progress("step", {"step": 5, "status": "start", "message": "换算物理量与不确定度"})

        slope = float(mapping["slope"])
        intercept = float(mapping["intercept"])
        scale = abs(slope)
        center_cm = slope * peaks.center + intercept
        negative_cm = peaks.negative_distance * scale
        positive_cm = peaks.positive_distance * scale
        calibration_anchors = mapping["anchors"]
        predicted = np.array([slope * d["orig_y"] + intercept for d in calibration_anchors])
        labels = np.array([d["value"] for d in calibration_anchors], dtype=float)
        calibration_rmse = float(np.sqrt(np.mean((labels - predicted) ** 2)))

        if progress:
            progress("step", {"step": 5, "status": "done"})
        return {
            "image": image,
            "profile": profile,
            "profileRoi": roi,
            "initial": initial,
            "peaks": peaks,
            "rulerDetections": calibration_anchors,
            "rejectedRulerDetections": mapping.get("rejected_anchors", []),
            "rulerMapping": mapping,
            "centerHeightCm": center_cm,
            "negativeDistancePx": peaks.negative_distance,
            "positiveDistancePx": peaks.positive_distance,
            "negativeDistanceCm": negative_cm,
            "positiveDistanceCm": positive_cm,
            "averageDistanceCm": (negative_cm + positive_cm) / 2,
            "pixelsPerCm": 1.0 / scale,
            "sirenFitRmse": fit_rmse,
            "calibrationRmseCm": calibration_rmse,
        }
