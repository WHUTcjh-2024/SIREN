from scripts.benchmark_measurement import summarize


def test_benchmark_summary_counts_failures_and_calculates_error():
    report = summarize(
        [
            {"status": "ok", "absoluteErrorsPx": [1.0, 0.0, 1.0], "durationSeconds": 2.0},
            {"status": "failed", "durationSeconds": 1.0},
        ],
        total=2,
    )
    assert report["failureRate"] == 0.5
    assert report["peakMaePx"] == 2 / 3
    assert report["peakRmsePx"] > report["peakMaePx"]
