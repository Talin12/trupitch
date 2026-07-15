from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.campaign import Campaign
    from models.hacker import Hacker


class Submission(Base):
    """One hacker's project entry into one campaign.

    Created by POST /api/campaigns/{id}/submit with status=pending,
    then owned entirely by the worker's evaluate_submission task
    (apps/worker/tasks.py), which moves it through
    pending -> evaluating -> (evaluated | disqualified), filling in
    final_score and notes along the way. The API only ever reads these
    fields back out (leaderboard, polling, WebSocket) — it never writes
    status/final_score/notes itself once the submission is queued.
    """

    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    # Nullable: submissions predating GitHub OAuth have no linked hacker.
    # ondelete="SET NULL" (rather than CASCADE) so deleting a Hacker
    # account doesn't destroy the submissions they made — it just
    # detaches them.
    hacker_id: Mapped[int | None] = mapped_column(
        ForeignKey("hackers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    team_name: Mapped[str] = mapped_column(String(255))
    # The specific repo the hacker picked from their GitHub account,
    # verified server-side (routers/submissions.py) to belong to them
    # before this row is even created.
    github_url: Mapped[str] = mapped_column(String(512))
    pitch_text: Mapped[str] = mapped_column(Text)
    # SubmissionStatus values (core/constants.py):
    # pending | evaluating | evaluated | disqualified.
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    # Final weighted score (0-100) from Stage 3; stays None until the
    # pipeline reaches "evaluated" (or forever, if disqualified in Stage 1).
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Evaluation feedback or disqualification reason. For an evaluated
    # submission this is "<Stage 2 tech summary> | <Stage 3 rationale>"
    # (see apps/worker/tasks.py); for a disqualified one it's just the
    # Stage 1 failure reason.
    notes: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Bumped automatically by Postgres (via onupdate) every time any
    # column on this row changes — used by the dashboard to show a
    # "last updated" timestamp per submission.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="submissions")
    hacker: Mapped["Hacker | None"] = relationship(back_populates="submissions")
