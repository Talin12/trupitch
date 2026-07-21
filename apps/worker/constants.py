from enum import Enum


class SubmissionStatus(str, Enum):

    PENDING = "pending"
    EVALUATING = "evaluating"
    EVALUATED = "evaluated"
    DISQUALIFIED = "disqualified"
