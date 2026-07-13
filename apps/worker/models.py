"""Worker-side ORM mapping.

Deliberately minimal and independent from apps/api: the worker only
touches the columns it needs. The schema itself is owned by the API's
Alembic migrations.
"""

from sqlalchemy import Float, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int]
    github_url: Mapped[str] = mapped_column(String(512))
    pitch_text: Mapped[str] = mapped_column(Text)
    # pending | evaluating | evaluated | disqualified
    status: Mapped[str] = mapped_column(String(32))
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1024), nullable=True)


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int]
    description: Mapped[str] = mapped_column(Text)
    weight: Mapped[float] = mapped_column(Float)
