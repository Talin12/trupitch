"""Canonical status values (mirror of the API's core/constants.py)."""

from enum import Enum


class SubmissionStatus(str, Enum):
    PENDING = "pending"
    EVALUATING = "evaluating"
    EVALUATED = "evaluated"
    DISQUALIFIED = "disqualified"
