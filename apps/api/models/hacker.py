from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.submission import Submission


class Hacker(Base):
    """A participant identified via GitHub OAuth."""

    __tablename__ = "hackers"

    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255))
    github_token: Mapped[str] = mapped_column(String(255))

    submissions: Mapped[list["Submission"]] = relationship(back_populates="hacker")
