"""FastAPI Endpoints for Module 3: Supply Chain Control Center.

Exposes:
1. GET /api/v1/supply-chain/forecast: Month 0 firm SAP orders + Months +1/+2 ML predictions
   with 80% and 95% confidence bands (ECharts Demand Fan Chart).
2. GET /api/v1/supply-chain/mrp-proposals: Automated raw material purchase reorder indents
   and safety stock alerts via BOM explosion.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.backend.api.v1.schemas.supply_chain_schemas import (
    DemandForecastResponse,
    MRPProposalsResponse,
)
from src.backend.ml.demand_forecaster import (
    DemandForecaster,
    get_demand_forecaster,
)

logger = logging.getLogger("nerolac.api.v1.supply_chain")

router = APIRouter(prefix="/supply-chain", tags=["Supply Chain Control Center"])


@router.get(
    "/forecast",
    response_model=DemandForecastResponse,
    summary="Demand Fan Chart Forecasting (Month 0 + M+1/M+2 ML Predictions)",
    description=(
        "Returns Month 0 firm SAP orders + Months +1 and +2 ML predictions with "
        "80% and 95% confidence bands from an ensemble of LightGBM and Prophet."
    ),
)
async def get_demand_forecast(
    depot_id: Annotated[
        str | None,
        Query(description="Regional depot code (e.g. DEPOT_01) or ALL"),
    ] = None,
    sku_id: Annotated[
        str | None,
        Query(description="Paint SKU code (e.g. SKU_DEC_01) or ALL"),
    ] = None,
    forecaster: DemandForecaster = Depends(get_demand_forecaster),
) -> DemandForecastResponse:
    """Return historical actuals + Month 0 firm orders + M+1/M+2 ML ensemble predictions."""
    return await forecaster.get_demand_forecast(depot_id=depot_id, sku_id=sku_id)


@router.get(
    "/mrp-proposals",
    response_model=MRPProposalsResponse,
    summary="Material Requirements Planning (MRP) Purchase Indents & Safety Stock Alerts",
    description=(
        "Generates automated raw material purchase reorder indents and safety stock "
        "alerts derived from forecasted demand exploded through product Bills of Materials (BOM)."
    ),
)
async def get_mrp_proposals(
    depot_id: Annotated[
        str | None,
        Query(description="Regional depot code (e.g. DEPOT_01) or ALL"),
    ] = None,
    category: Annotated[
        str | None,
        Query(description="Raw material category (TIO2, RESIN, SOLVENT, EXTENDER) or ALL"),
    ] = None,
    alert_level: Annotated[
        str | None,
        Query(description="Alert status filter (CRITICAL_STOCKOUT_RISK, REORDER_REQUIRED)"),
    ] = None,
    forecaster: DemandForecaster = Depends(get_demand_forecaster),
) -> MRPProposalsResponse:
    """Return automated raw material purchase reorder indents and safety stock alerts."""
    return await forecaster.get_mrp_proposals(
        depot_id=depot_id, category=category, alert_level=alert_level
    )
