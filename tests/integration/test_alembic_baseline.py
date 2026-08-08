import shutil
import sqlite3
from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_DB = (ROOT.parents[1] / "backend" / "sports_industry.db").resolve()


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
    assert copied.resolve() != PRODUCTION_DB
    shutil.copy2(PRODUCTION_DB, copied)
    before = business_row_counts(copied)
    command.stamp(alembic_config(copied), "head")
    after = business_row_counts(copied)
    assert after == before
    engine = create_engine(f"sqlite:///{copied}")
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert revision == "1d865fc0001"
