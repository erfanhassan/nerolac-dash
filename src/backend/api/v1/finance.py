"""FastAPI Endpoints for Module 1: Finance Control Center.

Exposes:
1. GET /api/v1/finance/segment-pnl: GL 10000–10017 actuals aggregated by division/segment/SKU.
2. GET /api/v1/finance/supplier-variance: Unit purchase spreads across vendors, flagging >5%.
3. POST /api/v1/finance/simulate-cashflow: Real-time <50ms cash flow simulations (AR %, DPO, CapEx).
   GET /api/v1/finance/simulate-cashflow: Convenience endpoint for real-time frontend sliders.
4. GET /api/v1/finance/ar-ap-aging: Receivables and payables in 0–30, 31–60, 61–90, 90+ buckets.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.api.v1.schemas.finance_schemas import (
    ARAPAgingResponse,
    CashflowSimulationRequest,
    CashflowSimulationResponse,
    SegmentPnLResponse,
    SupplierVarianceResponse,
)
from src.backend.api.v1.services.finance_service import (
    FinanceCalculationService,
    get_finance_service,
)
from src.backend.database.session_router import provide_read_session

logger = logging.getLogger("nerolac.api.v1.finance")

router = APIRouter(prefix="/finance", tags=["Finance Control Center"])


@router.get(
    "/segment-pnl",
    response_model=SegmentPnLResponse,
    summary="Segment P&L (Waterfall & TanStack Tree Grid)",
    description=(
        "Returns SAP trial balance actuals for GL codes 10000–10017 aggregated by division, "
        "segment, and SKU. Pre-formatted for Apache ECharts Waterfall chart and TanStack Tree Grid."
    ),
)
async def get_segment_pnl(
    fiscal_year: Annotated[
        int, Query(description="Fiscal year (e.g. 2024)", ge=2000, le=2100)
    ] = 2024,
    fiscal_month: Annotated[int, Query(description="Fiscal month (1–12)", ge=1, le=12)] = 3,
    depot_id: Annotated[
        str | None, Query(description="Depot filter (e.g. DEPOT_01) or null for all")
    ] = None,
    service: FinanceCalculationService = Depends(get_finance_service),
    db_session: AsyncSession = Depends(provide_read_session),
) -> SegmentPnLResponse:
    """Retrieve sub-50ms cached or aggregated Segment P&L."""
    return await service.get_segment_pnl(
        fiscal_year=fiscal_year,
        fiscal_month=fiscal_month,
        depot_id=depot_id,
        db_session=db_session,
    )


@router.get(
    "/supplier-variance",
    response_model=SupplierVarianceResponse,
    summary="Raw Material Supplier Price Spread Analysis",
    description=(
        "Analyzes raw material unit purchase prices across vendors, computing variance relative to "
        "benchmarks and flagging >5% spreads in warm amber (#D97706)."
    ),
)
async def get_supplier_variance(
    material_code: Annotated[
        str | None, Query(description="Filter by specific raw material code")
    ] = None,
    depot_id: Annotated[str | None, Query(description="Filter by receiving depot")] = None,
    service: FinanceCalculationService = Depends(get_finance_service),
    db_session: AsyncSession = Depends(provide_read_session),
) -> SupplierVarianceResponse:
    """Retrieve raw material supplier price variance analysis."""
    return await service.get_supplier_variance(
        material_code=material_code,
        depot_id=depot_id,
        db_session=db_session,
    )


@router.post(
    "/simulate-cashflow",
    response_model=CashflowSimulationResponse,
    summary="Interactive Real-Time Cash Flow Simulation",
    description=(
        "Executes a real-time <50ms cash flow simulation scenario based on AR collection %, "
        "DPO days, and CapEx slider inputs."
    ),
)
async def simulate_cashflow(
    payload: CashflowSimulationRequest,
    service: FinanceCalculationService = Depends(get_finance_service),
) -> CashflowSimulationResponse:
    """Execute dynamic cash flow scenario simulation (POST body)."""
    return await service.simulate_cashflow(payload)


@router.get(
    "/simulate-cashflow",
    response_model=CashflowSimulationResponse,
    summary="Interactive Cash Flow Simulation (Slider Query Trigger)",
    description="Convenience GET endpoint allowing frontend sliders to trigger real-time updates.",
)
async def simulate_cashflow_get(
    ar_collection_pct: Annotated[
        float, Query(ge=0.0, le=100.0, description="AR collection % (0–100)")
    ] = 85.0,
    dpo_days: Annotated[int, Query(ge=15, le=180, description="DPO days slider (15–180)")] = 45,
    capex_bdt: Annotated[float, Query(ge=0.0, description="Planned CapEx in BDT")] = 5000000.0,
    forecast_months: Annotated[
        int, Query(ge=1, le=24, description="Forecast horizon in months")
    ] = 6,
    service: FinanceCalculationService = Depends(get_finance_service),
) -> CashflowSimulationResponse:
    """Execute dynamic cash flow scenario simulation via query parameters."""
    req = CashflowSimulationRequest(
        ar_collection_pct=ar_collection_pct,
        dpo_days=dpo_days,
        capex_bdt=capex_bdt,
        forecast_months=forecast_months,
    )
    return await service.simulate_cashflow(req)


@router.get(
    "/ar-ap-aging",
    response_model=ARAPAgingResponse,
    summary="Accounts Receivable & Accounts Payable Aging Buckets",
    description=(
        "Returns receivables and payables sorted into 0–30, 31–60, 61–90, and 90+ day buckets, "
        "calculating net working capital gap, DSO, and DPO."
    ),
)
async def get_ar_ap_aging(
    depot_id: Annotated[str | None, Query(description="Filter by depot")] = None,
    service: FinanceCalculationService = Depends(get_finance_service),
    db_session: AsyncSession = Depends(provide_read_session),
) -> ARAPAgingResponse:
    """Retrieve AR / AP Aging buckets and entity details."""
    return await service.get_ar_ap_aging(
        depot_id=depot_id,
        db_session=db_session,
    )
