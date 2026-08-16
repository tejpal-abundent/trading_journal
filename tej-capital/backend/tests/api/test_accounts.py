import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_composite_membership_cannot_be_changed_R4(db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create = await ac.post("/api/accounts", json={
            "name": "Main", "broker": "IBKR", "currency": "USD",
            "account_type": "live", "in_composite": True,
        })
        assert create.status_code == 201
        aid = create.json()["id"]

        patch = await ac.patch(f"/api/accounts/{aid}", json={"in_composite": False,
                                                             "exclusion_reason": "changed my mind about it"})
        assert patch.status_code == 409
        assert patch.json()["detail"]["error"] == "composite_membership_immutable"


@pytest.mark.asyncio
async def test_excluding_account_requires_reason_ge_10_chars():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/accounts", json={
            "name": "Prop", "broker": "Apex", "currency": "USD",
            "account_type": "prop_evaluation", "in_composite": False,
            "exclusion_reason": "too short",
        })
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_and_list_accounts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create = await ac.post("/api/accounts", json={
            "name": "Sim Mirror", "broker": "Darwinex", "currency": "USD",
            "account_type": "verified_mirror", "in_composite": True,
        })
        assert create.status_code == 201
        body = create.json()
        assert body["name"] == "Sim Mirror"
        assert body["archived_at"] is None
        aid = body["id"]

        listing = await ac.get("/api/accounts")
        assert listing.status_code == 200
        ids = [row["id"] for row in listing.json()]
        assert aid in ids


@pytest.mark.asyncio
async def test_update_editable_fields_without_touching_composite():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create = await ac.post("/api/accounts", json={
            "name": "Editable", "broker": "IBKR", "currency": "USD",
            "account_type": "live", "in_composite": True,
        })
        aid = create.json()["id"]

        patch = await ac.patch(f"/api/accounts/{aid}", json={"broker": "Interactive Brokers"})
        assert patch.status_code == 200
        body = patch.json()
        assert body["broker"] == "Interactive Brokers"
        assert body["in_composite"] is True


@pytest.mark.asyncio
async def test_archive_account_sets_archived_at():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create = await ac.post("/api/accounts", json={
            "name": "To Archive", "broker": "IBKR", "currency": "USD",
            "account_type": "demo", "in_composite": True,
        })
        aid = create.json()["id"]
        assert create.json()["archived_at"] is None

        archived = await ac.post(f"/api/accounts/{aid}/archive")
        assert archived.status_code == 200
        assert archived.json()["archived_at"] is not None
