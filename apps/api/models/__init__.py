"""ORM models. Importing this package registers all tables on Base.metadata.

Any code that needs a model should `from models import Campaign` (etc.)
rather than reaching into the submodule directly — this file is the
single place that guarantees every model has been imported and is
therefore known to SQLAlchemy and to Alembic's autogenerate.
"""

from models.base import Base
from models.campaign import Campaign
from models.hacker import Hacker
from models.organizer import Organizer
from models.rule import Rule
from models.submission import Submission

__all__ = ["Base", "Campaign", "Hacker", "Organizer", "Rule", "Submission"]
