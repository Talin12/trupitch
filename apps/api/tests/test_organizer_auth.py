from conftest import auth, register_organizer


async def test_register_returns_token(client):
    token, organizer_id = await register_organizer(client)
    assert token
    assert isinstance(organizer_id, int)


async def test_duplicate_email_conflicts(client):
    await register_organizer(client, email="dup@test.io")
    resp = await client.post(
        "/api/auth/organizer/register",
        json={"email": "dup@test.io", "name": "Other", "password": "password123"},
    )
    assert resp.status_code == 409


async def test_login_succeeds_and_wrong_password_fails(client):
    await register_organizer(client, email="login@test.io", password="password123")
    ok = await client.post(
        "/api/auth/organizer/login",
        json={"email": "login@test.io", "password": "password123"},
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = await client.post(
        "/api/auth/organizer/login",
        json={"email": "login@test.io", "password": "wrong"},
    )
    assert bad.status_code == 401


async def test_login_unknown_email_fails(client):
    resp = await client.post(
        "/api/auth/organizer/login",
        json={"email": "nobody@test.io", "password": "whatever12"},
    )
    assert resp.status_code == 401


async def test_email_is_normalized(client):
    await register_organizer(client, email="Mixed@Case.IO", password="password123")
    # Login with a differently-cased email still works.
    resp = await client.post(
        "/api/auth/organizer/login",
        json={"email": "mixed@case.io", "password": "password123"},
    )
    assert resp.status_code == 200


async def test_hacker_token_cannot_act_as_organizer(client, session):
    """A hacker-typed JWT must not authorize organizer-only endpoints."""
    from core.security import create_access_token
    from models import Hacker

    hacker = Hacker(github_id="1", username="h", github_token="t")
    session.add(hacker)
    await session.commit()
    await session.refresh(hacker)

    hacker_token = create_access_token(hacker.id)
    resp = await client.get("/api/campaigns/mine", headers=auth(hacker_token))
    assert resp.status_code == 401
