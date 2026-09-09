import os
from logging.config import fileConfig
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.core.database import Base
from app.model.models import *

config = context.config

# Diretórios do projeto
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"

# Define qual ambiente será utilizado
environment = os.getenv("DEVDELIVERY_ENV", "development")

if environment == "test":
    env_file = BACKEND_ROOT / ".env.test"
else:
    env_file = BACKEND_ROOT / ".env"

# Carrega o arquivo de ambiente
load_dotenv(env_file, override=True)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        f"DATABASE_URL não encontrada em: {env_file}"
    )

# Proteção contra migration acidental no banco de desenvolvimento
if environment == "test" and "devdelivery_test" not in DATABASE_URL:
    raise RuntimeError(
        "ABORTADO: ambiente de teste não está apontando para "
        "o banco 'devdelivery_test'."
    )

config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()