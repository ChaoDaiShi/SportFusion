import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALGORITHM_ROOTS = (ROOT / "backend" / "domain", ROOT / "analysis")
FORBIDDEN = {
    "golden literal": re.compile(r"(?<![\d.])(8950|8016|191\.94|2170\.80)(?![\d.])"),
    "batch-specific return": re.compile(r"BATCH-20260803-R1.{0,120}return", re.DOTALL),
    "formal demo fallback": re.compile(
        r"formal.{0,120}(fallback|回退).{0,80}demo", re.IGNORECASE | re.DOTALL
    ),
}


def test_new_algorithm_modules_do_not_embed_golden_results():
    violations = []
    for root in ALGORITHM_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for label, pattern in FORBIDDEN.items():
                if pattern.search(text):
                    violations.append(f"{path.relative_to(ROOT)}: {label}")
    assert violations == []
