from datetime import datetime, timedelta, timezone

import pytest_asyncio

from conftest import auth


@pytest_asyncio.fixture
async def hacker_token(session):
    from core.security import create_access_token
    from models import Hacker

    hacker = Hacker(github_id="99", username="tester", github_token="tok")
    session.add(hacker)
    await session.commit()
    await session.refresh(hacker)
    return create_access_token(hacker.id)


@pytest_asyncio.fixture(autouse=True)
def _stub_external(monkeypatch):
    """Submissions call GitHub and Celery; stub both so tests stay hermetic."""
    import routers.submissions as subs

    async def _noop_repo(*args, **kwargs):
        return None

    monkeypatch.setattr(subs, "_verify_repo_access", _noop_repo)
    monkeypatch.setattr(subs.celery_client, "send_task", lambda *a, **k: None)


async def _make_campaign(session, **overrides):
    from models import Campaign, Organizer

    org = Organizer(email=f"o{datetime.now().timestamp()}@t.io", name="O")
    session.add(org)
    await session.flush()
    defaults = dict(
        organizer_id=org.id,
        name="C",
        status="open",
        deadline=datetime.now(timezone.utc) + timedelta(days=1),
        max_team_size=4,
        max_submissions_per_team=1,
        allow_late_submissions=False,
    )
    defaults.update(overrides)
    campaign = Campaign(**defaults)
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)
    return campaign


def _body(**extra):
    base = {
        "team_name": "Team A",
        "github_url": "https://github.com/octocat/hello",
        "pitch_text": "we built a thing",
    }
    base.update(extra)
    return base


async def test_valid_submission_accepted_and_persists_team_size(client, session, hacker_token):
    campaign = await _make_campaign(session)
    resp = await client.post(
        f"/api/campaigns/{campaign.id}/submit",
        json=_body(team_size=3),
        headers=auth(hacker_token),
    )
    assert resp.status_code == 202, resp.text
    assert resp.json()["team_size"] == 3


async def test_team_size_over_max_rejected(client, session, hacker_token):
    campaign = await _make_campaign(session, max_team_size=2)
    resp = await client.post(
        f"/api/campaigns/{campaign.id}/submit",
        json=_body(team_size=5),
        headers=auth(hacker_token),
    )
    assert resp.status_code == 400
    assert "Team size" in resp.json()["detail"]


async def test_past_deadline_rejected(client, session, hacker_token):
    campaign = await _make_campaign(
        session, deadline=datetime.now(timezone.utc) - timedelta(days=1)
    )
    resp = await client.post(
        f"/api/campaigns/{campaign.id}/submit",
        json=_body(),
        headers=auth(hacker_token),
    )
    assert resp.status_code == 400
    assert "deadline" in resp.json()["detail"].lower()


async def test_late_submission_allowed_when_configured(client, session, hacker_token):
    campaign = await _make_campaign(
        session,
        deadline=datetime.now(timezone.utc) - timedelta(days=1),
        allow_late_submissions=True,
    )
    resp = await client.post(
        f"/api/campaigns/{campaign.id}/submit",
        json=_body(),
        headers=auth(hacker_token),
    )
    assert resp.status_code == 202


async def test_per_team_submission_cap(client, session, hacker_token):
    campaign = await _make_campaign(session, max_submissions_per_team=1)
    first = await client.post(
        f"/api/campaigns/{campaign.id}/submit",
        json=_body(team_name="Wolves"),
        headers=auth(hacker_token),
    )
    assert first.status_code == 202
    # Same team, case-insensitive, second attempt exceeds the cap.
    second = await client.post(
        f"/api/campaigns/{campaign.id}/submit",
        json=_body(team_name="wolves"),
        headers=auth(hacker_token),
    )
    assert second.status_code == 400


async def test_submit_requires_hacker_auth(client, session):
    campaign = await _make_campaign(session)
    resp = await client.post(
        f"/api/campaigns/{campaign.id}/submit", json=_body()
    )
    assert resp.status_code == 401
