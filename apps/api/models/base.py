"""Declarative base shared by all ORM models.

Every table class in this package (Organizer, Campaign, Rule,
Submission, Hacker) inherits from Base. SQLAlchemy uses Base.metadata to
know the full set of tables that exist — that's what Alembic's
`alembic/env.py` points at when autogenerating migrations, and it's why
`models/__init__.py` must import every model module: a model that's
never imported never registers itself on Base.metadata.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
