from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from schemas.rule import RuleCreate, RuleResponse


class CampaignCreate(BaseModel):

    name: str = Field(min_length=1, max_length=255)
    start_date: datetime | None = None
    deadline: datetime
    status: Literal["draft", "open"] = "draft"
    max_team_size: int = Field(default=4, ge=1)
    max_submissions_per_team: int = Field(default=1, ge=1)
    allow_late_submissions: bool = False
    rules: list[RuleCreate] = Field(default_factory=list)


class CampaignResponse(BaseModel):

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
    rules: list[RuleResponse]
