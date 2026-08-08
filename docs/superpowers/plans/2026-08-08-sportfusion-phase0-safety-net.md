# SportFusion Phase 0 Safety Net Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不修改现有算法和 Vue 业务口径的前提下，为 SportFusion 建立可复现依赖、分层测试、Golden 契约、配置哈希、Alembic 基线和 CI。

**Architecture:** 保留现有 `backend/requirements.txt`、`backend/.venv` 和启动脚本，新增根目录 uv 工程与 pytest 入口。测试分为现状回归、报告契约和可选正式产物三层；配置加载器与 Alembic 只建立边界，不接入现有业务服务。

**Tech Stack:** Python 3.11.9、uv 0.11.32、FastAPI 0.115.6、SQLAlchemy 2.0.36、Alembic 1.x、pytest 8.x、PyYAML 6.x、Vue 3、Node.js 24、Vite 6。

## Global Constraints

- 基线必须是 `master@6e13f2f`，其父提交 `1d865fc4cd9dbb78cf355b19345fb44c16edd46e` 是 v1.0 业务代码基线。
- Phase 0 不修改 `backend/services/sport_recognition.py`、`sport_share_service.py`、`scale_measure_service.py`、`model_validate.py` 及任何 Vue 业务页面。
- `data/processed_BATCH-20260803-R1` 只能标记为 legacy，不得认证为新的 formal artifact。
- 缺少 500 条 SportShare 样本、RF 模型、q90、校准配置、12 情景或 24 项审计时，必须报告缺失，不能生成替代数据。
- Golden 数字只能进入测试 fixture、测试断言、来源配置或正式产物，不能写入算法模块。
- 测试不得访问外部网络、DeepSeek 或其他大模型服务。
- Alembic 测试只操作 pytest 临时目录中的 SQLite 数据库，不能迁移工作区的 `backend/sports_industry.db`。
- 每个任务单独提交；提交前运行该任务列出的测试。

---

### Task 1: 建立 uv 工程和统一 pytest 入口

**Files:**
- Create: `pyproject.toml`
- Create: `uv.lock`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/unit/test_project_metadata.py`
- Modify: `backend/requirements.txt`

**Interfaces:**
- Consumes: 当前 `backend/requirements.txt` 中的运行依赖和本机 Python 3.11.9。
- Produces: `uv sync --locked` 可复现环境；`uv run pytest` 可发现顶层测试和 `backend/tests`。

- [ ] **Step 1: 创建项目元数据失败测试**

创建空的 `tests/__init__.py`、`tests/unit/__init__.py`。创建 `tests/conftest.py`，让旧测试可以沿用当前绝对导入：

```python
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
```

创建 `tests/unit/test_project_metadata.py`：

```python
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[2]


def load_project() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)


def test_project_pins_python_311_and_runtime_dependencies():
    project = load_project()["project"]
    assert project["requires-python"] == ">=3.11,<3.12"
    dependencies = "\n".join(project["dependencies"])
    for package in ("fastapi", "sqlalchemy", "pydantic", "pandas", "scikit-learn", "PyYAML"):
        assert package.lower() in dependencies.lower()


def test_project_declares_phase0_development_tools():
    config = load_project()
    dev = "\n".join(config["dependency-groups"]["dev"])
    for package in ("pytest", "pytest-asyncio", "httpx", "ruff", "alembic"):
        assert package.lower() in dev.lower()


def test_pytest_collects_top_level_and_legacy_tests():
    testpaths = load_project()["tool"]["pytest"]["ini_options"]["testpaths"]
    assert testpaths == ["tests", "backend/tests"]
```

- [ ] **Step 2: 安装执行测试所需的固定版本 uv**

Run:

```powershell
python -m pip install uv==0.11.32
uv --version
```

Expected: 输出 `uv 0.11.32`。如果网络沙箱阻止 PyPI，申请一次仅用于安装 uv 的网络权限，不改用来源不明的二进制。

- [ ] **Step 3: 运行测试，确认因缺少 pyproject 失败**

Run:

```powershell
uv run --no-project --with pytest==8.3.5 pytest tests/unit/test_project_metadata.py -v
```

Expected: 3 tests failed，首个错误包含 `pyproject.toml` 不存在。

- [ ] **Step 4: 创建 pyproject.toml**

创建 `pyproject.toml`：

```toml
[project]
name = "sportfusion"
version = "1.0.0"
description = "SportFusion sports industry boundary recognition and structural estimation platform"
requires-python = ">=3.11,<3.12"
dependencies = [
  "fastapi==0.115.6",
  "uvicorn[standard]==0.34.0",
  "sqlalchemy==2.0.36",
  "pydantic==2.10.3",
  "python-multipart==0.0.19",
  "python-dotenv==1.0.1",
  "cryptography==44.0.0",
  "openpyxl==3.1.5",
  "pandas==2.2.3",
  "matplotlib>=3.8,<4",
  "jieba==0.42.1",
  "numpy==2.2.1",
  "scikit-learn==1.6.0",
  "aiofiles==24.1.0",
  "openai>=1.0.0,<3",
  "PyYAML>=6.0,<7",
]

[dependency-groups]
dev = [
  "alembic>=1.14,<2",
  "httpx>=0.28,<1",
  "pytest>=8.3,<9",
  "pytest-asyncio>=0.24,<1",
  "ruff>=0.9,<1",
]

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests", "backend/tests"]
addopts = "-ra --strict-markers"
markers = [
  "formal_artifact: requires a complete locked formal batch artifact",
]

