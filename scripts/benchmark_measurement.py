"""Run a traceable blind benchmark against manually reviewed fringe positions.

Manifest CSV columns: image, negative_px, center_px, positive_px. Image paths are
resolved relative to the manifest. The command exits non-zero when any supplied
acceptance threshold is missed, which makes the report usable in CI or delivery.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.high_precision import HighPrecisionDiffractionAnalyzer


@dataclass(frozen=True)
class Reference:
    image: Path
    negative_px: float
    center_px: float
    positive_px: float


def load_manifest(path: Path) -> list[Reference]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    required = {"image", "negative_px", "center_px", "positive_px"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"基准清单必须包含列：{', '.join(sorted(required))}")
    references: list[Reference] = []
    for number, row in enumerate(rows, start=2):
        image = (path.parent / row["image"]).resolve()
        if not image.is_file():
            raise ValueError(f"第 {number} 行图像不存在：{row['image']}")
        try:
            positions = [float(row[key]) for key in ("negative_px", "center_px", "positive_px")]
        except (TypeError, ValueError) as exc:
            raise ValueError(f"第 {number} 行参考坐标无效") from exc
        if not positions[0] < positions[1] < positions[2]:
            raise ValueError(f"第 {number} 行参考坐标必须递增")
        references.append(Reference(image, *positions))
    return references


def summarize(rows: list[dict[str, Any]], total: int) -> dict[str, Any]:
    successful = [row for row in rows if row["status"] == "ok"]
    errors = [error for row in successful for error in row["absoluteErrorsPx"]]
    durations = sorted(float(row["durationSeconds"]) for row in successful)
    percentile_index = max(0, math.ceil(len(durations) * 0.95) - 1)
    return {
        "sampleCount": total,
        "successCount": len(successful),
        "failureCount": total - len(successful),
        "failureRate": (total - len(successful)) / total,
        "peakMaePx": statistics.fmean(errors) if errors else None,
        "peakRmsePx": math.sqrt(statistics.fmean(value * value for value in errors)) if errors else None,
        "peakMaxErrorPx": max(errors) if errors else None,
        "medianDurationSeconds": statistics.median(durations) if durations else None,
        "p95DurationSeconds": durations[percentile_index] if durations else None,
    }


def run(references: list[Reference], device: str | None = None) -> dict[str, Any]:
    analyzer = HighPrecisionDiffractionAnalyzer(device=device)
    rows: list[dict[str, Any]] = []
    for reference in references:
        started = time.perf_counter()
        try:
            result = analyzer.analyse(reference.image)
            predicted = result["peaks"]
            actual = [reference.negative_px, reference.center_px, reference.positive_px]
            values = [predicted.negative, predicted.center, predicted.positive]
            rows.append(
                {
                    "image": str(reference.image),
                    "status": "ok",
                    "predictedPx": values,
                    "referencePx": actual,
                    "absoluteErrorsPx": [abs(left - right) for left, right in zip(values, actual)],
                    "durationSeconds": time.perf_counter() - started,
                    "fitRmse": result["sirenFitRmse"],
                    "calibrationRmseCm": result["calibrationRmseCm"],
                }
            )
        except Exception as exc:  # A benchmark must preserve per-sample failures.
            rows.append(
                {
                    "image": str(reference.image),
                    "status": "failed",
                    "errorType": type(exc).__name__,
                    "error": str(exc),
                    "durationSeconds": time.perf_counter() - started,
                }
            )
    return {"method": "dimensionless-siren-regularized-v2", "summary": summarize(rows, len(references)), "samples": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="SIREN 测量盲测基准")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, default=Path("output/measurement-benchmark.json"))
    parser.add_argument("--device", choices=("cpu", "cuda"))
    parser.add_argument("--max-rmse-px", type=float)
    parser.add_argument("--max-failure-rate", type=float)
    args = parser.parse_args()
    references = load_manifest(args.manifest.resolve())
    report = run(references, args.device)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = report["summary"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    failed = False
    if args.max_rmse_px is not None:
        failed |= summary["peakRmsePx"] is None or summary["peakRmsePx"] > args.max_rmse_px
    if args.max_failure_rate is not None:
        failed |= summary["failureRate"] > args.max_failure_rate
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
