"""Worker-side ORM mapping.

Deliberately minimal and independent from apps/api: the worker only
touches the columns it needs. The schema itself is owned by the API's
Alembic migrations — this file just describes enough of the same two
tables (submissions, rules) for the worker to read and update rows
directly against Postgres, without importing anything from apps/api.
"""

from sqlalchemy import Float, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Worker's own declarative base — separate from (but describing
    the same tables as) apps/api/models/base.Base."""

    pass


class Submission(Base):
    """Subset of apps/api/models/submission.Submission's columns: only
    the ones the pipeline in tasks.py actually reads or writes.
    hacker_id, created_at/updated_at, and the relationships aren't
    needed here and are intentionally omitted.
    """

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
    """Read-only from the worker's perspective: tasks.py loads a
    campaign's rules to build the LLM prompt in Stage 3, but never
    writes to this table.
    """

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int]
    description: Mapped[str] = mapped_column(Text)
    weight: Mapped[float] = mapped_column(Float)
