"""FastAPI Endpoints for Document Generation & Reporting.

Exposes:
1. GET /api/v1/reports/pdf: Compiles executive briefing PDFs (Segment P&L summaries,
   HR capacity justifications) with embedded ECharts PNG renders.
2. POST /api/v1/reports/pdf: Accepts client-rendered ECharts PNG (base64) and compiles briefing PDF.
3. GET /api/v1/reports/excel: Exports formatted .xlsx purchase indents and trial balance sheets
   with live formulas, header styling, and tabular-nums formatting.
4. POST /api/v1/reports/excel: Filtered workbook export.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.backend.api.v1.services.finance_service import (
    GL_CODE_METADATA,
    FinanceCalculationService,
    get_finance_service,
)
from src.backend.api.v1.services.hr_service import (
    HRWorkforceService,
    get_hr_service,
)
from src.backend.database.session_router import get_read_session
from src.backend.ml.demand_forecaster import (
    DemandForecaster,
    get_demand_forecaster,
)
from src.backend.reporting.excel_generator import (
    ExcelReportExporter,
    get_excel_report_exporter,
)
from src.backend.reporting.pdf_generator import (
    PDFReportGenerator,
    get_pdf_report_generator,
)

logger = logging.getLogger("nerolac.api.v1.reports")

router = APIRouter(prefix="/reports", tags=["Reporting & Document Generation"])


class PDFReportRequest(BaseModel):
    """Payload schema for generating executive briefing PDFs with optional chart renders."""

    report_type: str = Field(
        "segment_pnl",
        description="Type of report: 'segment_pnl' or 'hr_capacity'",
    )
    fiscal_year: int = Field(2024, description="Fiscal year (e.g. 2024)")
    fiscal_month: int = Field(3, description="Fiscal month (1-12)")
    depot_id: str | None = Field(None, description="Depot identifier or None for ALL")
    chart_image_base64: str | None = Field(
        None,
        description="Base64-encoded PNG chart render from ECharts frontend instance",
    )


class ExcelReportRequest(BaseModel):
    """Payload schema for exporting formatted .xlsx spreadsheets."""

    report_type: str = Field(
        "purchase_indents",
        description="Type of export: 'purchase_indents' or 'trial_balance'",
    )
    fiscal_year: int = Field(2024, description="Fiscal year (e.g. 2024)")
    fiscal_month: int = Field(3, description="Fiscal month (1-12)")
    depot_id: str | None = Field(None, description="Depot identifier or None for ALL")
    category: str | None = Field(None, description="Raw material category filter")
    alert_level: str | None = Field(None, description="Procurement alert status filter")


async def _get_trial_balance_accounts(
    fiscal_year: int,
    fiscal_month: int,
    depot_id: str | None,
    finance_service: FinanceCalculationService,
) -> list[dict[str, Any]]:
    """Retrieve trial balance ledger rows from sap_trial_balances or compute from PnL."""
    accounts: list[dict[str, Any]] = []

    try:
        async with get_read_session() as session:
            depot_filter = "AND depot_id = :depot_id" if depot_id else ""
            query = text(f"""
                SELECT
                    gl_code,
                    segment_code,
                    SUM(amount) as total_amount
                FROM nerolac_ops.sap_trial_balances
                WHERE fiscal_year = :fiscal_year
                  AND fiscal_month = :fiscal_month
                  AND gl_code >= '10000' AND gl_code <= '10017'
                  {depot_filter}
                GROUP BY gl_code, segment_code
                ORDER BY gl_code, segment_code;
            """)
            params: dict[str, Any] = {"fiscal_year": fiscal_year, "fiscal_month": fiscal_month}
            if depot_id:
                params["depot_id"] = depot_id

            res = await session.execute(query, params)
            rows = res.fetchall()

            if rows:
                for row in rows:
                    gl = str(row[0]).strip()
                    seg = str(row[1]).strip()
                    amt = float(row[2])
                    meta = GL_CODE_METADATA.get(
                        gl,
                        {"name": f"GL Account {gl}", "category": "GENERAL", "type": "DEBIT"},
                    )
                    is_credit = meta["type"] == "CREDIT"
                    accounts.append(
                        {
                            "gl_code": gl,
                            "account_name": meta["name"],
                            "category": meta["category"],
                            "segment": seg,
                            "debit": 0.0 if is_credit else amt,
                            "credit": amt if is_credit else 0.0,
                        }
                    )
                return accounts
    except Exception as exc:
        logger.warning("Direct trial balance DB query failed: %s. Using aggregated fallback.", exc)

    # Fallback using P&L summary data
    pnl = await finance_service.get_segment_pnl(
        fiscal_year=fiscal_year, fiscal_month=fiscal_month, depot_id=depot_id
    )

    gross_rev = pnl.gross_revenue_bdt
    discounts = pnl.discounts_bdt
    cogs = pnl.cogs_bdt
    opex = pnl.opex_bdt

    accounts = [
        {
            "gl_code": "10000",
            "account_name": GL_CODE_METADATA["10000"]["name"],
            "category": "REVENUE",
            "segment": "Architectural Coatings",
            "debit": 0.0,
            "credit": gross_rev,
        },
        {
            "gl_code": "10001",
            "account_name": GL_CODE_METADATA["10001"]["name"],
            "category": "REVENUE",
            "segment": "Commercial Trade",
            "debit": discounts,
            "credit": 0.0,
        },
        {
            "gl_code": "10002",
            "account_name": GL_CODE_METADATA["10002"]["name"],
            "category": "COGS",
            "segment": "Direct Production",
            "debit": round(cogs * 0.72, 2),
            "credit": 0.0,
        },
        {
            "gl_code": "10003",
            "account_name": GL_CODE_METADATA["10003"]["name"],
            "category": "COGS",
            "segment": "Factory Operations",
            "debit": round(cogs * 0.15, 2),
            "credit": 0.0,
        },
        {
            "gl_code": "10004",
            "account_name": GL_CODE_METADATA["10004"]["name"],
            "category": "COGS",
            "segment": "Plant Operations",
            "debit": round(cogs * 0.13, 2),
            "credit": 0.0,
        },
        {
            "gl_code": "10008",
            "account_name": GL_CODE_METADATA["10008"]["name"],
            "category": "OPEX",
            "segment": "Logistics & Supply Chain",
            "debit": round(opex * 0.35, 2),
            "credit": 0.0,
        },
        {
            "gl_code": "10009",
            "account_name": GL_CODE_METADATA["10009"]["name"],
            "category": "OPEX",
            "segment": "Depot Operations",
            "debit": round(opex * 0.25, 2),
            "credit": 0.0,
        },
        {
            "gl_code": "10011",
            "account_name": GL_CODE_METADATA["10011"]["name"],
            "category": "OPEX",
            "segment": "Field Sales Force",
            "debit": round(opex * 0.40, 2),
            "credit": 0.0,
        },
    ]
    return accounts


@router.get(
    "/pdf",
    summary="Compile Executive Briefing PDF Report",
    description=(
        "Compiles an executive briefing PDF (Segment P&L summary or HR capacity justification) "
        "with embedded ECharts PNG renders and corporate styling."
    ),
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Executive Briefing PDF Document",
        }
    },
)
async def generate_pdf_report(
    report_type: Annotated[
        str,
        Query(
            description="Type of report: 'segment_pnl' or 'hr_capacity'",
            pattern="^(segment_pnl|hr_capacity)$",
        ),
    ] = "segment_pnl",
    fiscal_year: Annotated[int, Query(description="Fiscal year analyzed")] = 2024,
    fiscal_month: Annotated[int, Query(description="Fiscal month analyzed (1-12)")] = 3,
    depot_id: Annotated[str | None, Query(description="Depot filter or ALL")] = None,
    pdf_generator: PDFReportGenerator = Depends(get_pdf_report_generator),
    finance_service: FinanceCalculationService = Depends(get_finance_service),
    hr_service: HRWorkforceService = Depends(get_hr_service),
) -> Response:
    """Generate and download server-side executive briefing PDF."""
    if report_type == "segment_pnl":
        pnl = await finance_service.get_segment_pnl(
            fiscal_year=fiscal_year,
            fiscal_month=fiscal_month,
            depot_id=depot_id,
        )
        pdf_bytes = pdf_generator.generate_segment_pnl_pdf(pnl.model_dump())
        filename = f"nerolac_segment_pnl_fy{fiscal_year}_m{fiscal_month:02d}.pdf"

    elif report_type == "hr_capacity":
        capacity = await hr_service.get_manpower_capacity(depot_id=depot_id)
        pdf_bytes = pdf_generator.generate_hr_capacity_pdf(capacity.model_dump())
        filename = "nerolac_hr_workforce_capacity_briefing.pdf"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported report type '{report_type}'. Supported: segment_pnl, hr_capacity.",
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/pdf",
    summary="Compile Executive Briefing PDF with Client ECharts Render",
    description=(
        "Accepts a base64-encoded ECharts PNG render from the frontend and embeds it directly "
        "into the executive briefing PDF document."
    ),
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Executive Briefing PDF Document with embedded ECharts image",
        }
    },
)
async def generate_pdf_report_with_chart(
    req: PDFReportRequest,
    pdf_generator: PDFReportGenerator = Depends(get_pdf_report_generator),
    finance_service: FinanceCalculationService = Depends(get_finance_service),
    hr_service: HRWorkforceService = Depends(get_hr_service),
) -> Response:
    """Generate executive briefing PDF embedding client-provided ECharts PNG render."""
    if req.report_type == "segment_pnl":
        pnl = await finance_service.get_segment_pnl(
            fiscal_year=req.fiscal_year,
            fiscal_month=req.fiscal_month,
            depot_id=req.depot_id,
        )
        pdf_bytes = pdf_generator.generate_segment_pnl_pdf(
            pnl.model_dump(),
            chart_image=req.chart_image_base64,
        )
        filename = f"nerolac_segment_pnl_fy{req.fiscal_year}_m{req.fiscal_month:02d}.pdf"

    elif req.report_type == "hr_capacity":
        capacity = await hr_service.get_manpower_capacity(depot_id=req.depot_id)
        pdf_bytes = pdf_generator.generate_hr_capacity_pdf(
            capacity.model_dump(),
            chart_image=req.chart_image_base64,
        )
        filename = "nerolac_hr_workforce_capacity_briefing.pdf"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported report type '{req.report_type}'.",
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/excel",
    summary="Export Formatted Excel Spreadsheet",
    description=(
        "Exports formatted Microsoft Excel (.xlsx) workbooks for purchase indents "
        "or trial balance sheets complete with formulas, header styling, and tabular-nums."
    ),
    responses={
        200: {
            "content": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}},
            "description": "Formatted Excel Workbook (.xlsx)",
        }
    },
)
async def export_excel_report(
    report_type: Annotated[
        str,
        Query(
            description="Type of export: 'purchase_indents' or 'trial_balance'",
            pattern="^(purchase_indents|trial_balance)$",
        ),
    ] = "purchase_indents",
    fiscal_year: Annotated[int, Query(description="Fiscal year")] = 2024,
    fiscal_month: Annotated[int, Query(description="Fiscal month (1-12)")] = 3,
    depot_id: Annotated[str | None, Query(description="Depot filter or ALL")] = None,
    category: Annotated[str | None, Query(description="Raw material category filter")] = None,
    alert_level: Annotated[str | None, Query(description="Reorder alert filter")] = None,
    excel_exporter: ExcelReportExporter = Depends(get_excel_report_exporter),
    finance_service: FinanceCalculationService = Depends(get_finance_service),
    forecaster: DemandForecaster = Depends(get_demand_forecaster),
) -> Response:
    """Generate and download formatted Excel spreadsheet with live formulas."""
    if report_type == "purchase_indents":
        mrp_resp = await forecaster.get_mrp_proposals(
            category=category,
            alert_level=alert_level,
        )
        proposals_data = [p.model_dump() for p in mrp_resp.proposals]
        xlsx_bytes = excel_exporter.generate_purchase_indents_excel(
            proposals=proposals_data,
            metadata={"evaluation_date": mrp_resp.evaluation_date},
        )
        filename = "nerolac_purchase_indents.xlsx"

    elif report_type == "trial_balance":
        accounts = await _get_trial_balance_accounts(
            fiscal_year=fiscal_year,
            fiscal_month=fiscal_month,
            depot_id=depot_id,
            finance_service=finance_service,
        )
        xlsx_bytes = excel_exporter.generate_trial_balance_excel(
            accounts=accounts,
            metadata={
                "fiscal_year": fiscal_year,
                "fiscal_month": fiscal_month,
                "depot_id": depot_id,
            },
        )
        filename = f"nerolac_trial_balance_fy{fiscal_year}_m{fiscal_month:02d}.xlsx"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported report type '{report_type}'.",
        )

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/excel",
    summary="Filtered Export of Formatted Excel Spreadsheet",
    description="Filtered export endpoint for purchase indents or trial balance spreadsheets.",
    responses={
        200: {
            "content": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}},
            "description": "Formatted Excel Workbook (.xlsx)",
        }
    },
)
async def export_excel_report_filtered(
    req: ExcelReportRequest,
    excel_exporter: ExcelReportExporter = Depends(get_excel_report_exporter),
    finance_service: FinanceCalculationService = Depends(get_finance_service),
    forecaster: DemandForecaster = Depends(get_demand_forecaster),
) -> Response:
    """Generate filtered Excel report."""
    return await export_excel_report(
        report_type=req.report_type,
        fiscal_year=req.fiscal_year,
        fiscal_month=req.fiscal_month,
        depot_id=req.depot_id,
        category=req.category,
        alert_level=req.alert_level,
        excel_exporter=excel_exporter,
        finance_service=finance_service,
        forecaster=forecaster,
    )
