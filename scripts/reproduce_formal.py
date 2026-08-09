#!/usr/bin/env python
"""
Phase 5 Formal Reproduction Pipeline

Usage: python scripts/reproduce_formal.py [--dry-run] [--skip-missing]

Fail-closed: stops on missing formal artifacts unless --skip-missing.
Does NOT auto-fallback to demo.
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


def check_artifacts() -> dict:
    """Check all required formal artifacts. Returns status dict."""
    from formal_artifacts.manifest import load_manifest
    manifest_path = ROOT / "formal_artifacts" / "manifest.json"
    if not manifest_path.exists():
        print("[ERROR] formal_artifacts/manifest.json not found. Run artifact scan first.")
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = {}
    for a in manifest.get("artifacts", []):
        status[a["artifact_id"]] = a["status"]
    return status


def print_header(title: str):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


def reproduction_pipeline(skip_missing: bool = False):
    """Run the full formal reproduction pipeline."""
    print_header("Artifact Check")
    artifacts = check_artifacts()
    missing = [k for k, v in artifacts.items() if v == "missing"]
    available = [k for k, v in artifacts.items() if v == "available"]

    print(f"  Available: {len(available)}")
    for a in available:
        print(f"    ✅ {a}")
    print(f"  Missing:   {len(missing)}")
    for m in missing:
        print(f"    ❌ {m}")

    if missing and not skip_missing:
        print("\n[STOP] Formal artifacts missing. Use --skip-missing to continue with available data.")
        print("Missing:", ", ".join(missing))
        sys.exit(1)

    # ---- Benchmark ----
    print_header("Benchmark (Recognition Pipeline)")
    from services.sport_recognition import recognize_sport_business

    # Find formal dataset
    import csv
    dataset_paths = sorted(ROOT.glob("data/**/enterprise_dataset_*.csv"))
    if not dataset_paths:
        dataset_paths = sorted(ROOT.glob("submission/**/enterprise*.csv"))

    if dataset_paths and not skip_missing:
        path = dataset_paths[-1]
        with open(path, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        print(f"  Dataset: {path.name} ({len(rows)} rows)")

        # Benchmark: 3 warmup + 5 repeat
        times = []
        for w in range(3):
            for r in rows[:100]:
                recognize_sport_business(r.get("主要业务活动", ""), r.get("行业代码"))
        print(f"  Warmup: 3 iterations done")

        for rep in range(5):
            t0 = time.perf_counter()
            for r in rows:
                recognize_sport_business(r.get("主要业务活动", ""), r.get("行业代码"))
            elapsed = time.perf_counter() - t0
            times.append(elapsed)
            print(f"  Repeat {rep+1}: {elapsed:.2f}s")

        median = sorted(times)[2]
        print(f"\n  Median: {median:.2f}s")
        print(f"  Records/sec: {len(rows)/median:.0f}")
        print(f"  ms/record: {median/len(rows)*1000:.3f}")
    else:
        print("  No formal dataset found — benchmark skipped")

    # ---- Audit ----
    print_header("Audit Run")
    from services.validation_service import run_audit_checks
    audit = run_audit_checks()
    print(f"  Total: {audit.total}")
    print(f"  Passed: {audit.passed}")
    print(f"  Warning: {audit.warnings}")
    print(f"  Failed: {audit.failed}")
    print(f"  Skipped/Pending: {audit.skipped}")

    # ---- Release Manifest ----
    print_header("Release Manifest")
    manifest = {
        "release_version": "SPORTFUSION-RC-2026-08",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "artifact_status": artifacts,
        "audit_summary": {
            "total": audit.total, "passed": audit.passed,
            "failed": audit.failed, "pending": audit.skipped,
        },
    }
    out_path = ROOT / "formal_artifacts" / "release_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"  Written to: {out_path}")

    print_header("Reproduction Complete")
    if missing:
        print(f"  Status: READY_WITH_MISSING_ARTIFACTS ({len(missing)} missing)")
    else:
        print(f"  Status: READY_FOR_RELEASE")
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Phase 5 Formal Reproduction Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Check artifacts only")
    parser.add_argument("--skip-missing", action="store_true", help="Continue despite missing artifacts")
    args = parser.parse_args()

    if args.dry_run:
        check_artifacts()
        print("Dry run complete.")
    else:
        reproduction_pipeline(skip_missing=args.skip_missing)
