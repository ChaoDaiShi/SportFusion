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