[tool.ruff]
target-version = "py311"
line-length = 100
```

- [ ] **Step 5: 生成锁文件**

Run:

```powershell
uv lock --python 3.11
```

Expected: 根目录生成 `uv.lock`。如果网络沙箱阻止项目依赖下载，申请仅用于 PyPI 依赖同步的网络权限。

- [ ] **Step 6: 从锁定项目导出兼容 requirements**

Run:

```powershell
uv export --locked --no-dev --format requirements-txt --no-hashes --output-file backend/requirements.txt
```

Expected: `backend/requirements.txt` 包含运行依赖，不包含 pytest、ruff 或 Alembic。

- [ ] **Step 7: 运行元数据测试和旧后端测试**

Run:

```powershell
uv sync --locked
uv run pytest tests/unit/test_project_metadata.py backend/tests -v
```

Expected: 7 tests passed，包括新增 3 项和旧后端 4 项。

- [ ] **Step 8: 提交依赖基础设施**

```powershell
git add pyproject.toml uv.lock backend/requirements.txt tests/__init__.py tests/conftest.py tests/unit/__init__.py tests/unit/test_project_metadata.py
git commit -m "build: add reproducible uv environment"
```

---

### Task 2: 建立版本化配置与 SHA256 校验边界

**Files:**
- Create: `backend/core/__init__.py`
- Create: `backend/core/versions.py`
- Create: `backend/core/configuration.py`
- Create: `config/manifest.yaml`
- Create: `config/sportscore.yaml`
- Create: `config/sportshare.yaml`
- Create: `config/sports_business_dictionary.yaml`
- Create: `config/industry_code_map.yaml`
- Create: `config/evidence_calibration.yaml`
- Create: `config/official_structure_2022.yaml`
- Create: `config/scale_scenarios.yaml`
- Create: `tests/unit/test_configuration.py`

**Interfaces:**
- Consumes: Task 1 提供的 PyYAML 和 pytest。
- Produces: `load_config(path: Path) -> dict`、`sha256_file(path: Path) -> str`、`require_formal_config(path: Path) -> dict`；后续阶段只通过这三个入口读取正式配置。

- [ ] **Step 1: 写配置加载失败测试**

创建 `tests/unit/test_configuration.py`：

```python
from hashlib import sha256
from pathlib import Path

import pytest

from backend.core import configuration
from backend.core.configuration import (
    ConfigurationHashMismatch,
    ConfigurationNotFound,
    ConfigurationParseError,
    ConfigurationVersionError,
    FormalConfigurationUnavailable,
    load_config,
    require_formal_config,
    sha256_file,
)


def write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_sha256_file_hashes_original_bytes(tmp_path):
    path = tmp_path / "sample.yaml"
    payload = "schema_version: 1\nconfig_id: SAMPLE\nversion: V1\nstatus: ready\n"
    path.write_bytes(payload.encode("utf-8"))
    assert sha256_file(path) == sha256(payload.encode("utf-8")).hexdigest()


def test_load_config_rejects_invalid_yaml(tmp_path):
    path = write(tmp_path / "broken.yaml", "schema_version: [\n")
    with pytest.raises(ConfigurationParseError, match="broken.yaml"):
        load_config(path)


def test_load_config_distinguishes_missing_file(tmp_path):
    with pytest.raises(ConfigurationNotFound, match="missing.yaml"):
        load_config(tmp_path / "missing.yaml")


def test_load_config_rejects_empty_version(tmp_path):
    path = write(
        tmp_path / "empty-version.yaml",
        "schema_version: 1\nconfig_id: SAMPLE\nversion: ''\nstatus: ready\n",
    )
    with pytest.raises(ConfigurationVersionError, match="version"):
        load_config(path)


def test_require_formal_config_rejects_not_imported(tmp_path):
    path = write(
        tmp_path / "sportshare.yaml",
        "schema_version: 1\nconfig_id: SPORT-SHARE-CONFIG\n"
        "version: NOT-IMPORTED\nstatus: not_imported\n",
    )
    with pytest.raises(FormalConfigurationUnavailable, match="not_imported"):
        require_formal_config(path)


def test_require_formal_config_rejects_hash_mismatch(tmp_path, monkeypatch):
    path = write(
        tmp_path / "sportscore.yaml",
        "schema_version: 1\nconfig_id: SPORT-SCORE-CONFIG\nversion: V1\nstatus: ready\n",
    )
    manifest = write(
        tmp_path / "manifest.yaml",
        "schema_version: 1\nconfig_id: CONFIG-MANIFEST\nversion: PHASE0\nstatus: ready\n"
        "configs:\n  - config_id: SPORT-SCORE-CONFIG\n    path: config/sportscore.yaml\n"
        "    version: V1\n    status: ready\n    sha256: deadbeef\n",
    )
    monkeypatch.setattr(configuration, "MANIFEST_PATH", manifest)
    with pytest.raises(ConfigurationHashMismatch, match="SPORT-SCORE-CONFIG"):
        require_formal_config(path)


def test_require_formal_config_returns_verified_config(tmp_path, monkeypatch):
    path = write(
        tmp_path / "sportscore.yaml",
        "schema_version: 1\nconfig_id: SPORT-SCORE-CONFIG\nversion: V1\nstatus: ready\n",
    )
    digest = sha256_file(path)
    manifest = write(
        tmp_path / "manifest.yaml",
        "schema_version: 1\nconfig_id: CONFIG-MANIFEST\nversion: PHASE0\nstatus: ready\n"
        "configs:\n  - config_id: SPORT-SCORE-CONFIG\n    path: config/sportscore.yaml\n"
        f"    version: V1\n    status: ready\n    sha256: {digest}\n",
    )
    monkeypatch.setattr(configuration, "MANIFEST_PATH", manifest)
    assert require_formal_config(path)["version"] == "V1"
