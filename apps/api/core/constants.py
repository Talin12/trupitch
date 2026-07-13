"""Canonical status values shared across the API (mirrored in the worker)."""

from enum import Enum


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    EVALUATING = "evaluating"
    CLOSED = "closed"


class SubmissionStatus(str, Enum):
    PENDING = "pending"
    EVALUATING = "evaluating"
    EVALUATED = "evaluated"
    DISQUALIFIED = "disqualified"
