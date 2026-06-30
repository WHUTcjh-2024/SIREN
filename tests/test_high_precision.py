from pathlib import Path

import numpy as np

from calibration.ruler import RulerReader
from modules.high_precision import HighPrecisionDiffractionAnalyzer


def test_ruler_mapping_rejects_geometric_ocr_outlier():
    detections = [
        {"value": 40, "orig_y": 56, "confidence": 0.9},
        {"value": 30, "orig_y": 153, "confidence": 0.6},  # partial-label false positive
        {"value": 20, "orig_y": 335, "confidence": 1.0},
        {"value": 10, "orig_y": 474, "confidence": 0.8},
    ]
    mapping = RulerReader.build_ruler_mapping(detections)
    assert mapping is not None
    assert [(item["value"], item["orig_y"]) for item in mapping["rejected_anchors"]] == [(30, 153)]
    assert mapping["r_squared"] > 0.999


def test_symmetric_triplet_selection_ignores_unrelated_peaks():
    y = np.arange(800, dtype=np.float64)
    profile = np.full_like(y, 30.0)
    for center, amplitude, width in ((342, 130, 3.2), (380, 180, 3.8), (419, 140, 3.4)):
        profile += amplitude * np.exp(-0.5 * ((y - center) / width) ** 2)
    profile += 90 * np.exp(-0.5 * ((y - 610) / 4.0) ** 2)
    peaks = HighPrecisionDiffractionAnalyzer._initial_triplet(profile)
    assert abs(peaks.negative - 342) <= 1
    assert abs(peaks.center - 380) <= 1
    assert abs(peaks.positive - 419) <= 1


def test_reference_experiment_selects_three_adjacent_principal_fringes():
    image_path = Path(__file__).resolve().parents[1] / "实验图片" / "实验图片 (1).jpg"
    image = HighPrecisionDiffractionAnalyzer._load(image_path)
    profile, _ = HighPrecisionDiffractionAnalyzer._profile(image)

    peaks = HighPrecisionDiffractionAnalyzer._initial_triplet(profile)

    assert abs(peaks.negative - 789) <= 2
    assert abs(peaks.center - 828) <= 2
    assert abs(peaks.positive - 862) <= 2
