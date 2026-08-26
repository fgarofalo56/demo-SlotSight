"""API contract tests.

Exercises the HTTP surface against the seeded in-memory database by overriding
the session dependency. Covers the shapes the frontend and the MCP server both
depend on, plus the one behaviour most likely to bite a new cloner: what
``/api/chat`` does when Azure OpenAI is not configured.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from slotsight.db import get_session
from slotsight.main import create_app


@pytest_asyncio.fixture
async def client(seeded_engine):
    """Test client wired to the seeded in-memory database."""
    app = create_app()
    factory = async_sessionmaker(seeded_engine, expire_on_commit=False, class_=AsyncSession)

    async def _session_override():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_session] = _session_override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


class TestHealth:
    async def test_reports_ok_when_seeded(self, client: AsyncClient) -> None:
        r = await client.get("/api/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert {d["name"] for d in body["dependencies"]} == {"database", "azure_openai"}

    async def test_never_leaks_the_endpoint_or_a_token(self, client: AsyncClient) -> None:
        """Verifying a credential must confirm presence, never reveal a value."""
        raw = (await client.get("/api/health")).text.lower()
        assert "cognitiveservices.azure.com" not in raw
        assert "bearer" not in raw
        assert "eyj" not in raw  # JWT prefix


class TestFloor:
    async def test_summary_shape(self, client: AsyncClient) -> None:
        r = await client.get("/api/floor/summary?days=30")
        assert r.status_code == 200
        body = r.json()
        assert body["active_machine_count"] > 0
        assert body["floor_wpupd"] > 0
        assert len(body["zones"]) == 6

    async def test_summary_returns_both_indices(self, client: AsyncClient) -> None:
        """Both are returned so the UI can show why floor_index misleads."""
        zones = (await client.get("/api/floor/summary?days=30")).json()["zones"]
        assert all("peer_index" in z and "floor_index" in z for z in zones)

    async def test_high_limit_indices_diverge_sharply(self, client: AsyncClient) -> None:
        """The teaching case: floor-wide indexing mostly just sorts by denomination."""
        zones = (await client.get("/api/floor/summary?days=30")).json()["zones"]
        hl = next(z for z in zones if z["zone_code"] == "HL")
        assert hl["floor_index"] > 2.0
        assert hl["peer_index"] < 1.5

    async def test_trend_is_ordered(self, client: AsyncClient) -> None:
        pts = (await client.get("/api/floor/trend?days=60")).json()["points"]
        dates = [p["business_date"] for p in pts]
        assert dates == sorted(dates)

    async def test_signals_endpoint_documents_the_plants(self, client: AsyncClient) -> None:
        body = (await client.get("/api/floor/signals")).json()
        assert len(body["signals"]) == 4
        assert all(s["expected_outcome"] for s in body["signals"])

    @pytest.mark.parametrize("days", [0, 366, -1])
    async def test_invalid_window_rejected(self, client: AsyncClient, days: int) -> None:
        assert (await client.get(f"/api/floor/summary?days={days}")).status_code == 422


class TestMachines:
    async def test_list_and_filter(self, client: AsyncClient) -> None:
        r = await client.get("/api/machines?days=30&denomination_cents=1&limit=5")
        assert r.status_code == 200
        body = r.json()
        assert body["returned"] <= 5
        assert all(m["denomination_cents"] == 1 for m in body["machines"])

    async def test_sorted_ascending_by_peer_index_by_default(self, client: AsyncClient) -> None:
        machines = (await client.get("/api/machines?days=30&limit=20")).json()["machines"]
        indices = [m["peer_index"] for m in machines]
        assert indices == sorted(indices)

    async def test_detail_includes_trend(self, client: AsyncClient) -> None:
        first = (await client.get("/api/machines?days=30&limit=1")).json()["machines"][0]
        r = await client.get(f"/api/machines/{first['asset_number']}?days=30")
        assert r.status_code == 200
        assert len(r.json()["trend"]) > 0

    async def test_unknown_machine_is_404(self, client: AsyncClient) -> None:
        assert (await client.get("/api/machines/NP-99999")).status_code == 404

    async def test_unknown_sort_field_is_422(self, client: AsyncClient) -> None:
        assert (await client.get("/api/machines?sort=nonsense")).status_code == 422


class TestRecommendations:
    async def test_returns_ranked_recommendations(self, client: AsyncClient) -> None:
        body = (await client.get("/api/recommendations?days=30")).json()
        assert body["total"] > 0
        assert all(r["evidence"] for r in body["recommendations"])

    async def test_filter_by_action(self, client: AsyncClient) -> None:
        body = (await client.get("/api/recommendations?days=30&action=convert")).json()
        assert all(r["action"] == "convert" for r in body["recommendations"])

    async def test_outliers_exclude_flagged_machines(self, client: AsyncClient) -> None:
        body = (await client.get("/api/outliers?days=30&limit=50")).json()
        flagged = {f["asset_number"] for f in body["data_quality_flags"]}
        assert flagged
        tops = {t["machine"]["asset_number"] for t in body["top_performers"]}
        unders = {u["machine"]["asset_number"] for u in body["underperformers"]}
        assert not (flagged & tops)
        assert not (flagged & unders)


class TestMarket:
    async def test_always_declares_synthetic_provenance(self, client: AsyncClient) -> None:
        """Non-negotiable: invented benchmarks must never look sourced."""
        for path in ("/api/market/titles", "/api/market/competitors"):
            body = (await client.get(path)).json()
            assert body["is_synthetic"] is True
            assert "SYNTHETIC" in body["disclaimer"]

    async def test_exclude_owned_finds_opportunities(self, client: AsyncClient) -> None:
        body = (await client.get("/api/market/titles?exclude_owned=true")).json()
        assert body["titles"]
        assert all(t["on_our_floor"] is False for t in body["titles"])


class TestChatWithoutAzure:
    """The failure mode a brand-new cloner is most likely to hit."""

    async def test_returns_503_with_actionable_remediation(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from slotsight.config import Settings, get_settings

        get_settings.cache_clear()
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
        monkeypatch.setattr(Settings, "model_config", {**Settings.model_config, "env_file": None})
        get_settings.cache_clear()

        r = await client.post("/api/chat", json={"message": "hi", "window_days": 30})
        get_settings.cache_clear()

        assert r.status_code == 503
        detail = r.json()["detail"]
        assert detail["error"] == "azure_openai_not_configured"
        assert "AZURE_OPENAI_ENDPOINT" in detail["missing"]
        # The whole point: tell them what still works.
        assert "/api/recommendations" in detail["unaffected_endpoints"]

    async def test_analytics_endpoints_unaffected_by_missing_azure(
        self, client: AsyncClient
    ) -> None:
        """The architectural claim, asserted: analytics never touch Azure OpenAI."""
        for path in (
            "/api/floor/summary?days=30",
            "/api/machines?days=30&limit=5",
            "/api/recommendations?days=30&limit=5",
            "/api/outliers?days=30&limit=5",
        ):
            assert (await client.get(path)).status_code == 200
