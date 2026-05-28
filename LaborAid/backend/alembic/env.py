from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Import all models so Alembic can detect them and resolve the correct URL.
# ---------------------------------------------------------------------------
from app.core.database import Base
import app.models  # noqa: F401 — register all models
target_metadata = Base.metadata

# Resolve the database URL from the app's own settings so that `alembic`
# upgrade/downgrade works without manually editing alembic.ini.
try:
    from app.config import get_settings
    _settings = get_settings()
    # Prefer the sync URL for Alembic (it uses synchronous SQLAlchemy).
    _db_url = getattr(_settings, "DATABASE_URL_SYNC", None) or _settings.DATABASE_URL
    # Convert async driver to sync driver for Alembic if needed.
    _db_url = _db_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    config.set_main_option("sqlalchemy.url", _db_url)
except Exception:
    # Fall back to whatever is in alembic.ini.
    pass


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Compare types so ALTER COLUMN is emitted when column types change.
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
