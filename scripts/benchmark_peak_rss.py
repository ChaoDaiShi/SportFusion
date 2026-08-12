#!/usr/bin/env python
"""Strict recognition benchmark with same-run peak RSS measurement.

Measures recognition runtime and memory in the same Linux process that performs
full-batch recognition. Each measured repeat runs in a fresh child process so
peak RSS is independent across repeats.

Output: formal_artifacts/benchmark_peak_rss.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import resource
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


def rss_mib() -> float:
    """Return Linux process maximum resident set size in MiB."""
    # Linux ru_maxrss is KiB. (macOS differs, but formal workflow is Ubuntu.)
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def find_dataset() -> Path:
    paths = sorted(ROOT.glob("submission/**/enterprise_dataset_*.csv"))
    if not paths:
        paths = sorted(ROOT.glob("data/**/enterprise_dataset_*.csv"))
    if not paths:
        raise FileNotFoundError("formal enterprise_dataset_*.csv not found")
    return paths[-1]


def single_run() -> dict:
    from services.sport_recognition import recognize_sport_business

    path = find_dataset()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    # Same warm-up policy as Phase 5: 3 × first 100 records.
    for _ in range(3):
        for row in rows[:100]:
            recognize_sport_business(row.get("主要业务活动", ""), row.get("行业代码"))

    baseline_rss = rss_mib()
    t0 = time.perf_counter()
    sport_count = 0
    for row in rows:
        result = recognize_sport_business(row.get("主要业务活动", ""), row.get("行业代码"))
        sport_count += int(bool(result.get("is_sport")))
    elapsed = time.perf_counter() - t0
    peak_rss = rss_mib()

    return {
        "dataset": str(path.relative_to(ROOT)),
        "rows": len(rows),
        "sport_candidates": sport_count,
        "elapsed_seconds": elapsed,
        "records_per_second": len(rows) / elapsed,
        "ms_per_record": elapsed / len(rows) * 1000,
        "baseline_rss_mib": baseline_rss,
        "peak_rss_mib": peak_rss,
        "incremental_peak_rss_mib": max(0.0, peak_rss - baseline_rss),
    }


def child() -> int:
    result = single_run()
    print(json.dumps(result, ensure_ascii=False))
    return 0


def cpu_model() -> str:
    try:
        text = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def mem_total_mib() -> float | None:
    try:
        text = Path("/proc/meminfo").read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) / 1024.0
    except OSError:
        pass
    return None


def run_repeats(repeats: int) -> dict:
    samples: list[dict] = []
    for i in range(repeats):
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--child"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        line = proc.stdout.strip().splitlines()[-1]
        sample = json.loads(line)
        samples.append(sample)
        print(
            f"repeat {i + 1}/{repeats}: {sample['elapsed_seconds']:.3f}s, "
            f"{sample['records_per_second']:.0f} rec/s, "
            f"peak RSS {sample['peak_rss_mib']:.2f} MiB, "
            f"delta {sample['incremental_peak_rss_mib']:.2f} MiB"
        )

    elapsed = [s["elapsed_seconds"] for s in samples]
    throughput = [s["records_per_second"] for s in samples]
    peak = [s["peak_rss_mib"] for s in samples]
    baseline = [s["baseline_rss_mib"] for s in samples]
    delta = [s["incremental_peak_rss_mib"] for s in samples]

    summary = {
        "benchmark_id": "recognition-peak-rss-v1",
        "method": {
            "measured_repeats": repeats,
            "warmup_per_repeat": "3 x first 100 records",
            "process_isolation": "fresh child process per measured repeat",
            "memory_metric": "resource.getrusage(RUSAGE_SELF).ru_maxrss on Linux",
            "scope": "dataset loaded + recognition pipeline; delta is peak above post-load/post-warmup baseline",
        },
        "environment": {
            "runner_os": os.environ.get("RUNNER_OS", platform.system()),
            "runner_arch": os.environ.get("RUNNER_ARCH", platform.machine()),
            "python": platform.python_version(),
            "cpu_model": cpu_model(),
            "logical_cpus": os.cpu_count(),
            "mem_total_mib": mem_total_mib(),
            "git_sha": os.environ.get("GITHUB_SHA", "unknown"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        },
        "dataset": samples[0]["dataset"],
        "rows": samples[0]["rows"],
        "sport_candidates": samples[0]["sport_candidates"],
        "samples": samples,
        "summary": {
            "median_elapsed_seconds": statistics.median(elapsed),
            "min_elapsed_seconds": min(elapsed),
            "max_elapsed_seconds": max(elapsed),
            "median_records_per_second": statistics.median(throughput),
            "median_ms_per_record": statistics.median(elapsed) / samples[0]["rows"] * 1000,
            "median_baseline_rss_mib": statistics.median(baseline),
            "median_peak_rss_mib": statistics.median(peak),
            "max_peak_rss_mib": max(peak),
            "median_incremental_peak_rss_mib": statistics.median(delta),
            "max_incremental_peak_rss_mib": max(delta),
        },
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "formal_artifacts" / "benchmark_peak_rss.json",
    )
    args = parser.parse_args()

    if args.child:
        return child()

    result = run_repeats(args.repeats)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nSUMMARY")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
