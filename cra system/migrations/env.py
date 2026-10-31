from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from cra_app.governance import models as governance_models  # noqa: E402,F401
from cra_app.documents import models as document_models  # noqa: E402,F401
from cra_app.edc_import import models as edc_import_models  # noqa: E402,F401
from cra_app.issues import models as issue_models  # noqa: E402,F401
from cra_app.laboratory import models as laboratory_models  # noqa: E402,F401
from cra_app.platform import jobs as platform_jobs  # noqa: E402,F401
from cra_app.rules import models as rule_models  # noqa: E402,F401
from cra_app.subjects import models as subject_models  # noqa: E402,F401
from cra_app.shared.config import get_settings  # noqa: E402
from cra_app.shared.db import Base  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(object_, name, type_, reflected, compare_to):
    """Procrastinate owns its tables and indexes, not the CRA metadata."""
    if type_ in {"table", "index"} and name and name.startswith("procrastinate_"):
        return False
    if (
        type_ == "index"
        and getattr(object_, "table", None) is not None
        and object_.table.name.startswith("procrastinate_")
    ):
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().sqlalchemy_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_settings().sqlalchemy_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
