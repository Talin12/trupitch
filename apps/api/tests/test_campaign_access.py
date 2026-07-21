from conftest import auth, register_organizer

FUTURE = "2035-01-01T00:00:00Z"


def _campaign_body(name="Camp", status="open", **extra):
    return {"name": name, "deadline": FUTURE, "status": status, **extra}


async def test_create_requires_auth(client):
    resp = await client.post("/api/campaigns", json=_campaign_body())
    assert resp.status_code == 401


async def test_create_attaches_to_authenticated_organizer(client):
    token, organizer_id = await register_organizer(client)
    resp = await client.post(
        "/api/campaigns", json=_campaign_body(), headers=auth(token)
    )
    assert resp.status_code == 201
    assert resp.json()["organizer_id"] == organizer_id


async def test_mine_is_scoped_to_owner(client):
    token_a, _ = await register_organizer(client, email="a@test.io")
    token_b, _ = await register_organizer(client, email="b@test.io")
    await client.post(
        "/api/campaigns", json=_campaign_body(name="A"), headers=auth(token_a)
    )

    mine_a = await client.get("/api/campaigns/mine", headers=auth(token_a))
    mine_b = await client.get("/api/campaigns/mine", headers=auth(token_b))
    assert [c["name"] for c in mine_a.json()] == ["A"]
    assert mine_b.json() == []


async def test_public_list_excludes_drafts(client):
    token, _ = await register_organizer(client)
    await client.post(
        "/api/campaigns", json=_campaign_body(name="Draft", status="draft"),
        headers=auth(token),
    )
    await client.post(
        "/api/campaigns", json=_campaign_body(name="Open", status="open"),
        headers=auth(token),
    )
    resp = await client.get("/api/campaigns")
    names = [c["name"] for c in resp.json()]
    assert names == ["Open"]


async def test_submissions_ownership(client):
    token_a, _ = await register_organizer(client, email="a@test.io")
    token_b, _ = await register_organizer(client, email="b@test.io")
    created = await client.post(
        "/api/campaigns", json=_campaign_body(), headers=auth(token_a)
    )
    cid = created.json()["id"]

    assert (await client.get(f"/api/campaigns/{cid}/submissions")).status_code == 401
    assert (
        await client.get(f"/api/campaigns/{cid}/submissions", headers=auth(token_a))
    ).status_code == 200
    # Another organizer gets 404 (existence not revealed), not 403.
    assert (
        await client.get(f"/api/campaigns/{cid}/submissions", headers=auth(token_b))
    ).status_code == 404


async def test_event_page_read_stays_public(client):
    """GET /api/campaigns/{id} must remain public for the hacker event page."""
    token, _ = await register_organizer(client)
    created = await client.post(
        "/api/campaigns", json=_campaign_body(), headers=auth(token)
    )
    cid = created.json()["id"]
    resp = await client.get(f"/api/campaigns/{cid}")
    assert resp.status_code == 200
