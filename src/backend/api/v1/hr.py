"""FastAPI Endpoints for Module 2: HR Workforce Intelligence.

Exposes:
1. GET /api/v1/hr/manpower-capacity: 2-Factor Capacity across 39 vacant territories.
2. GET /api/v1/hr/kpi-scorecard: 0–100 weighted index across 6 core KPIs & 6-axis Radar specs.
3. GET /api/v1/hr/ctc-scatter-plot: Fully-loaded CTC vs Margin 4-Quadrant scatter.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.api.v1.schemas.hr_schemas import (
    CTCScatterPlotResponse,
    KPIScorecardResponse,
    ManpowerCapacityResponse,
)
from src.backend.api.v1.services.hr_service import (
    HRWorkforceService,
    get_hr_service,
)
from src.backend.database.session_router import provide_read_session

logger = logging.getLogger("nerolac.api.v1.hr")

router = APIRouter(prefix="/hr", tags=["HR Workforce Intelligence"])


@router.get(
    "/manpower-capacity",
    response_model=ManpowerCapacityResponse,
    summary="2-Factor Capacity across 39 Vacant Territories",
    description=(
        "Calculates 2-Factor capacity combining Sales Capacity (Target / 15L BDT) "
        "and Workload Capacity (Dealers x Freq / 24 Days) for 39 vacant territories "
        "with executive ROI payback metrics."
    ),
)
async def get_manpower_capacity(
    depot_id: Annotated[
        str | None,
        Query(description="Filter by supply hub depot code or ALL"),
    ] = None,
    service: HRWorkforceService = Depends(get_hr_service),
    session: AsyncSession = Depends(provide_read_session),
) -> ManpowerCapacityResponse:
    """Return 2-Factor Capacity models and justification cards for 39 vacant territories."""
    return await service.get_manpower_capacity(depot_id=depot_id, session=session)


@router.get(
    "/kpi-scorecard",
    response_model=KPIScorecardResponse,
    summary="6-Core KPI Scorecard & Radar Dimensions",
    description=(
        "Calculates a 0–100 composite weighted index across 6 core KPIs (Sales %, Collections %, "
        "Coverage, Conversions, Reviews, WhatsApp Discipline) and returns pre-formatted series "
        "for Apache ECharts 6-Axis Radar chart."
    ),
)
async def get_kpi_scorecard(
    assessment_period: Annotated[
        str,
        Query(description="Evaluation period format YYYY-MM or YYYY-Qn"),
    ] = "2024-M03",
    depot_id: Annotated[
        str | None,
        Query(description="Filter by supply hub depot code or ALL"),
    ] = None,
    service: HRWorkforceService = Depends(get_hr_service),
    session: AsyncSession = Depends(provide_read_session),
) -> KPIScorecardResponse:
    """Return 0–100 composite weighted KPI scores and 6-axis radar specs for all sales reps."""
    return await service.get_kpi_scorecard(
        assessment_period=assessment_period,
        depot_id=depot_id,
        session=session,
    )


@router.get(
    "/ctc-scatter-plot",
    response_model=CTCScatterPlotResponse,
    summary="Fully-Loaded CTC vs. Contribution Margin 4-Quadrant Scatter",
    description=(
        "Computes fully-loaded CTC (Base + TA/DA + Incentives + Overhead) vs. Margin "
        "and partitions sales officers into 4 quadrants: Stars, Heavy Hitters, "
        "Ramp-up, and Value Destroyers."
    ),
)
async def get_ctc_scatter_plot(
    period: Annotated[
        str,
        Query(description="Evaluation period format YYYY-MM"),
    ] = "2024-M03",
    depot_id: Annotated[
        str | None,
        Query(description="Filter by supply hub depot code or ALL"),
    ] = None,
    service: HRWorkforceService = Depends(get_hr_service),
    session: AsyncSession = Depends(provide_read_session),
) -> CTCScatterPlotResponse:
    """Return CTC vs Contribution Margin coordinates for Apache ECharts 4-Quadrant Scatter Plot."""
    return await service.get_ctc_scatter_plot(
        period=period,
        depot_id=depot_id,
        session=session,
    )
