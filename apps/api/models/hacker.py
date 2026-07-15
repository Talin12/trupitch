from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.submission import Submission


class Hacker(Base):
    """A participant identified via GitHub OAuth.

    Created/updated by routers/auth.py's OAuth callback: on first login
    a new row is inserted; on every subsequent login the existing row
    (matched by github_id) has its username and github_token refreshed.
    There is no separate password or local account — GitHub identity
    *is* the account.
    """

    __tablename__ = "hackers"

    id: Mapped[int] = mapped_column(primary_key=True)
    # GitHub's own numeric user id (as a string) — stable even if the
    # hacker later renames their GitHub account, which is why we key
    # lookups on this rather than on `username`.
    github_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255))
    # The GitHub OAuth access token for this hacker, used server-side
    # (routers/hacker.py, routers/submissions.py) to list their repos
    # and verify they have push access to the one they submit. Never
    # sent to the frontend — only our session JWT is.
    github_token: Mapped[str] = mapped_column(String(255))

    submissions: Mapped[list["Submission"]] = relationship(back_populates="hacker")
