#!/usr/bin/env python
"""Strict full-batch SportFusion recognition benchmark with peak RSS.

The benchmark is intended for the locked formal-report baseline.  Each measured
repeat runs in a fresh child process.  The child loads the same enterprise CSV,
performs the same 3 x 100-record warm-up used by Phase 5, then times one complete
recognition pass and records Linux ru_maxrss for that same process.

The benchmark fails if the recognition result is not the locked 8,950 candidates.
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
EXPECTED_ROWS = 76687
EXPECTED_CANDIDATES = 8950


def rss_mib() -> float:
    # Linux resource.ru_maxrss is KiB.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def find_dataset() -> Path:
    paths = sorted(ROOT.glob("submission/**/enterprise_dataset_*.csv"))
    if not paths:
        paths = sorted(ROOT.glob("data/**/enterprise_dataset_*.csv"))
    if not paths:
        raise FileNotFoundError("enterprise_dataset_*.csv not found")
    return paths[-1]


def single_run() -> dict:
    from services.sport_recognition import recognize_sport_business

    path = find_dataset()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != EXPECTED_ROWS:
        raise RuntimeError(f"row count drift: {len(rows)} != {EXPECTED_ROWS}")

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

    if sport_count != EXPECTED_CANDIDATES:
        raise RuntimeError(
            f"candidate count drift: {sport_count} != {EXPECTED_CANDIDATES}; "
            "benchmark is not valid for the locked report baseline"
        )

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
    print(json.dumps(single_run(), ensure_ascii=False))
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
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
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
        sample = json.loads(proc.stdout.strip().splitlines()[-1])
        samples.append(sample)
        print(
            f"repeat {i+1}/{repeats}: {sample['elapsed_seconds']:.3f}s, "
            f"{sample['records_per_second']:.0f} rec/s, "
            f"peak RSS {sample['peak_rss_mib']:.2f} MiB"
        )

    elapsed = [s["elapsed_seconds"] for s in samples]
    throughput = [s["records_per_second"] for s in samples]
    peak = [s["peak_rss_mib"] for s in samples]
    baseline = [s["baseline_rss_mib"] for s in samples]
    delta = [s["incremental_peak_rss_mib"] for s in samples]
    return {
        "benchmark_id": "formal-recognition-peak-rss-v1",
        "method": {
            "measured_repeats": repeats,
            "warmup_per_repeat": "3 x first 100 records",
            "process_isolation": "fresh child process per repeat",
            "memory_metric": "resource.getrusage(RUSAGE_SELF).ru_maxrss (Linux)",
            "memory_scope": "process RSS including loaded full input and recognition execution",
            "validity_guard": f"rows={EXPECTED_ROWS}, sport_candidates={EXPECTED_CANDIDATES}",
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
            "median_ms_per_record": statistics.median(elapsed) / EXPECTED_ROWS * 1000,
            "median_baseline_rss_mib": statistics.median(baseline),
            "median_peak_rss_mib": statistics.median(peak),
            "max_peak_rss_mib": max(peak),
            "median_incremental_peak_rss_mib": statistics.median(delta),
            "max_incremental_peak_rss_mib": max(delta),
        },
    }


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
    print("SUMMARY")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
