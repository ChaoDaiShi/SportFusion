import json
from pathlib import Path

import pytest

from tests.golden.formal_contract import (
    REQUIRED,
    validate_formal_artifact,
    validate_sha256_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = json.loads(
    (ROOT / "tests" / "fixtures" / "expected_formal_metrics.json").read_text(encoding="utf-8")
)
ARTIFACT_ROOT = ROOT / "artifacts" / "formal" / EXPECTED["batch_number"]


def require_artifacts() -> None:
    missing = [relative for relative in REQUIRED if not (ARTIFACT_ROOT / relative).is_file()]
    if missing:
        pytest.skip("missing formal artifacts: " + ", ".join(missing))


@pytest.mark.formal_artifact
def test_locked_formal_artifact_matches_golden_contract():
    require_artifacts()
    validate_formal_artifact(ARTIFACT_ROOT, EXPECTED)


@pytest.mark.formal_artifact
def test_sha256_manifest_covers_every_formal_file():
    require_artifacts()
    validate_sha256_manifest(ARTIFACT_ROOT)
