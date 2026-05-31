import sqlalchemy

from app.core import database


async def get_one_or_none(test_database: database.Database, model, **filters):
    async for session in test_database.get_session():
        stmt = sqlalchemy.select(model).filter_by(**filters)
        result = await session.execute(stmt)
    return result.scalar_one_or_none()
