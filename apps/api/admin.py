from datetime import datetime, timedelta, timezone

import jwt
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from core.config import settings
from core.database import engine
from models import Campaign, Hacker, Organizer, Rule, Submission

_SESSION_TTL = timedelta(hours=12)
_JWT_ALG = "HS256"

_ADMIN_SECRET = settings.admin_session_secret or settings.jwt_secret


class AdminAuth(AuthenticationBackend):

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username", "")
        password = form.get("password", "")

        if not settings.admin_password:
            return False
        if username != settings.admin_username or password != settings.admin_password:
            return False

        token = jwt.encode(
            {
                "sub": username,
                "exp": datetime.now(timezone.utc) + _SESSION_TTL,
            },
            _ADMIN_SECRET,
            algorithm=_JWT_ALG,
        )
        request.session.update({"token": token})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        try:
            jwt.decode(token, _ADMIN_SECRET, algorithms=[_JWT_ALG])
        except jwt.PyJWTError:
            return False
        return True


class OrganizerAdmin(ModelView, model=Organizer):
    name = "Organizer"
    name_plural = "Organizers"
    icon = "fa-solid fa-user-tie"
    column_list = [Organizer.id, Organizer.email, Organizer.name, Organizer.created_at]
    column_searchable_list = [Organizer.email, Organizer.name]
    column_sortable_list = [Organizer.id, Organizer.created_at]


class CampaignAdmin(ModelView, model=Campaign):
    name = "Campaign"
    name_plural = "Campaigns"
    icon = "fa-solid fa-trophy"
    column_list = [
        Campaign.id,
        Campaign.name,
        Campaign.organizer_id,
        Campaign.status,
        Campaign.deadline,
    ]
    column_searchable_list = [Campaign.name, Campaign.status]
    column_sortable_list = [Campaign.id, Campaign.deadline, Campaign.status]


class RuleAdmin(ModelView, model=Rule):
    name = "Rule"
    name_plural = "Rules"
    icon = "fa-solid fa-list-check"
    column_list = [Rule.id, Rule.campaign_id, Rule.description, Rule.weight]
    column_sortable_list = [Rule.id, Rule.campaign_id, Rule.weight]


class SubmissionAdmin(ModelView, model=Submission):
    name = "Submission"
    name_plural = "Submissions"
    icon = "fa-solid fa-code-pull-request"
    column_list = [
        Submission.id,
        Submission.campaign_id,
        Submission.team_name,
        Submission.status,
        Submission.final_score,
        Submission.created_at,
    ]
    column_searchable_list = [Submission.team_name, Submission.status]
    column_sortable_list = [
        Submission.id,
        Submission.status,
        Submission.final_score,
        Submission.created_at,
    ]


class HackerAdmin(ModelView, model=Hacker):
    name = "Hacker"
    name_plural = "Hackers"
    icon = "fa-solid fa-user"
    column_list = [Hacker.id, Hacker.username, Hacker.github_id]
    column_searchable_list = [Hacker.username, Hacker.github_id]
    column_details_exclude_list = [Hacker.github_token]
    form_excluded_columns = [Hacker.github_token]


def setup_admin(app) -> None:
    authentication_backend = AdminAuth(secret_key=_ADMIN_SECRET)
    admin = Admin(
        app,
        engine,
        authentication_backend=authentication_backend,
        title="TruPitch Admin",
    )
    admin.add_view(OrganizerAdmin)
    admin.add_view(CampaignAdmin)
    admin.add_view(RuleAdmin)
    admin.add_view(SubmissionAdmin)
    admin.add_view(HackerAdmin)
