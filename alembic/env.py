import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from alembic import context

EXPLICIT_DATABASE_URL_REQUIRED = "__SPORTFUSION_EXPLICIT_DATABASE_URL_REQUIRED__"

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

x_arguments = context.get_x_argument(as_dictionary=True)
if x_arguments.get("database_url"):
    config.set_main_option("sqlalchemy.url", x_arguments["database_url"])

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def _protected_runtime_databases() -> set[Path]:
    protected = {(BACKEND / "sports_industry.db").resolve()}
    if ROOT.parent.name == ".worktrees":
        protected.add((ROOT.parent.parent / "backend" / "sports_industry.db").resolve())
    return protected


def _validated_database_url() -> str:
    database_url = config.get_main_option("sqlalchemy.url")
    if not database_url or database_url == EXPLICIT_DATABASE_URL_REQUIRED:
        raise RuntimeError(
            "Alembic requires an explicit database target: pass "
            "-x database_url=<url> or set sqlalchemy.url on the Config object."
        )

    try:
        url = make_url(database_url)
    except ArgumentError as exc:
        raise RuntimeError("Alembic database target is not a valid SQLAlchemy URL.") from exc

    if url.get_backend_name() != "sqlite" or url.database in {None, "", ":memory:"}:
        return database_url

    if "uri" in url.query:
        raise RuntimeError(
            "SQLite URI targets are not supported; use an explicit filesystem path "
            "to a temporary/copy database."
        )

    database_path = Path(url.database).expanduser()
    if not database_path.is_absolute():
        database_path = Path.cwd() / database_path
    resolved_database_path = database_path.resolve()

    if resolved_database_path in _protected_runtime_databases():
        raise RuntimeError(
            "Alembic refuses to target a SportFusion runtime database; use a "
            "temporary/copy database outside the workspace runtime path."
        )

    return database_url


DATABASE_URL = _validated_database_url()

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import models.tables  # noqa: F401
from models import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
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
