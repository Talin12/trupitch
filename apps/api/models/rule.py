from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.campaign import Campaign


class Rule(Base):
    """A single weighted rubric criterion within a campaign."""

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str] = mapped_column(Text)
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    campaign: Mapped["Campaign"] = relationship(back_populates="rules")
