import hashlib
import os
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command

ROOT = Path(__file__).resolve().parents[2]
WORKTREE_RUNTIME_DB = (ROOT / "backend" / "sports_industry.db").resolve()
MAIN_WORKSPACE_RUNTIME_DB = (
    (ROOT.parent.parent / "backend" / "sports_industry.db").resolve()
    if ROOT.parent.name == ".worktrees"
    else None
)
RUNTIME_DATABASES = [WORKTREE_RUNTIME_DB]
if MAIN_WORKSPACE_RUNTIME_DB is not None:
    RUNTIME_DATABASES.append(MAIN_WORKSPACE_RUNTIME_DB)

EXPECTED_TABLES = {
    "arbitration_records",
    "batches",
    "data_sources",
    "enterprise_businesses",
    "enterprise_scales",
    "enterprises",
    "measurements",
    "model_metrics",
    "operation_logs",
    "recognition_results_v2",
    "regional_scale_results",
    "review_records",
    "review_tasks",
    "sport_share_results",
}


def alembic_config(db_path: Path) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.resolve().as_posix()}")
    return config


def default_alembic_config() -> Config:
    return Config(str(ROOT / "alembic.ini"))


def relative_sqlite_config(db_path: Path) -> Config:
    relative = Path(os.path.relpath(db_path, Path.cwd())).as_posix()
    config = default_alembic_config()
    config.set_main_option("sqlalchemy.url", f"sqlite:///{relative}")
    return config


def file_fingerprint(path: Path) -> tuple[bool, int | None, int | None, str | None]:
    if not path.exists():
        return False, None, None, None
    stat = path.stat()
    return True, stat.st_size, stat.st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest()


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


def test_default_config_fails_without_touching_runtime_databases():
    before = {path: file_fingerprint(path) for path in RUNTIME_DATABASES}

    with pytest.raises(RuntimeError, match="explicit database target"):
        command.upgrade(default_alembic_config(), "head")

    assert {path: file_fingerprint(path) for path in RUNTIME_DATABASES} == before


@pytest.mark.parametrize("sql_mode", [False, True], ids=["online", "offline"])
@pytest.mark.parametrize("runtime_db", RUNTIME_DATABASES, ids=lambda path: str(path))
def test_explicit_runtime_database_paths_are_rejected_without_writes(runtime_db, sql_mode):
    before = file_fingerprint(runtime_db)

    with pytest.raises(RuntimeError, match="temporary/copy database"):
        command.upgrade(relative_sqlite_config(runtime_db), "head", sql=sql_mode)

    assert file_fingerprint(runtime_db) == before


def test_truthy_sqlite_uri_cannot_bypass_runtime_guard_in_offline_mode():
    before = file_fingerprint(WORKTREE_RUNTIME_DB)
    config = default_alembic_config()
    config.set_main_option(
        "sqlalchemy.url",
        f"sqlite:///file:{WORKTREE_RUNTIME_DB.as_posix()}?uri=1",
    )

    with pytest.raises(RuntimeError, match="temporary/copy database"):
        command.upgrade(config, "head", sql=True)

    assert file_fingerprint(WORKTREE_RUNTIME_DB) == before


def test_empty_database_upgrades_to_exact_current_schema(tmp_path):
    db_path = tmp_path / "empty.db"
    config = alembic_config(db_path)

    command.upgrade(config, "head")
    command.check(config)

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        assert set(inspect(engine).get_table_names()) == EXPECTED_TABLES | {"alembic_version"}
    finally:
        engine.dispose()


def test_temporary_copy_with_runtime_filename_is_allowed(tmp_path):
    copied_name = tmp_path / "copies" / "sports_industry.db"
    copied_name.parent.mkdir()

    command.upgrade(alembic_config(copied_name), "head")

    assert copied_name.is_file()


def test_seeded_current_schema_can_be_stamped_without_changing_business_rows(tmp_path):
    from models import Base

    copied = tmp_path / "legacy-current-schema.db"
    engine = create_engine(f"sqlite:///{copied}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            Base.metadata.tables["data_sources"].insert(),
            {"filename": "legacy-input.csv", "file_type": "csv", "row_count": 3},
        )
        connection.execute(
            Base.metadata.tables["model_metrics"].insert(),
            {"metric_name": "legacy_f1", "metric_value": 0.87},
        )
    engine.dispose()

    before = business_row_counts(copied)
    assert before["data_sources"] == 1
    assert before["model_metrics"] == 1

    config = alembic_config(copied)
    command.stamp(config, "head")

    assert business_row_counts(copied) == before
    stamped_engine = create_engine(f"sqlite:///{copied}")
    try:
        with stamped_engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
    finally:
        stamped_engine.dispose()
    assert revision == "1d865fc0001"
