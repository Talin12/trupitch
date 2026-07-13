from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.organizer import Organizer
    from models.rule import Rule
    from models.submission import Submission


class Campaign(Base):
    """A hackathon event whose submissions TruPitch evaluates."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    organizer_id: Mapped[int] = mapped_column(
        ForeignKey("organizers.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # draft | open | evaluating | closed
    status: Mapped[str] = mapped_column(String(32), default="draft")

    organizer: Mapped["Organizer"] = relationship(back_populates="campaigns")
    rules: Mapped[list["Rule"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
