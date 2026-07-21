from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.organizer import Organizer
    from models.rule import Rule
    from models.submission import Submission


class Campaign(Base):

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    organizer_id: Mapped[int] = mapped_column(
        ForeignKey("organizers.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    max_team_size: Mapped[int] = mapped_column(Integer, default=4)
    max_submissions_per_team: Mapped[int] = mapped_column(Integer, default=1)
    allow_late_submissions: Mapped[bool] = mapped_column(Boolean, default=False)

    organizer: Mapped["Organizer"] = relationship(back_populates="campaigns")
    rules: Mapped[list["Rule"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
