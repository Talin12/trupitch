"""Canonical status values shared across the API (mirrored in the worker).

Using `str, Enum` (rather than a plain Enum) means these members compare
equal to their raw string value (`CampaignStatus.OPEN == "open"` is True)
and serialize to plain strings in JSON responses — so switching from raw
strings to these enums was a drop-in change everywhere they're used.

Note: apps/worker/constants.py defines the equivalent SubmissionStatus
enum independently (the worker is a separate deployable and deliberately
doesn't import API code). If a status value changes here, update it there
too.
"""

from enum import Enum


class CampaignStatus(str, Enum):
    """Lifecycle of an organizer's campaign (hackathon event)."""

    DRAFT = "draft"  # created but not yet accepting submissions
    OPEN = "open"  # accepting submissions
    EVALUATING = "evaluating"  # submissions closed, pipeline still running
    CLOSED = "closed"  # evaluation finished / event over


class SubmissionStatus(str, Enum):
    """Lifecycle of a single hacker submission through the worker pipeline.

    Transitions: PENDING -> EVALUATING -> (EVALUATED | DISQUALIFIED).
    Set by apps/worker/tasks.py as the 3-stage pipeline progresses;
    read here by the API to build responses and the leaderboard.
    """

    PENDING = "pending"  # queued, not yet picked up by a worker
    EVALUATING = "evaluating"  # worker is actively running the pipeline
    EVALUATED = "evaluated"  # all 3 stages passed; final_score is set
    DISQUALIFIED = "disqualified"  # failed Stage 1 (hard heuristics)
