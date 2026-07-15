from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

# See models/organizer.py for why these are TYPE_CHECKING-only imports.
if TYPE_CHECKING:
    from models.organizer import Organizer
    from models.rule import Rule
    from models.submission import Submission


class Campaign(Base):
    """A hackathon event whose submissions TruPitch evaluates.

    Hackers submit against a specific campaign (via
    POST /api/campaigns/{id}/submit); organizers configure one campaign
    per hackathon, including its judging rubric (the `rules` list) and
    the deterministic entry rules below (team size, submission limits,
    late-submission policy).
    """

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    organizer_id: Mapped[int] = mapped_column(
        ForeignKey("organizers.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    # Optional: when set, the frontend can show "starts on <date>" ahead
    # of the deadline; purely informational, not enforced server-side.
    start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Hard cutoff for submissions, enforced by routers/submissions.py
    # unless allow_late_submissions is true.
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # CampaignStatus values (core/constants.py): draft | open | evaluating | closed.
    # Only "open" campaigns accept new submissions.
    status: Mapped[str] = mapped_column(String(32), default="draft")
    # Deterministic (non-AI) entry rules, set by the organizer in the
    # Campaign Builder UI. These are currently informational/display-only
    # on the frontend; enforcing them server-side (e.g. rejecting a 5th
    # team member) is a natural next step, not yet implemented.
    max_team_size: Mapped[int] = mapped_column(Integer, default=4)
    max_submissions_per_team: Mapped[int] = mapped_column(Integer, default=1)
    allow_late_submissions: Mapped[bool] = mapped_column(Boolean, default=False)

    organizer: Mapped["Organizer"] = relationship(back_populates="campaigns")
    # cascade="all, delete-orphan" on both children below means deleting
    # a Campaign row also deletes every Rule and Submission that points
    # at it — there is no "orphaned rule/submission" state.
    rules: Mapped[list["Rule"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
