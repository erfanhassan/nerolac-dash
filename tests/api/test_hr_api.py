"""Integration & Performance Test Suite for Module 2: HR Workforce Intelligence API.

Verifies:
1. Sub-50ms execution speed across all HR endpoints (/manpower-capacity, /kpi-scorecard,
   /ctc-scatter-plot).
2. 2-Factor Capacity formula calculations:
   - Sales Revenue Capacity == Territory Target / 15 Lacs BDT (1,500,000 BDT)
   - Workload Capacity == (Active Dealers x Visit Frequency) / 24 Days
   - Exactly 39 vacant territories with ROI payback metrics.
3. 0–100 composite weighted index across 6 core KPIs:
   - Sales % (30%), Collections % (20%), Coverage % (15%), Conversions % (15%),
     Reviews % (10%), WhatsApp Discipline % (10%).
   - ECharts 6-axis Radar indicators and benchmark values.
4. Fully-loaded CTC formula:
   - Base + TA/DA + Incentives + Overhead.
   - 4-Quadrant classification (Stars, Heavy Hitters, Ramp-up, Value Destroyers).
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from src.backend.cache.cache_invalidation import get_cache_manager
from src.backend.main import app


@pytest.fixture(autouse=True)
async def clear_hr_cache() -> AsyncIterator[None]:
    """Flush relevant HR query caches before and after each test."""
    cache = get_cache_manager()
    await cache.flush_pattern("dash:hr:*")
    yield
    await cache.flush_pattern("dash:hr:*")


class TestHRWorkforceAPI:
    """Verifies Module 2 HR endpoints meet functional and sub-50ms SLA specifications."""

    async def test_manpower_capacity_2_factor_formula(self) -> None:
        """Verify 2-Factor Capacity calculations and 39 vacant territories."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Warm-up / cache seed
            warmup = await client.get("/api/v1/hr/manpower-capacity")
            assert warmup.status_code == 200

            # Measure cached sub-50ms SLA
            start = time.perf_counter()
            response = await client.get("/api/v1/hr/manpower-capacity")
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            assert response.status_code == 200
            assert elapsed_ms < 50.0, f"API response exceeded 50ms SLA: took {elapsed_ms:.2f}ms"

            data = response.json()
            assert data["total_vacant_territories"] == 39
            assert len(data["territories"]) == 39
            assert data["benchmark_sales_capacity_lac_bdt"] == 15.0
            assert data["benchmark_working_days"] == 24
            assert data["total_recommended_headcount"] >= 39
            assert data["average_payback_months"] > 0

            # Verify 2-Factor Capacity arithmetic for every territory
            for t in data["territories"]:
                target_bdt = t["territory_target_bdt"]
                dealers = t["active_dealers"]
                visit_freq = t["visit_frequency"]

                expected_sales_cap = round(target_bdt / 1_500_000.0, 2)
                expected_workload_cap = round((dealers * visit_freq) / 24.0, 2)
                expected_combined_cap = round((expected_sales_cap + expected_workload_cap) / 2.0, 2)

                assert t["sales_revenue_capacity"] == pytest.approx(expected_sales_cap, abs=0.01)
                assert t["workload_capacity"] == pytest.approx(expected_workload_cap, abs=0.01)
                assert t["combined_capacity"] == pytest.approx(expected_combined_cap, abs=0.01)
                assert t["recommended_headcount"] >= 1
                assert t["current_headcount"] == 0
                assert t["gap_headcount"] == t["recommended_headcount"]
                assert t["roi_payback_months"] > 0
                assert len(t["justification_summary"]) > 20

    async def test_manpower_capacity_depot_filter(self) -> None:
        """Verify filtering vacant territories by regional depot."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/hr/manpower-capacity?depot_id=DEPOT_01")
            assert response.status_code == 200
            data = response.json()
            assert data["total_vacant_territories"] == 10
            for t in data["territories"]:
                assert t["depot_id"] == "DEPOT_01"

    async def test_kpi_scorecard_calculation_and_performance(self) -> None:
        """Assert /kpi-scorecard computes 0–100 weighted index across 6 core KPIs."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            warmup = await client.get("/api/v1/hr/kpi-scorecard?assessment_period=2024-M03")
            assert warmup.status_code == 200

            start = time.perf_counter()
            response = await client.get("/api/v1/hr/kpi-scorecard?assessment_period=2024-M03")
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            assert response.status_code == 200
            assert elapsed_ms < 50.0, f"API response exceeded 50ms SLA: took {elapsed_ms:.2f}ms"

            data = response.json()
            assert data["assessment_period"] == "2024-M03"
            assert len(data["indicators"]) == 6
            indicator_names = [ind["name"] for ind in data["indicators"]]
            assert "Sales %" in indicator_names
            assert "Collections %" in indicator_names
            assert "Coverage" in indicator_names
            assert "Conversions" in indicator_names
            assert "Reviews" in indicator_names
            assert "WhatsApp Discipline" in indicator_names

            weights = data["weights"]
            assert pytest.approx(sum(weights.values()), abs=0.001) == 1.0

            assert len(data["team_benchmark_radar_values"]) == 6
            assert data["total_reps_evaluated"] >= 20

            # Verify individual rep weighted composite calculation
            for rep in data["scorecards"]:
                k = rep["kpi_breakdown"]
                expected_overall = round(
                    k["sales_score"] * 0.30
                    + k["collections_score"] * 0.20
                    + k["coverage_score"] * 0.15
                    + k["conversions_score"] * 0.15
                    + k["reviews_score"] * 0.10
                    + k["whatsapp_discipline_score"] * 0.10,
                    2,
                )
                assert rep["overall_score"] == pytest.approx(expected_overall, abs=0.01)
                assert 0.0 <= rep["overall_score"] <= 100.0
                assert len(rep["radar_values"]) == 6
                assert rep["performance_tier"] in [
                    "TOP_PERFORMER",
                    "SOLID_PERFORMER",
                    "NEEDS_IMPROVEMENT",
                    "CRITICAL",
                ]

    async def test_ctc_scatter_plot_and_quadrants(self) -> None:
        """Assert /ctc-scatter-plot computes fully loaded CTC and 4 quadrants."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            warmup = await client.get("/api/v1/hr/ctc-scatter-plot?period=2024-M03")
            assert warmup.status_code == 200

            start = time.perf_counter()
            response = await client.get("/api/v1/hr/ctc-scatter-plot?period=2024-M03")
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            assert response.status_code == 200
            assert elapsed_ms < 50.0, f"API response exceeded 50ms SLA: took {elapsed_ms:.2f}ms"

            data = response.json()
            assert data["total_reps"] >= 20
            assert data["median_ctc_bdt"] > 0
            assert data["median_contribution_margin_bdt"] > 0
            assert len(data["quadrants"]) == 4

            quad_codes = [q["quadrant"] for q in data["quadrants"]]
            assert "STARS" in quad_codes
            assert "HEAVY_HITTERS" in quad_codes
            assert "RAMP_UP" in quad_codes
            assert "VALUE_DESTROYERS" in quad_codes

            # Verify fully-loaded CTC formula for each rep
            for pt in data["points"]:
                expected_ctc = round(
                    pt["base_salary_bdt"]
                    + pt["tada_bdt"]
                    + pt["incentives_bdt"]
                    + pt["overhead_bdt"],
                    2,
                )
                assert pt["fully_loaded_ctc_bdt"] == pytest.approx(expected_ctc, abs=0.01)
                assert pt["roi_multiple"] > 0
                expected_coords = [
                    pt["fully_loaded_ctc_bdt"],
                    pt["contribution_margin_bdt"],
                ]
                assert pt["coordinates"] == expected_coords
                assert pt["quadrant"] in [
                    "STARS",
                    "HEAVY_HITTERS",
                    "RAMP_UP",
                    "VALUE_DESTROYERS",
                ]
