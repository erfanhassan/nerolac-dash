"""Integration & Performance Test Suite for Module 1: Finance Control Center API.

Verifies:
1. Sub-50ms execution speed across all endpoints (/segment-pnl, /supplier-variance,
   /simulate-cashflow, /ar-ap-aging).
2. Segment P&L GL codes 10000–10017 aggregation, Apache ECharts Waterfall series,
   and TanStack Tree Grid hierarchical payload.
3. Supplier price spread calculations flagging >5% variances with warm amber #D97706.
4. Real-time Cash Flow simulation dynamics across AR %, DPO, and CapEx sliders.
5. AR / AP Aging buckets (0–30, 31–60, 61–90, 90+ days) and working capital gap.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from src.backend.cache.cache_invalidation import get_cache_manager
from src.backend.main import app


@pytest.fixture(autouse=True)
async def clear_finance_cache() -> AsyncIterator[None]:
    """Flush relevant finance query caches before/after tests."""
    cache = get_cache_manager()
    await cache.flush_pattern("dash:finance:*")
    yield
    await cache.flush_pattern("dash:finance:*")


class TestFinanceControlCenterAPI:
    """Verifies Module 1 Finance endpoints meet functional and sub-50ms SLA specifications."""

    async def test_segment_pnl_endpoint_and_performance(self) -> None:
        """Assert /segment-pnl returns valid GL 10000–10017 aggregates in <50ms."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # First call warms cache if not cached
            warmup = await client.get("/api/v1/finance/segment-pnl?fiscal_year=2024&fiscal_month=3")
            assert warmup.status_code == 200

            # Second call tests the cached sub-50ms execution SLA
            start = time.perf_counter()
            response = await client.get(
                "/api/v1/finance/segment-pnl?fiscal_year=2024&fiscal_month=3"
            )
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            assert response.status_code == 200
            assert elapsed_ms < 50.0, f"API response exceeded 50ms SLA: took {elapsed_ms:.2f}ms"

            data = response.json()
            assert data["fiscal_year"] == 2024
            assert data["fiscal_month"] == 3
            assert data["gross_revenue_bdt"] > 0
            assert data["net_revenue_bdt"] > 0
            assert data["cogs_bdt"] > 0
            assert "waterfall_series" in data
            assert len(data["waterfall_series"]) >= 10
            assert "tree_grid_rows" in data
            assert len(data["tree_grid_rows"]) >= 2  # Architectural and Industrial divisions

            # Validate GL code 10000–10017 mapping
            gl_summary = data["gl_code_summary"]
            for gl in range(10000, 10018):
                assert str(gl) in gl_summary, f"Missing GL code {gl} in summary"

            # Assert Waterfall structure
            waterfall_names = [item["name"] for item in data["waterfall_series"]]
            assert "Gross Sales" in waterfall_names
            assert "Net Revenue" in waterfall_names
            assert "Gross Margin" in waterfall_names
            assert "EBITDA" in waterfall_names
            assert "Net Profit" in waterfall_names

            # Assert TanStack Tree Grid structure
            division_labels = [row["label"] for row in data["tree_grid_rows"]]
            assert "Architectural Coatings" in division_labels
            assert "Industrial Coatings" in division_labels
            assert len(data["tree_grid_rows"][0]["children"]) > 0

    async def test_supplier_variance_endpoint_and_performance(self) -> None:
        """Assert /supplier-variance identifies price spreads & flags >5% with #D97706 in <50ms."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Warm cache
            await client.get("/api/v1/finance/supplier-variance")

            start = time.perf_counter()
            response = await client.get("/api/v1/finance/supplier-variance")
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            assert response.status_code == 200
            assert elapsed_ms < 50.0, f"API response exceeded 50ms SLA: took {elapsed_ms:.2f}ms"

            data = response.json()
            assert data["total_materials_evaluated"] > 0
            assert data["flagged_variance_count"] >= 1
            assert len(data["records"]) > 0

            # Verify variance flags and warm amber styling (#D97706)
            for record in data["records"]:
                if record["variance_pct"] > 5.0:
                    assert record["is_flagged"] is True
                    assert record["severity_color"] == "#D97706", "Flagged spread must use #D97706"
                else:
                    assert record["is_flagged"] is False
                    assert record["severity_color"] != "#D97706"

    async def test_simulate_cashflow_endpoint_and_performance(self) -> None:
        """Assert /simulate-cashflow executes real-time simulations in <50ms."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            payload = {
                "ar_collection_pct": 85.0,
                "dpo_days": 45,
                "capex_bdt": 5000000.0,
                "forecast_months": 6,
            }

            start = time.perf_counter()
            response = await client.post("/api/v1/finance/simulate-cashflow", json=payload)
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            assert response.status_code == 200
            assert elapsed_ms < 50.0, f"Simulation exceeded 50ms SLA: took {elapsed_ms:.2f}ms"

            data = response.json()
            assert data["execution_time_ms"] < 50.0
            assert data["forecast_months"] == 6
            assert len(data["monthly_projections"]) == 6
            assert data["liquidity_status"] in ("HEALTHY", "CAUTION", "CRITICAL")

    async def test_simulate_cashflow_slider_sensitivity(self) -> None:
        """Verify dynamic sensitivity when sliders change (AR collection %, DPO, CapEx)."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Baseline Scenario
            base_res = await client.post(
                "/api/v1/finance/simulate-cashflow",
                json={
                    "ar_collection_pct": 75.0,
                    "dpo_days": 45,
                    "capex_bdt": 5000000.0,
                    "forecast_months": 6,
                },
            )
            base_data = base_res.json()

            # Scenario 1: Aggressive AR Collection (95% vs 75%) -> higher cash balance
            high_ar_res = await client.post(
                "/api/v1/finance/simulate-cashflow",
                json={
                    "ar_collection_pct": 95.0,
                    "dpo_days": 45,
                    "capex_bdt": 5000000.0,
                    "forecast_months": 6,
                },
            )
            high_ar_data = high_ar_res.json()
            assert high_ar_data["ending_cash_balance_bdt"] > base_data["ending_cash_balance_bdt"]

            # Scenario 2: Extended DPO (90d vs 45d) -> deferred outflow -> higher cash balance
            high_dpo_res = await client.post(
                "/api/v1/finance/simulate-cashflow",
                json={
                    "ar_collection_pct": 75.0,
                    "dpo_days": 90,
                    "capex_bdt": 5000000.0,
                    "forecast_months": 6,
                },
            )
            high_dpo_data = high_dpo_res.json()
            assert high_dpo_data["ending_cash_balance_bdt"] > base_data["ending_cash_balance_bdt"]

            # Scenario 3: High CapEx (25M vs 5M) -> lower cash balance
            high_capex_res = await client.post(
                "/api/v1/finance/simulate-cashflow",
                json={
                    "ar_collection_pct": 75.0,
                    "dpo_days": 45,
                    "capex_bdt": 25000000.0,
                    "forecast_months": 6,
                },
            )
            high_capex_data = high_capex_res.json()
            assert high_capex_data["ending_cash_balance_bdt"] < base_data["ending_cash_balance_bdt"]

    async def test_simulate_cashflow_get_slider_trigger(self) -> None:
        """Verify GET /simulate-cashflow endpoint for frontend real-time slider queries."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get(
                "/api/v1/finance/simulate-cashflow?ar_collection_pct=90.0&dpo_days=60&capex_bdt=3000000"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["ar_collection_pct"] == 90.0
            assert data["dpo_days"] == 60
            assert data["capex_bdt"] == 3000000.0

    async def test_ar_ap_aging_endpoint_and_performance(self) -> None:
        """Assert /ar-ap-aging returns sorted 0–30, 31–60, 61–90, and 90+ buckets in <50ms."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Warm cache
            await client.get("/api/v1/finance/ar-ap-aging")

            start = time.perf_counter()
            response = await client.get("/api/v1/finance/ar-ap-aging")
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            assert response.status_code == 200
            assert elapsed_ms < 50.0, f"API response exceeded 50ms SLA: took {elapsed_ms:.2f}ms"

            data = response.json()
            assert data["total_receivables_bdt"] > 0
            assert data["total_payables_bdt"] > 0
            assert data["net_working_capital_bdt"] == round(
                data["total_receivables_bdt"] - data["total_payables_bdt"], 2
            )

            # Assert buckets
            bucket_labels = [b["bucket_label"] for b in data["buckets"]]
            assert "0–30 Days" in bucket_labels
            assert "31–60 Days" in bucket_labels
            assert "61–90 Days" in bucket_labels
            assert "90+ Days" in bucket_labels

            # Assert entity details
            assert len(data["entity_records"]) > 0
            entry_types = {r["entry_type"] for r in data["entity_records"]}
            assert "RECEIVABLE" in entry_types
            assert "PAYABLE" in entry_types
