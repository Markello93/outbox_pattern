import asyncio

import pytest
import sqlalchemy

from app.core import database, settings


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config() -> settings.WorkersSettings:
    return settings.WorkersSettings()


@pytest.fixture(scope="session")
async def test_database(test_config: settings.WorkersSettings) -> database.Database:
    db = database.Database(config=test_config.database)
    yield db
    await db.shutdown()


@pytest.fixture(autouse=True)
async def cleanup_tables(test_database: database.Database) -> None:
    tables = ("outbox_events", "payments")
    async for session in test_database.get_session():
        for table in tables:
            await session.execute(sqlalchemy.text(f'TRUNCATE "{table}" CASCADE'))
        await session.commit()
