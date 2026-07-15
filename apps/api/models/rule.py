from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.campaign import Campaign


class Rule(Base):
    """A single weighted rubric criterion within a campaign.

    Example: description="Uses AI meaningfully, not as a gimmick",
    weight=2.0. The full set of a campaign's rules is sent to the LLM
    in Stage 3 of the worker pipeline (see
    apps/worker/pipeline/stage3_scoring.py), which scores each
    submission against them and returns a single weighted score.
    """

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str] = mapped_column(Text)
    # How much this rule counts relative to the campaign's other rules.
    # There's no enforced range or normalization — the LLM prompt just
    # includes each rule's raw weight and is instructed to weigh
    # accordingly (see stage3_scoring.py / clients/llm.py).
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    campaign: Mapped["Campaign"] = relationship(back_populates="rules")
