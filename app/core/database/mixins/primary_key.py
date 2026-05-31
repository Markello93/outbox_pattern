import uuid

import sqlalchemy
from sqlalchemy import orm


class PrimaryKeyMixin:
    id: orm.Mapped[uuid.UUID] = orm.mapped_column(
        sqlalchemy.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
