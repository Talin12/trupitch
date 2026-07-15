"""Pydantic request/response schemas.

Routers import from this package (`from schemas import CampaignCreate`)
rather than from the individual submodules, so this file's job is just
to re-export everything in one place.
"""

from schemas.campaign import CampaignCreate, CampaignResponse
from schemas.rule import RuleCreate, RuleResponse
from schemas.submission import SubmissionCreate, SubmissionResponse

__all__ = [
    "CampaignCreate",
    "CampaignResponse",
    "RuleCreate",
    "RuleResponse",
    "SubmissionCreate",
    "SubmissionResponse",
]
