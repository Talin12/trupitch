"""Canonical status values (mirror of the API's core/constants.py).

Deliberately duplicated rather than imported: the worker and the API
are separate deployables (see models.py's docstring for the same
reasoning applied to ORM models), so the worker doesn't depend on
apps/api at all. If you change a status value here, change the matching
one in apps/api/core/constants.py too.
"""

from enum import Enum


class SubmissionStatus(str, Enum):
    """Mirrors apps/api/core/constants.py's SubmissionStatus. `str, Enum`
    means these compare equal to their raw string ("pending", etc.) and
    serialize as plain strings, matching what's stored in the DB column.
    """

    PENDING = "pending"  # queued, not yet picked up by a worker
    EVALUATING = "evaluating"  # worker is actively running the pipeline
    EVALUATED = "evaluated"  # all 3 stages passed; final_score is set
    DISQUALIFIED = "disqualified"  # failed Stage 1 (hard heuristics)
