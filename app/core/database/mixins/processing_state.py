import datetime

import sqlalchemy
from sqlalchemy import orm


class ProcessingStateMixin:
    processed_at: orm.Mapped[datetime.datetime | None] = orm.mapped_column(sqlalchemy.DateTime, nullable=True)
    last_error: orm.Mapped[str | None] = orm.mapped_column(sqlalchemy.String, nullable=True)
