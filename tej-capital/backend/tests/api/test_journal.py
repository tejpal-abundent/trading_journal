import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_journal_crud_roundtrip():
    """Test from the brief: POST, then GET with filters."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/journal", json={
            "entry_date": "2026-08-16", "body": "First entry", "tags": ["reflection"],
        })
        assert r.status_code == 201
        eid = r.json()["id"]
        listing = await ac.get("/api/journal?since=2026-08-16&tag=reflection")
        assert any(e["id"] == eid for e in listing.json())


@pytest.mark.asyncio
async def test_journal_patch_entry():
    """Test updating a journal entry."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create an entry
        r = await ac.post("/api/journal", json={
            "entry_date": "2026-08-16", "body": "Original", "tags": ["test"],
        })
        assert r.status_code == 201
        eid = r.json()["id"]

        # Update it
        patch = await ac.patch(f"/api/journal/{eid}", json={
            "body": "Updated body", "tags": ["test", "updated"],
        })
        assert patch.status_code == 200
        body = patch.json()
        assert body["body"] == "Updated body"
        assert "updated" in body["tags"]


@pytest.mark.asyncio
async def test_journal_get_without_filters():
    """Test listing all entries without filters returns at least created entries."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.post("/api/journal", json={
            "entry_date": "2026-08-14", "body": "Unique Entry 1", "tags": ["a"],
        })
        id1 = r1.json()["id"]
        r2 = await ac.post("/api/journal", json={
            "entry_date": "2026-08-15", "body": "Unique Entry 2", "tags": ["b"],
        })
        id2 = r2.json()["id"]
        listing = await ac.get("/api/journal")
        assert listing.status_code == 200
        entries = listing.json()
        assert any(e["id"] == id1 for e in entries)
        assert any(e["id"] == id2 for e in entries)


@pytest.mark.asyncio
async def test_journal_get_with_since_filter():
    """Test listing entries filtered by since date."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.post("/api/journal", json={
            "entry_date": "2026-08-14", "body": "Old Entry", "tags": [],
        })
        old_id = r1.json()["id"]
        r2 = await ac.post("/api/journal", json={
            "entry_date": "2026-08-16", "body": "New Entry", "tags": [],
        })
        new_id = r2.json()["id"]
        listing = await ac.get("/api/journal?since=2026-08-15")
        entries = listing.json()
        # Should include the new entry
        assert any(e["id"] == new_id for e in entries)
        # Should NOT include the old entry
        assert not any(e["id"] == old_id for e in entries)


@pytest.mark.asyncio
async def test_journal_get_with_tag_filter():
    """Test listing entries filtered by tag."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.post("/api/journal", json={
            "entry_date": "2026-08-16", "body": "Tagged Important", "tags": ["important"],
        })
        tagged_id = r1.json()["id"]
        r2 = await ac.post("/api/journal", json={
            "entry_date": "2026-08-16", "body": "Tagged Other", "tags": ["other"],
        })
        other_id = r2.json()["id"]
        listing = await ac.get("/api/journal?tag=important")
        entries = listing.json()
        # Should include the important entry
        assert any(e["id"] == tagged_id for e in entries)
        # Should NOT include the other entry
        assert not any(e["id"] == other_id for e in entries)


@pytest.mark.asyncio
async def test_journal_patch_nonexistent_returns_404():
    """Test patching a non-existent entry."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        import uuid
        fake_id = uuid.uuid4()
        r = await ac.patch(f"/api/journal/{fake_id}", json={"body": "nope"})
        assert r.status_code == 404
        assert r.json()["detail"]["error"] == "entry_not_found"


@pytest.mark.asyncio
async def test_journal_post_body_min_length():
    """Test that body must have min 1 character."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/journal", json={
            "entry_date": "2026-08-16", "body": "", "tags": [],
        })
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_journal_post_default_tags_empty():
    """Test that tags default to empty list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/journal", json={
            "entry_date": "2026-08-16", "body": "No tags",
        })
        assert r.status_code == 201
        assert r.json()["tags"] == []
