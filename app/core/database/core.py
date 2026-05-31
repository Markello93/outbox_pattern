from collections import abc

import sqlalchemy
from sqlalchemy.ext import asyncio
from sqlalchemy.orm import declarative_base

from app.core import settings


class Database:
    def __init__(self, config: settings.DatabaseSettings):
        self._db_dsn = config.dsn.unicode_string()
        self._engine = asyncio.create_async_engine(
            self._db_dsn,
            echo=False,
            pool_size=config.engine_pool_size,
            max_overflow=config.engine_max_overflow,
            pool_timeout=config.engine_pool_timeout,
            pool_pre_ping=config.engine_pool_ping,
        )
        self._session_local = asyncio.async_sessionmaker(bind=self._engine, expire_on_commit=False)

    async def get_session(self) -> abc.AsyncGenerator[asyncio.AsyncSession]:
        async with self._session_local() as session:
            yield session

    async def ping(self) -> None:
        async with self._engine.connect() as connection:
            await connection.execute(sqlalchemy.text("SELECT 1"))

    async def shutdown(self):
        await self._engine.dispose()


Base = declarative_base(
    metadata=sqlalchemy.MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    ),
)
