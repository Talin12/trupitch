from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.campaign import Campaign
    from models.hacker import Hacker


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    # Nullable: submissions predating GitHub OAuth have no linked hacker.
    hacker_id: Mapped[int | None] = mapped_column(
        ForeignKey("hackers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    team_name: Mapped[str] = mapped_column(String(255))
    github_url: Mapped[str] = mapped_column(String(512))
    pitch_text: Mapped[str] = mapped_column(Text)
    # SubmissionStatus values (core/constants.py)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Evaluation feedback or disqualification reason.
    notes: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="submissions")
    hacker: Mapped["Hacker | None"] = relationship(back_populates="submissions")
