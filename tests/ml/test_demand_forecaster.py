"""Unit & Integration Test Suite for Module 3: LightGBM + Prophet ML Forecasting Pipeline.

Verifies:
1. 24-month historical sales logs across 8 depots and stockout preprocessing imputation.
2. LightGBM & Prophet ensemble training and MAPE error validation.
3. Month 0 firm SAP orders + Months +1/+2 predictions with 80% & 95% confidence bands.
4. Material Requirements Planning (MRP) BOM explosion, safety stock calculations, and alerts.
5. FastAPI /forecast and /mrp-proposals sub-50ms execution SLA.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from src.backend.cache.cache_invalidation import get_cache_manager
from src.backend.main import app
from src.backend.ml.demand_forecaster import DemandForecaster, get_demand_forecaster


@pytest.fixture(autouse=True)
async def clear_scm_cache() -> AsyncIterator[None]:
    """Flush relevant SCM query caches before and after each test."""
    cache = get_cache_manager()
    await cache.flush_pattern("dash:scm:*")
    yield
    await cache.flush_pattern("dash:scm:*")


class TestDemandForecasterMLPipeline:
    """Verifies LightGBM + Prophet model training, prediction, and MRP generation."""

    def test_historical_sales_and_stockout_preprocessing(self) -> None:
        """Verify 24-month historical sales data generation and stockout imputation."""
        forecaster = DemandForecaster()
        raw_df = forecaster.generate_24_month_historical_sales()

        assert len(raw_df) > 0
        assert raw_df["depot_id"].nunique() == 8
        assert raw_df["sku_id"].nunique() == 4
        assert raw_df["ds"].dt.to_period("M").nunique() == 24

        # Verify stockouts are flagged
        stockout_count = (raw_df["is_stockout_flag"]).sum()
        assert stockout_count > 0

        # Run stockout imputation
        clean_df = forecaster.preprocess_stockouts(raw_df)
        assert len(clean_df) == len(raw_df)

        # Assert no zero-volume periods remain for stockouts in clean_df
        stockout_rows = clean_df[clean_df["is_stockout_flag"]]
        assert (stockout_rows["quantity_liters"] > 0).all()

    def test_ensemble_model_training_and_mape(self) -> None:
        """Verify training of LightGBM regressor and Prophet time-series models."""
        forecaster = DemandForecaster()
        forecaster.train_models()

        assert forecaster._is_trained is True
        assert forecaster._lgb_model is not None
        assert forecaster._prophet_model is not None
        assert 0.0 < forecaster._mape_score < 10.0

    @pytest.mark.asyncio
    async def test_demand_forecast_predictions_and_confidence_bands(self) -> None:
        """Assert Month 0 firm orders + Months +1/+2 predictions with 80% and 95% bands."""
        forecaster = get_demand_forecaster()
        forecast = await forecaster.get_demand_forecast(depot_id="DEPOT_01", sku_id="ALL")

        assert forecast.depot_id == "DEPOT_01"
        assert forecast.unit_of_measure == "LITERS"
        assert forecast.training_period_months == 24
        assert forecast.month_0_firm_liters > 0
        assert forecast.month_1_forecast_liters > 0
        assert forecast.month_2_forecast_liters > 0

        # Verify sequential time-series series points
        assert len(forecast.series) >= 13

        # Check Month 0 firm order point
        m0_pts = [p for p in forecast.series if p.is_firm_order]
        assert len(m0_pts) == 1
        m0 = m0_pts[0]
        assert m0.actual_liters == forecast.month_0_firm_liters

        # Check Month +1 and Month +2 confidence band hierarchies
        # lower_95 <= lower_80 <= forecast <= upper_80 <= upper_95
        future_pts = [p for p in forecast.series if p.actual_liters is None]
        assert len(future_pts) == 2

        for pt in future_pts:
            assert pt.forecast_liters is not None
            assert pt.lower_80 is not None and pt.upper_80 is not None
            assert pt.lower_95 is not None and pt.upper_95 is not None

            assert pt.lower_95 <= pt.lower_80
            assert pt.lower_80 <= pt.forecast_liters
            assert pt.forecast_liters <= pt.upper_80
            assert pt.upper_80 <= pt.upper_95

    @pytest.mark.asyncio
    async def test_mrp_proposals_bom_explosion_and_alerts(self) -> None:
        """Assert BOM explosion produces raw material purchase indents with alert flags."""
        forecaster = get_demand_forecaster()
        mrp = await forecaster.get_mrp_proposals()

        assert mrp.total_materials_monitored >= 8
        assert mrp.total_recommended_po_bdt > 0
        assert len(mrp.proposals) >= 8

        categories = [p.category for p in mrp.proposals]
        assert "TIO2" in categories
        assert "RESIN" in categories
        assert "SOLVENT" in categories

        # Validate line item metrics
        for p in mrp.proposals:
            assert p.current_stock_kg >= 0
            assert p.safety_stock_kg > 0
            assert p.lead_time_days > 0
            assert p.gross_requirement_kg > 0
            assert p.unit_cost_bdt > 0
            assert p.alert_level in [
                "CRITICAL_STOCKOUT_RISK",
                "REORDER_REQUIRED",
                "ADEQUATE_STOCK",
                "OVERSTOCKED",
            ]
            if p.net_shortfall_kg > 0:
                assert p.recommended_reorder_kg >= p.net_shortfall_kg
                assert p.estimated_po_cost_bdt > 0

    @pytest.mark.asyncio
    async def test_supply_chain_api_endpoints_and_performance(self) -> None:
        """Assert /forecast and /mrp-proposals execute within sub-50ms SLA."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. Warm-up call
            warmup = await client.get("/api/v1/supply-chain/forecast?depot_id=DEPOT_01")
            assert warmup.status_code == 200

            # 2. Performance SLA assertion
            start = time.perf_counter()
            resp = await client.get("/api/v1/supply-chain/forecast?depot_id=DEPOT_01")
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            assert resp.status_code == 200
            assert elapsed_ms < 50.0, f"API response exceeded 50ms SLA: took {elapsed_ms:.2f}ms"

            data = resp.json()
            assert data["depot_id"] == "DEPOT_01"
            assert data["month_0_firm_liters"] > 0
            assert data["month_1_forecast_liters"] > 0

            # 3. Test MRP proposals endpoint
            warmup_mrp = await client.get("/api/v1/supply-chain/mrp-proposals")
            assert warmup_mrp.status_code == 200

            start_mrp = time.perf_counter()
            resp_mrp = await client.get("/api/v1/supply-chain/mrp-proposals")
            elapsed_mrp_ms = (time.perf_counter() - start_mrp) * 1000.0

            assert resp_mrp.status_code == 200
            assert (
                elapsed_mrp_ms < 50.0
            ), f"MRP API response exceeded 50ms SLA: took {elapsed_mrp_ms:.2f}ms"
            mrp_data = resp_mrp.json()
            assert mrp_data["total_materials_monitored"] >= 8
