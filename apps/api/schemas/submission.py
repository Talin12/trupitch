"""Pydantic schemas for the Submission API surface (see
routers/submissions.py and routers/campaigns.py's leaderboard route)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SubmissionCreate(BaseModel):
    """Body for POST /api/campaigns/{id}/submit.

    Note there's no campaign_id or hacker_id field here — campaign_id
    comes from the URL path, and hacker_id is derived server-side from
    the caller's JWT (see core/security.get_current_hacker), never from
    anything the client could spoof in the body.
    """

    team_name: str = Field(min_length=1, max_length=255)
    # HttpUrl both validates the value is a well-formed URL *and*
    # normalizes it (e.g. adds a trailing slash), which is why
    # routers/submissions.py stores str(payload.github_url) rather than
    # the raw client-submitted string.
    github_url: HttpUrl
    pitch_text: str = Field(min_length=1)


class SubmissionResponse(BaseModel):
    """Shape returned by the create/get/leaderboard submission endpoints,
    and pushed to the frontend on initial fetch (subsequent live updates
    while a submission is evaluating arrive as a smaller ad hoc JSON
    payload over the WebSocket — see apps/worker/tasks.py's
    publish_update and the frontend's LiveUpdate type).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    team_name: str
    github_url: str
    pitch_text: str
    # SubmissionStatus value as a plain string (core/constants.py).
    status: str
    # None until Stage 3 completes; stays None forever if disqualified.
    final_score: float | None
    # "<tech summary> | <AI rationale>" once evaluated, or just the
    # disqualification reason if not — see models/submission.py.
    notes: str | None
    created_at: datetime
    updated_at: datetime
