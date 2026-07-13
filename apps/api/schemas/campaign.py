from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from schemas.rule import RuleCreate, RuleResponse


class CampaignCreate(BaseModel):
    organizer_id: int
    name: str = Field(min_length=1, max_length=255)
    deadline: datetime
    status: Literal["draft", "open"] = "draft"
    rules: list[RuleCreate] = Field(default_factory=list)


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organizer_id: int
    name: str
    deadline: datetime
    status: str
    rules: list[RuleResponse]