```

- [ ] **Step 2: 运行测试，确认模块不存在**

Run:

```powershell
uv run pytest tests/unit/test_configuration.py -v
```

Expected: collection FAIL，错误包含 `No module named 'backend.core'`。

- [ ] **Step 3: 创建配置版本常量与加载器**

创建空的 `backend/core/__init__.py`，并创建 `backend/core/versions.py`：

```python
CONFIG_SCHEMA_VERSION = 1
NOT_IMPORTED_VERSION = "NOT-IMPORTED"
NOT_IMPORTED_STATUS = "not_imported"
FORMAL_READY_STATUS = "ready"
```

创建 `backend/core/configuration.py`：

```python
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from .versions import FORMAL_READY_STATUS, NOT_IMPORTED_VERSION


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "config" / "manifest.yaml"
REQUIRED_FIELDS = ("schema_version", "config_id", "version", "status")


class ConfigurationError(RuntimeError):
    pass


class ConfigurationParseError(ConfigurationError):
    pass


class ConfigurationNotFound(ConfigurationError):
    pass


class ConfigurationVersionError(ConfigurationError):
    pass


class ConfigurationHashMismatch(ConfigurationError):
    pass


class FormalConfigurationUnavailable(ConfigurationError):
    pass


def sha256_file(path: Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def load_config(path: Path) -> dict[str, Any]:
    path = Path(path)
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationNotFound(f"配置文件不存在: {path.name}") from exc
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ConfigurationParseError(f"无法读取配置 {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigurationParseError(f"配置 {path.name} 的根节点必须是映射")
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ConfigurationParseError(f"配置 {path.name} 缺少字段: {', '.join(missing)}")
    if not isinstance(payload["version"], str) or not payload["version"].strip():
        raise ConfigurationVersionError(f"配置 {path.name} 的 version 不能为空")
    return payload


def require_formal_config(path: Path) -> dict[str, Any]:
    path = Path(path)
    payload = load_config(path)
    status = payload["status"]
    version = payload["version"]
    if status != FORMAL_READY_STATUS or version == NOT_IMPORTED_VERSION:
        raise FormalConfigurationUnavailable(
            f"配置 {path.name} 当前状态为 {status}，版本为 {version}，不能用于 formal 模式"
        )

    manifest = load_config(MANIFEST_PATH)
    entry = next(
        (item for item in manifest.get("configs", []) if item.get("config_id") == payload["config_id"]),
        None,
    )
    if not entry or not entry.get("sha256"):
        raise FormalConfigurationUnavailable(
            f"配置 {payload['config_id']} 未在 manifest 中登记有效 SHA256"
        )
    if entry.get("status") != FORMAL_READY_STATUS or entry.get("version") != version:
        raise FormalConfigurationUnavailable(
            f"配置 {payload['config_id']} 与 manifest 的 status/version 不一致"
        )
    actual = sha256_file(path)
    expected = entry["sha256"]
    if actual != expected:
        raise ConfigurationHashMismatch(
            f"配置 {payload['config_id']} SHA256 不一致: expected={expected}, actual={actual}"
        )
    return payload
```

- [ ] **Step 4: 创建配置 manifest 和七个明确缺失的配置骨架**

创建 `config/manifest.yaml`：

```yaml
schema_version: 1
config_id: CONFIG-MANIFEST
version: PHASE0
status: ready
source: phase0_safety_net
configs:
  - {config_id: SPORT-SCORE-CONFIG, path: config/sportscore.yaml, version: NOT-IMPORTED, status: not_imported, sha256: null}
  - {config_id: SPORT-SHARE-CONFIG, path: config/sportshare.yaml, version: NOT-IMPORTED, status: not_imported, sha256: null}
  - {config_id: SPORTS-BUSINESS-DICTIONARY, path: config/sports_business_dictionary.yaml, version: NOT-IMPORTED, status: not_imported, sha256: null}
  - {config_id: INDUSTRY-CODE-MAP, path: config/industry_code_map.yaml, version: NOT-IMPORTED, status: not_imported, sha256: null}
  - {config_id: EVIDENCE-CALIBRATION, path: config/evidence_calibration.yaml, version: NOT-IMPORTED, status: not_imported, sha256: null}
  - {config_id: OFFICIAL-STRUCTURE-2022, path: config/official_structure_2022.yaml, version: NOT-IMPORTED, status: not_imported, sha256: null}
  - {config_id: SCALE-SCENARIOS, path: config/scale_scenarios.yaml, version: NOT-IMPORTED, status: not_imported, sha256: null}
```

创建下列文件，内容分别如下：

```yaml
# config/sportscore.yaml
schema_version: 1
config_id: SPORT-SCORE-CONFIG
version: NOT-IMPORTED
status: not_imported
source: report_alignment_migration
```

```yaml
# config/sportshare.yaml
schema_version: 1
config_id: SPORT-SHARE-CONFIG
version: NOT-IMPORTED
status: not_imported
source: report_alignment_migration
```

```yaml
# config/sports_business_dictionary.yaml
schema_version: 1
config_id: SPORTS-BUSINESS-DICTIONARY
version: NOT-IMPORTED
status: not_imported
source: report_alignment_migration
terms: []
```

```yaml
# config/industry_code_map.yaml
schema_version: 1
config_id: INDUSTRY-CODE-MAP
version: NOT-IMPORTED
status: not_imported
source: report_alignment_migration
codes: []
```

```yaml
# config/evidence_calibration.yaml
schema_version: 1
config_id: EVIDENCE-CALIBRATION
version: NOT-IMPORTED
status: not_imported
source: report_alignment_migration
profiles: []
```

```yaml
# config/official_structure_2022.yaml
schema_version: 1
config_id: OFFICIAL-STRUCTURE-2022
version: NOT-IMPORTED
status: not_imported
source: report_alignment_migration
reference_year: 2022
official_total_output_100m_cny: null
categories: []
```

```yaml
# config/scale_scenarios.yaml
schema_version: 1
config_id: SCALE-SCENARIOS
version: NOT-IMPORTED
status: not_imported
source: report_alignment_migration
alphas: []
evidence_profiles: []
```

- [ ] **Step 5: 运行配置测试和静态检查**

Run:

```powershell
uv run pytest tests/unit/test_configuration.py -v
uv run ruff check backend/core tests/unit/test_configuration.py
```

Expected: 7 tests passed；ruff 退出码 0。

- [ ] **Step 6: 提交配置边界**

```powershell
git add backend/core config tests/unit/test_configuration.py
git commit -m "feat: add versioned configuration boundary"
```

---

### Task 3: 锁定报告 Golden 契约和正式产物门禁

**Files:**
- Create: `tests/fixtures/expected_formal_metrics.json`
- Create: `tests/golden/__init__.py`
- Create: `tests/golden/test_golden_contract.py`
- Create: `tests/golden/test_formal_artifact.py`
- Create: `tests/unit/test_forbidden_patterns.py`

**Interfaces:**
- Consumes: 报告锁定数字；Task 1 的 `formal_artifact` marker；Task 2 的 `sha256_file`。
- Produces: 自洽的 Golden fixture、正式产物缺失清单、未来算法目录的硬编码扫描。

- [ ] **Step 1: 创建正式指标 fixture**

创建 `tests/fixtures/expected_formal_metrics.json`：

```json
{
  "batch_number": "BATCH-20260803-R1",
  "boundary": {
    "total_enterprises": 76687,
    "traditional_count": 8016,
    "fusion_count": 8950,
    "intersection": 7999,
    "only_fusion": 951,
    "only_traditional": 17,
    "net_increase": 934,
    "net_increase_rate": 0.1165,
    "crossover_count": 977,
    "candidate_coverage_rate": 0.1167
  },
  "evidence_groups": {
    "code_text_consistent": 4161,
    "code_only": 2730,
    "code_text_mismatch": 1181,
    "text_incremental": 878
  },
  "sportshare_sources": {
    "model_estimated": 6220,
    "hierarchical_fallback": 2730
  },
  "validation": {
    "binary": {"accuracy": 0.9544, "precision": 0.9403, "recall": 0.9947, "f1": 0.9668},
    "category": {"accuracy": 0.9293, "macro_f1": 0.8671},
    "sportshare": {"mae": 0.0125, "rmse": 0.0485, "r2": 0.9618, "spearman": 0.8476},
    "reference_labels": {"total": 300, "sport": 190, "non_sport": 95, "insufficient": 15},
    "binary_evaluable": 285,
    "category_evaluable": 184,
    "audit": {"passed": 24, "total": 24}
  },
  "scale": {
    "official_total_100m_cny": 2170.80,
    "baseline_alpha": 0.20,
    "category_scale_100m_cny": {
      "体育用品": 655.94,
      "健身休闲": 649.40,
      "体育培训": 230.91,
      "体育赛事": 225.48,
      "体育场馆": 198.47,
      "体育管理": 145.41,
      "体育传媒": 59.09,
      "电子竞技": 5.97,
      "体育彩票": 0.13
    },
    "boundary_in_100m_cny": 1978.86,
    "boundary_out_100m_cny": 191.94,
    "boundary_out_share": 0.0884,
    "chengdu_100m_cny": 1225.53,
    "chengdu_share": 0.5646,
    "mapped_enterprises": 8908,
    "unresolved_enterprises": 42,
    "scenario_count": 12,
    "boundary_out_scenario_min_100m_cny": 138.19,
    "boundary_out_scenario_max_100m_cny": 228.45
  },
  "review_priority": {"P1": 2735, "P2": 1122, "P3": 1067, "P4": 4026}
}
```

- [ ] **Step 2: 写 Golden 内部一致性测试**

创建空的 `tests/golden/__init__.py`，并创建 `tests/golden/test_golden_contract.py`：

```python
import json
from pathlib import Path

import pytest


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "expected_formal_metrics.json"


@pytest.fixture(scope="module")
def expected():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_boundary_set_arithmetic_distinguishes_951_934_and_977(expected):
    boundary = expected["boundary"]
    assert boundary["intersection"] + boundary["only_fusion"] == boundary["fusion_count"]
    assert boundary["intersection"] + boundary["only_traditional"] == boundary["traditional_count"]
    assert boundary["fusion_count"] - boundary["traditional_count"] == boundary["net_increase"]
    assert len({boundary["only_fusion"], boundary["net_increase"], boundary["crossover_count"]}) == 3
    assert boundary["net_increase_rate"] == pytest.approx(
        boundary["net_increase"] / boundary["traditional_count"], abs=1e-4
    )


def test_evidence_and_sportshare_sources_cover_all_candidates(expected):
    assert sum(expected["evidence_groups"].values()) == expected["boundary"]["fusion_count"]
    assert sum(expected["sportshare_sources"].values()) == expected["boundary"]["fusion_count"]


def test_reference_label_denominators_are_explicit(expected):
    labels = expected["validation"]["reference_labels"]
    assert labels["sport"] + labels["non_sport"] + labels["insufficient"] == labels["total"]
    assert labels["sport"] + labels["non_sport"] == expected["validation"]["binary_evaluable"]


def test_scale_totals_and_scenario_bounds_are_consistent(expected):
    scale = expected["scale"]
    total = scale["official_total_100m_cny"]
    assert sum(scale["category_scale_100m_cny"].values()) == pytest.approx(total, abs=0.02)
    assert scale["boundary_in_100m_cny"] + scale["boundary_out_100m_cny"] == pytest.approx(
        total, abs=0.02
    )
    assert scale["mapped_enterprises"] + scale["unresolved_enterprises"] == expected["boundary"][
        "fusion_count"
    ]
    assert scale["boundary_out_scenario_min_100m_cny"] < scale["boundary_out_100m_cny"]
    assert scale["boundary_out_100m_cny"] < scale["boundary_out_scenario_max_100m_cny"]


def test_review_priority_covers_candidates_and_p1_p2_rate(expected):
    priority = expected["review_priority"]
    assert sum(priority.values()) == expected["boundary"]["fusion_count"]
    assert priority["P1"] + priority["P2"] == 3857
    assert (priority["P1"] + priority["P2"]) / expected["boundary"][
        "total_enterprises"
    ] == pytest.approx(0.0503, abs=1e-4)
```

- [ ] **Step 3: 运行 Golden 契约测试**

Run:

```powershell
uv run pytest tests/golden/test_golden_contract.py -v
```

Expected: 5 tests passed。若类别规模求和超出 0.02，先核对 fixture 抄录，不修改容差掩盖错误。

- [ ] **Step 4: 写 formal artifact 门禁测试**

创建 `tests/golden/test_formal_artifact.py`：

```python
import csv
import json
from pathlib import Path

import pytest

from backend.core.configuration import sha256_file


ROOT = Path(__file__).resolve().parents[2]
EXPECTED = json.loads(
    (ROOT / "tests" / "fixtures" / "expected_formal_metrics.json").read_text(encoding="utf-8")
)
ARTIFACT_ROOT = ROOT / "artifacts" / "formal" / EXPECTED["batch_number"]
REQUIRED = (
    "batch_metadata.json",
    "input_manifest.json",
    "recognition/recognition_summary.json",
    "recognition/evidence_group_summary.json",
    "sportshare/sportshare_summary.json",
    "scale/category_scale.csv",
    "scale/region_scale.csv",
    "scale/boundary_scale.json",
    "scale/scenarios.csv",
    "validation/binary_metrics.json",
    "validation/category_metrics.json",
    "validation/sportshare_cv.json",
    "audit/audit_checks.json",
    "SHA256SUMS",
)


def require_artifacts():
    missing = [relative for relative in REQUIRED if not (ARTIFACT_ROOT / relative).is_file()]
    if missing:
        pytest.skip("missing formal artifacts: " + ", ".join(missing))


def read_json(relative: str) -> dict:
    return json.loads((ARTIFACT_ROOT / relative).read_text(encoding="utf-8"))


def read_csv(relative: str) -> list[dict]:
    with (ARTIFACT_ROOT / relative).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


@pytest.mark.formal_artifact
def test_locked_formal_artifact_matches_golden_contract():
    require_artifacts()
    boundary = EXPECTED["boundary"]
    recognition = read_json("recognition/recognition_summary.json")
    evidence = read_json("recognition/evidence_group_summary.json")
    share = read_json("sportshare/sportshare_summary.json")
    scale = EXPECTED["scale"]
    boundary_scale = read_json("scale/boundary_scale.json")
    categories = read_csv("scale/category_scale.csv")
    regions = read_csv("scale/region_scale.csv")
    scenarios = read_csv("scale/scenarios.csv")
    binary = read_json("validation/binary_metrics.json")
    category = read_json("validation/category_metrics.json")
    share_cv = read_json("validation/sportshare_cv.json")
    audit = read_json("audit/audit_checks.json")

    for key in (
        "total_enterprises",
        "traditional_count",
        "fusion_count",
        "intersection",
        "only_fusion",
        "only_traditional",
        "net_increase",
        "crossover_count",
    ):
        assert recognition[key] == boundary[key]
    assert sum(evidence.values()) == boundary["fusion_count"]
    assert share["model_estimated"] == EXPECTED["sportshare_sources"]["model_estimated"]
    assert share["hierarchical_fallback"] == EXPECTED["sportshare_sources"]["hierarchical_fallback"]
    assert float(boundary_scale["boundary_in_100m_cny"]) == pytest.approx(
        scale["boundary_in_100m_cny"], abs=0.02
    )
    assert float(boundary_scale["boundary_out_100m_cny"]) == pytest.approx(
        scale["boundary_out_100m_cny"], abs=0.02
    )
    assert sum(float(row["scale_100m_cny"]) for row in categories) == pytest.approx(
        scale["official_total_100m_cny"], abs=0.02
    )
    assert sum(float(row["scale_100m_cny"]) for row in regions) == pytest.approx(
        scale["official_total_100m_cny"], abs=0.02
    )
    assert len(scenarios) == scale["scenario_count"]
    assert all(
        float(row["total_output_100m_cny"])
        == pytest.approx(scale["official_total_100m_cny"], abs=0.02)
        for row in scenarios
    )
    assert binary["f1"] == pytest.approx(EXPECTED["validation"]["binary"]["f1"], abs=1e-4)
    assert category["macro_f1"] == pytest.approx(
        EXPECTED["validation"]["category"]["macro_f1"], abs=1e-4
    )
    assert share_cv["r2"] == pytest.approx(
        EXPECTED["validation"]["sportshare"]["r2"], abs=1e-4
    )
    assert sum(item["status"] == "PASS" for item in audit["checks"]) == 24


@pytest.mark.formal_artifact
def test_sha256_manifest_covers_every_formal_file():
    require_artifacts()
    entries = {}
    for line in (ARTIFACT_ROOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split(maxsplit=1)
        entries[relative.lstrip("* ")] = digest
    for relative in REQUIRED[:-1]:
        assert entries[relative] == sha256_file(ARTIFACT_ROOT / relative)
```

- [ ] **Step 5: 写新算法目录的硬编码策略测试**

创建 `tests/unit/test_forbidden_patterns.py`：

```python
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ALGORITHM_ROOTS = (ROOT / "backend" / "domain", ROOT / "analysis")
FORBIDDEN = {
    "golden literal": re.compile(r"(?<![\d.])(8950|8016|191\.94|2170\.80)(?![\d.])"),
    "batch-specific return": re.compile(r"BATCH-20260803-R1.{0,120}return", re.DOTALL),
    "formal demo fallback": re.compile(r"formal.{0,120}(fallback|回退).{0,80}demo", re.IGNORECASE | re.DOTALL),
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
```

- [ ] **Step 6: 验证缺产物时明确跳过且策略测试通过**

Run:

```powershell
uv run pytest tests/golden tests/unit/test_forbidden_patterns.py -v
```

Expected: 6 passed, 2 skipped；skip 原因逐项列出缺失 formal artifact。

- [ ] **Step 7: 提交 Golden 安全网**

```powershell
git add tests/fixtures tests/golden tests/unit/test_forbidden_patterns.py
git commit -m "test: lock formal report contracts"
```

---

### Task 4: 建立 FastAPI 现状回归和已知故障记录

**Files:**
- Modify: `tests/conftest.py`
- Create: `tests/api/__init__.py`
- Create: `tests/api/test_api_smoke.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_database_metadata.py`

**Interfaces:**
- Consumes: 当前 `backend/main.py` 路由；当前 SQLAlchemy `Base.metadata`。
- Produces: session 级 `app` fixture、`client` fixture、外部网络阻断；路由和数据库结构基线。

- [ ] **Step 1: 扩展 pytest 入口并加入网络阻断 fixture**

将 `tests/conftest.py` 替换为以下完整内容：

```python
import socket
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture(scope="session")
def app():
    from main import app as fastapi_app

    return fastapi_app


@pytest.fixture()
def client(app):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch):
    def blocked_connect(sock, address):
        raise AssertionError(f"tests must not access external network: {address}")

    monkeypatch.setattr(socket.socket, "connect", blocked_connect)
```

创建空的 `tests/api/__init__.py` 和 `tests/integration/__init__.py`。

- [ ] **Step 2: 写 API smoke tests**

创建 `tests/api/test_api_smoke.py`：

```python
import pytest


EXPECTED_PATHS = {
    "/api/data/upload",
    "/api/recognition/single",
    "/api/measure/single",
    "/api/chart/dashboard",
    "/api/validate/summary",
    "/api/monitoring/overview",
    "/api/assistant/stream",
    "/api/share/estimate",
    "/api/scale/summary",
    "/api/review/tasks",
    "/api/system/batches",
}


def test_application_registers_current_route_surface(app):
    registered = {route.path for route in app.routes}
    assert EXPECTED_PATHS <= registered


def test_root_and_read_only_smoke_endpoints_return_structured_responses(client):
    root = client.get("/")
    categories = client.get("/api/recognition/categories")
    monitoring = client.get("/api/monitoring/overview")
    assert root.status_code == 200
    assert root.json()["docs"] == "/docs"
    assert categories.status_code == 200
    assert isinstance(categories.json()["data"], list)
    assert monitoring.status_code == 200
    assert monitoring.json()["code"] == 200


@pytest.mark.xfail(
    strict=True,
    reason="P0-07: validate summary accesses comparison['traditional_detailed'], which service omits",
)
def test_validate_summary_does_not_crash_when_preprocessed_data_exists(client):
    from routers.data_preprocess import _preprocess_results

    file_id = 990001
    _preprocess_results[file_id] = {
        "records": [
            {"详细名称": "测试体育企业", "行业代码": "8911", "主要业务活动": "体育赛事组织"}
        ]
    }
    try:
        response = client.get(f"/api/validate/summary?file_id={file_id}")
    finally:
        _preprocess_results.pop(file_id, None)
    assert response.status_code != 500
```

- [ ] **Step 3: 写空数据库 metadata 测试**

创建 `tests/integration/test_database_metadata.py`：

```python
from sqlalchemy import create_engine, inspect


EXPECTED_TABLES = {
    "enterprises",
    "enterprise_businesses",
    "measurements",
    "data_sources",
    "model_metrics",
    "batches",
    "recognition_results_v2",
    "sport_share_results",
    "enterprise_scales",
    "regional_scale_results",
    "review_tasks",
    "review_records",
    "arbitration_records",
    "operation_logs",
}


def test_current_orm_metadata_creates_expected_tables(tmp_path):
    from models import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'metadata.db'}")
    Base.metadata.create_all(engine)
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())
```

- [ ] **Step 4: 运行 smoke tests，确认已知故障是严格 xfail**

Run:

```powershell
uv run pytest tests/api tests/integration backend/tests -v
```

Expected: 7 passed, 1 xfailed。若 P0-07 意外转为 XPASS，先确认业务代码是否被其他变更修改；Phase 0 不在此任务修复算法验证链。

- [ ] **Step 5: 提交现状回归测试**

```powershell
git add tests/conftest.py tests/api tests/integration
git commit -m "test: capture legacy api and schema baseline"
```

---

### Task 5: 建立 Alembic 当前结构基线和迁移说明

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/1d865fc0001_current_schema_baseline.py`
- Create: `tests/integration/test_alembic_baseline.py`
- Create: `MIGRATION_BASELINE.md`

**Interfaces:**
- Consumes: 当前 `models.database.Base.metadata` 和 `backend/sports_industry.db` 的只读副本。
- Produces: revision `1d865fc0001`；空库 `upgrade head`；现有数据库副本 `stamp head`；后续迁移以该 revision 为父节点。

- [ ] **Step 1: 写 Alembic 安全测试**

创建 `tests/integration/test_alembic_baseline.py`：

```python
import shutil
import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_DB = (ROOT / "backend" / "sports_industry.db").resolve()


def alembic_config(db_path: Path) -> Config:
    resolved = db_path.resolve()
    assert resolved != PRODUCTION_DB, "migration tests cannot target the workspace database"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{resolved.as_posix()}")
    return config


def business_row_counts(db_path: Path) -> dict[str, int]:
    with sqlite3.connect(db_path) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name != 'alembic_version'"
            )
        ]
        return {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in tables
        }


def test_empty_database_upgrades_to_current_schema(tmp_path):
    db_path = tmp_path / "empty.db"
    command.upgrade(alembic_config(db_path), "head")
    tables = set(inspect(create_engine(f"sqlite:///{db_path}")).get_table_names())
    assert "enterprises" in tables
    assert "operation_logs" in tables
    assert "alembic_version" in tables


def test_existing_database_copy_can_be_stamped_without_changing_business_rows(tmp_path):
    copied = tmp_path / "existing.db"
    shutil.copy2(PRODUCTION_DB, copied)
    before = business_row_counts(copied)
    command.stamp(alembic_config(copied), "head")
    after = business_row_counts(copied)
    assert after == before
    engine = create_engine(f"sqlite:///{copied}")
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert revision == "1d865fc0001"
```

- [ ] **Step 2: 运行测试，确认缺少 Alembic 配置**

Run:

```powershell
uv run pytest tests/integration/test_alembic_baseline.py -v
```

Expected: FAIL，错误表明 `alembic.ini` 或 revision 不存在。

- [ ] **Step 3: 初始化 Alembic 配置**

Run:

```powershell
uv run alembic init alembic
```

然后将 `alembic.ini` 的数据库 URL 设置为只用于开发默认值：

```ini
sqlalchemy.url = sqlite:///./backend/sports_industry.db
```

将 `alembic/env.py` 的 metadata 和 URL 部分改为：

```python
from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

x_arguments = context.get_x_argument(as_dictionary=True)
if x_arguments.get("database_url"):
    config.set_main_option("sqlalchemy.url", x_arguments["database_url"])

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from models import Base  # noqa: E402
import models.tables  # noqa: E402,F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: 用空数据库自动生成可追溯 baseline revision**

Run:

```powershell
$env:SPORTFUSION_MIGRATION_DB = (New-TemporaryFile).FullName
uv run alembic -x database_url="sqlite:///$($env:SPORTFUSION_MIGRATION_DB -replace '\\','/')" revision --autogenerate --rev-id 1d865fc0001 -m "current schema baseline"
```

Expected: 生成 `alembic/versions/1d865fc0001_current_schema_baseline.py`，upgrade 创建 14 张业务表，不含 Phase 1 未来字段。

- [ ] **Step 5: 创建迁移基线说明**

创建 `MIGRATION_BASELINE.md`，内容必须包含以下确定信息：

```markdown
# SportFusion Migration Baseline

- Business baseline: `master@1d865fc4cd9dbb78cf355b19345fb44c16edd46e`
- Safety-net design: `6e13f2f`
- Alembic revision: `1d865fc0001`
- Database: SQLite, workspace runtime file `backend/sports_industry.db`

## Current tables

`enterprises`, `enterprise_businesses`, `measurements`, `data_sources`,
`model_metrics`, `batches`, `recognition_results_v2`, `sport_share_results`,
`enterprise_scales`, `regional_scale_results`, `review_tasks`, `review_records`,
`arbitration_records`, `operation_logs`.

## Known semantic debt

- `enterprise_businesses.sport_revenue_ratio` and `measurements.sport_ratio` use legacy ratio language.
- `recognition_results_v2.sport_score` exists, while API schemas still expose ambiguous `sport_ratio`.
- `sport_share_results.model_share` currently reuses the legacy recognition score.
- `enterprise_scales.sport_scale` stores the legacy enterprise financial-proxy result.
- Batch locking, review history, scale scenarios, evaluation runs and audit checks are incomplete.

## Migration ownership

- Phase 1 separates SportScore from legacy `sport_ratio`.
- Phase 2 versions the dictionary and industry-code map.
- Phase 3 adds immutable SportShare model outputs and fallback provenance.
- Phase 4 adds scale runs, scenarios and constrained aggregate results.
- Phase 5 adds evaluation and audit runs.
- Phase 6 persists batch locking and review workflow.
- Phase 7 changes monitoring, charts and exports to read locked artifacts.
- Phase 8 removes legacy columns after the compatibility window.

## Safe commands

Create a new database: `uv run alembic upgrade head` with a temporary or new database URL.
Register an existing database: copy it first, verify table counts, then run `uv run alembic stamp head` on the copy.
Never run destructive migration experiments against `backend/sports_industry.db`.
```

- [ ] **Step 6: 运行 Alembic 和 metadata 测试**

Run:

```powershell
uv run pytest tests/integration/test_database_metadata.py tests/integration/test_alembic_baseline.py -v
uv run alembic history
```

Expected: 3 tests passed；history 显示 `1d865fc0001 (head)`。

- [ ] **Step 7: 提交数据库基线**

```powershell
git add alembic.ini alembic MIGRATION_BASELINE.md tests/integration/test_alembic_baseline.py
git commit -m "chore: establish alembic schema baseline"
```

---

### Task 6: 建立 CI 并完成 Phase 0 总验收

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `docs/superpowers/plans/2026-08-08-sportfusion-phase0-safety-net.md`（只勾选已完成步骤）

**Interfaces:**
- Consumes: Tasks 1–5 的 uv lock、pytest、配置、Golden 测试和 Alembic revision；前端现有 package lock 与测试。
- Produces: 无密钥、无正式数据、无外部大模型依赖的 CI；Phase 0 完成证据。

- [ ] **Step 1: 创建 GitHub Actions workflow**

创建 `.github/workflows/ci.yml`：

```yaml
name: ci

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Install uv
        uses: astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0
        with:
          version: "0.11.32"
          enable-cache: true
      - name: Sync locked Python environment
        run: uv sync --locked --dev
      - name: Lint Phase 0 Python surfaces
        run: uv run ruff check backend/core tests alembic
      - name: Run backend and contract tests
        run: uv run pytest tests backend/tests -m "not formal_artifact"

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v6
        with:
          node-version: "24"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm test
      - run: npm run build
```

Action 版本依据 Astral 官方 uv GitHub 集成文档和 GitHub 官方 setup-node/checkout README；不要改回旧的 v4 action。

- [ ] **Step 2: 运行 Python 全量验收**

Run:

```powershell
uv sync --locked
uv run ruff check backend/core tests alembic
uv run pytest tests backend/tests -m "not formal_artifact" -v
uv run pytest tests/golden/test_formal_artifact.py -m formal_artifact -v
```

Expected:

- lint 退出码 0；
- 非 formal_artifact 测试全部通过，P0-07 恰好 1 项 xfailed；
- formal artifact 测试恰好 2 项 skipped，输出完整缺失文件清单；
- 没有外部网络访问。

- [ ] **Step 3: 运行前端回归与构建**

Run:

```powershell
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
```

Expected: 现有前端 17 项测试通过；Vite production build 退出码 0。依赖包体积 warning 可以记录，但不能有编译错误。

- [ ] **Step 4: 验证兼容 requirements 和 Alembic**

Run:

```powershell
uv export --locked --no-dev --format requirements-txt --no-hashes --output-file "$env:TEMP\sportfusion-requirements.txt"
Compare-Object (Get-Content backend/requirements.txt) (Get-Content "$env:TEMP\sportfusion-requirements.txt")
uv run alembic history
```

Expected: `Compare-Object` 无输出；Alembic history 显示 `1d865fc0001 (head)`。

- [ ] **Step 5: 验证 Phase 0 没有修改业务算法或 Vue 页面**

Run:

```powershell
$forbidden = git diff --name-only 6e13f2f..HEAD | Select-String -Pattern '^backend/services/(sport_recognition|sport_share_service|scale_measure_service|model_validate)\.py$|^frontend/src/views/'
if ($forbidden) { $forbidden; exit 1 }
Write-Output 'phase0-scope-check: clean'
```

Expected: `phase0-scope-check: clean`。

- [ ] **Step 6: 提交 CI 与已完成计划状态**

```powershell
git add .github/workflows/ci.yml docs/superpowers/plans/2026-08-08-sportfusion-phase0-safety-net.md
git commit -m "ci: verify phase 0 safety net"
```

- [ ] **Step 7: 输出 Phase 0 交付摘要**

交付消息必须包含：

```text
1. 实际提交列表与每个提交的范围
2. 新增测试数量、通过数量、xfail 和 skip 原因
3. uv、ruff、Alembic、前端测试和 build 的实际退出结果
4. 受影响 API：无业务契约变化，仅新增 smoke tests
5. 数据状态：legacy batch 保留，formal artifacts 仍缺失
6. 迁移风险：歧义字段、现有 SQLite 漂移和后续 Phase 所有权
7. 明确说明没有修改算法、Vue 业务页面或生成虚假正式结果
```

---

## Plan self-review map

- 设计规格第 5 节依赖与运行方式：Task 1。
- 第 6 节测试设计：Tasks 3–4。
- 第 7 节配置与版本：Task 2。
- 第 8 节 Alembic 基线：Task 5。
- 第 9 节 CI：Task 6。
- 第 10 节错误处理：Tasks 2–5 的异常、skip、网络和数据库保护。
- 第 11 节验收标准：Task 6 全部命令。
- 第 12 节风险控制：`MIGRATION_BASELINE.md`、formal marker、strict xfail 和范围扫描。

## Authoritative tooling references

- Astral uv installation: https://docs.astral.sh/uv/getting-started/installation/
- Astral uv GitHub Actions integration: https://docs.astral.sh/uv/guides/integration/github/
- GitHub setup-node: https://github.com/actions/setup-node
- GitHub checkout: https://github.com/actions/checkout
