"""Pydantic schemas for the Campaign API surface.

`*Create` schemas define what a client is allowed to send in a request
body — Pydantic validates and rejects anything that doesn't match before
the route handler ever runs. `*Response` schemas define what the API
sends back; `ConfigDict(from_attributes=True)` lets FastAPI build the
response directly from a SQLAlchemy ORM object's attributes (rather than
requiring a dict), which is what routers/campaigns.py relies on.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from schemas.rule import RuleCreate, RuleResponse


class CampaignCreate(BaseModel):
    """Body for POST /api/campaigns — creates a campaign and its rubric
    (list of rules) in one atomic request.
    """

    # Optional: when omitted the API resolves the default organizer
    # (settings.admin_email) until organizer auth exists.
    organizer_id: int | None = None
    name: str = Field(min_length=1, max_length=255)
    start_date: datetime | None = None
    deadline: datetime
    # Campaigns can only be created as draft or open — "evaluating" and
    # "closed" are states the system/organizer transitions a campaign
    # into later, not a starting state a client should be able to pick.
    status: Literal["draft", "open"] = "draft"
    max_team_size: int = Field(default=4, ge=1)
    max_submissions_per_team: int = Field(default=1, ge=1)
    allow_late_submissions: bool = False
    # Nested rule payloads; the router creates a Rule row for each one
    # in the same transaction as the Campaign itself.
    rules: list[RuleCreate] = Field(default_factory=list)


class CampaignResponse(BaseModel):
    """Shape returned by every campaign endpoint (create, get, list,
    and nested inside the leaderboard's submission responses isn't
    applicable, but campaigns.py's list/get routes return this directly).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    organizer_id: int
    name: str
    start_date: datetime | None
    deadline: datetime
    status: str
    max_team_size: int
    max_submissions_per_team: int
    allow_late_submissions: bool
    # Requires the ORM query to have eagerly loaded Campaign.rules
    # (selectinload) — otherwise accessing this attribute outside an
    # active session would raise a lazy-load error under asyncio.
    rules: list[RuleResponse]
