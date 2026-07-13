from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SubmissionCreate(BaseModel):
    team_name: str = Field(min_length=1, max_length=255)
    github_url: HttpUrl
    pitch_text: str = Field(min_length=1)


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    team_name: str
    github_url: str
    pitch_text: str
    status: str
    final_score: float | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
