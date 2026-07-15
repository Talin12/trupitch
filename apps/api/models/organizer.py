from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

# Import Campaign only for type-checking, not at runtime: Campaign also
# imports Organizer (for its own relationship), and importing both
# eagerly at module load time would create a circular import. The
# string literal "Campaign" in the relationship() call below is resolved
# lazily by SQLAlchemy, so this works without ever needing the real class
# at import time.
if TYPE_CHECKING:
    from models.campaign import Campaign


class Organizer(Base):
    """A hackathon host account. One organizer owns many campaigns.

    There is currently no organizer authentication — campaigns created
    without an explicit organizer_id are attached to a single default
    organizer row (see core/config.py's admin_email/admin_name and
    routers/campaigns.py's _resolve_organizer).
    """

    __tablename__ = "organizers"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # One-to-many: deleting an organizer cascades and deletes all of
    # their campaigns (and, transitively, those campaigns' rules and
    # submissions — see Campaign's own cascade).
    campaigns: Mapped[list["Campaign"]] = relationship(
        back_populates="organizer", cascade="all, delete-orphan"
    )
