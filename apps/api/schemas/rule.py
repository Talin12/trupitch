from pydantic import BaseModel, ConfigDict, Field


class RuleCreate(BaseModel):
    description: str = Field(min_length=1)
    weight: float = Field(default=1.0, gt=0)


class RuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    description: str
    weight: float
