"""Pydantic schemas for a single rubric rule, nested inside Campaign
schemas (see schemas/campaign.py)."""

from pydantic import BaseModel, ConfigDict, Field


class RuleCreate(BaseModel):
    """One rubric line item as submitted by the Campaign Builder form:
    a free-text criterion plus a positive weight."""

    description: str = Field(min_length=1)
    weight: float = Field(default=1.0, gt=0)


class RuleResponse(BaseModel):
    """Rule as stored, including its DB-assigned id and parent campaign_id."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    description: str
    weight: float
