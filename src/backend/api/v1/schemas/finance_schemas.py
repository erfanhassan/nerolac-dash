"""Pydantic v2 Schemas for Module 1: Finance Control Center API.

Defines request/response contracts for:
1. /segment-pnl: GL 10000–10017 actuals aggregated by division, segment, and SKU.
2. /supplier-variance: Vendor purchase price spreads flagging >5% variances.
3. /simulate-cashflow: Real-time <50ms Redis cash flow simulations (AR %, DPO, CapEx).
4. /ar-ap-aging: Receivables and payables grouped in 0–30, 31–60, 61–90, and 90+ day buckets.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# 1. Segment P&L Models (Waterfall & TanStack Tree Grid)
# ============================================================================


class WaterfallDataPoint(BaseModel):
    """Data item specifically structured for Apache ECharts Waterfall rendering."""

    name: str = Field(..., description="Step label (e.g. Gross Revenue, COGS, EBITDA)")
    value: float = Field(..., description="Signed or delta value in BDT")
    is_intermediate: bool = Field(
        False, description="True if subtotal (Gross Margin, EBITDA, Net Profit)"
    )
    is_negative: bool = Field(False, description="True for expense deductions")


class PnLTreeGridNode(BaseModel):
    """Hierarchical node for TanStack Tree Grid (Division -> Segment -> SKU)."""

    id: str = Field(..., description="Unique node identifier for tree grid")
    label: str = Field(..., description="Row display title")
    level: int = Field(..., description="Depth level: 0=Division, 1=Segment, 2=SKU/Ledger")
    category: str = Field(..., description="REVENUE, COGS, OPEX, NON_OPERATING, SUMMARY")
    volume_liters: float = Field(0.0, description="Volume in Liters (tabular-nums)")
    revenue_bdt: float = Field(0.0, description="Net Revenue in BDT")
    cogs_bdt: float = Field(0.0, description="Cost of Goods Sold in BDT")
    gross_margin_bdt: float = Field(0.0, description="Gross Margin in BDT")
    gross_margin_pct: float = Field(0.0, description="Gross Margin Percentage")
    opex_bdt: float = Field(0.0, description="Operating Expenses in BDT")
    ebitda_bdt: float = Field(0.0, description="EBITDA in BDT")
    ebitda_pct: float = Field(0.0, description="EBITDA Percentage")
    children: list[PnLTreeGridNode] = Field(
        default_factory=list, description="Sub-nodes for tree grid expansion"
    )


class SegmentPnLResponse(BaseModel):
    """Aggregated financial P&L response adhering to Bright Light Corporate Mode."""

    fiscal_year: int = Field(..., description="Fiscal year analyzed")
    fiscal_month: int = Field(..., description="Fiscal month analyzed")
    depot_id: str | None = Field(None, description="Depot filter or ALL")
    gross_revenue_bdt: float = Field(..., description="GL 10000 Gross Sales")
    discounts_bdt: float = Field(..., description="GL 10001 Sales Discounts")
    net_revenue_bdt: float = Field(..., description="Net Revenue (10000 - 10001)")
    cogs_bdt: float = Field(..., description="Total COGS (GL 10002–10007)")
    gross_margin_bdt: float = Field(..., description="Gross Profit (Net Revenue - COGS)")
    gross_margin_pct: float = Field(..., description="Gross Margin Ratio (%)")
    opex_bdt: float = Field(..., description="Operating Expenses (GL 10008–10014)")
    ebitda_bdt: float = Field(..., description="Operating Profit (EBITDA)")
    ebitda_pct: float = Field(..., description="EBITDA Margin Ratio (%)")
    non_operating_bdt: float = Field(..., description="Finance & Taxes (GL 10015–10017)")
    net_profit_bdt: float = Field(..., description="Final Net Income (EBITDA - Non-Operating)")
    net_profit_pct: float = Field(..., description="Net Profit Ratio (%)")
    gl_code_summary: dict[str, float] = Field(
        default_factory=dict,
        description="Lookup map of actuals for individual GL accounts 10000–10017",
    )
    waterfall_series: list[WaterfallDataPoint] = Field(
        ..., description="Series items formatted for Apache ECharts Waterfall chart"
    )
    tree_grid_rows: list[PnLTreeGridNode] = Field(
        ..., description="Hierarchical tree rows for TanStack Tree Grid component"
    )
    cached: bool = Field(False, description="True if fulfilled from Redis DB 0 sub-50ms cache")


# ============================================================================
# 2. Supplier Variance Models
# ============================================================================


class SupplierPurchaseRecord(BaseModel):
    """Individual vendor purchase with variance analysis against commodity benchmark."""

    procurement_id: int
    material_code: str
    material_name: str
    supplier_name: str
    depot_id: str
    purchase_date: date
    quantity: float
    unit_cost_bdt: float
    benchmark_unit_cost_bdt: float
    min_unit_cost_bdt: float
    max_unit_cost_bdt: float
    variance_pct: float = Field(
        ..., description="Spread percentage relative to benchmark/lowest unit cost"
    )
    is_flagged: bool = Field(..., description="True if variance spread > 5.0%")
    severity_color: str = Field(
        ...,
        description="#D97706 (Warm Amber) if variance > 5%, otherwise #475569 (Slate)",
    )


class SupplierVarianceResponse(BaseModel):
    """Collection of supplier price variances across raw material procurement register."""

    total_materials_evaluated: int
    flagged_variance_count: int
    max_variance_pct: float
    records: list[SupplierPurchaseRecord]
    cached: bool = Field(False, description="True if fulfilled from Redis DB 0 query cache")


# ============================================================================
# 3. Cash Flow Simulation Models
# ============================================================================


class CashflowSimulationRequest(BaseModel):
    """Input parameters for interactive Cash Flow Simulator sliders."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ar_collection_pct: float = Field(
        85.0,
        ge=0.0,
        le=100.0,
        description="AR collection efficiency percentage slider (0%–100%)",
    )
    dpo_days: int = Field(
        45,
        ge=15,
        le=180,
        description="Days Payable Outstanding (DPO) slider (15–180 days)",
    )
    capex_bdt: float = Field(
        5000000.0,
        ge=0.0,
        description="Planned Capital Expenditure in BDT slider",
    )
    forecast_months: int = Field(
        6,
        ge=1,
        le=24,
        description="Forecast simulation horizon in months (default 6)",
    )


class MonthlyCashflowProjection(BaseModel):
    """Detailed monthly cash flow position under slider scenario."""

    month_index: int
    month_label: str
    opening_balance_bdt: float
    ar_collected_bdt: float
    cash_sales_bdt: float
    total_inflow_bdt: float
    ap_disbursed_bdt: float
    opex_disbursed_bdt: float
    capex_disbursed_bdt: float
    total_outflow_bdt: float
    net_cashflow_bdt: float
    closing_balance_bdt: float


CashflowMonthlyProjection = MonthlyCashflowProjection


class CashflowSimulationResponse(BaseModel):
    """Simulation outcome guaranteed <50ms response time."""

    execution_time_ms: float = Field(..., description="Measured execution time in milliseconds")
    ar_collection_pct: float
    dpo_days: int
    capex_bdt: float
    forecast_months: int
    initial_cash_buffer_bdt: float
    ending_cash_balance_bdt: float
    minimum_cash_trough_bdt: float
    working_capital_burn_bdt: float
    liquidity_status: str = Field(..., description="HEALTHY, CAUTION, or CRITICAL")
    monthly_projections: list[MonthlyCashflowProjection]


# ============================================================================
# 4. AR / AP Aging Models
# ============================================================================


class AgingBucketSummary(BaseModel):
    """Aggregate totals for a specific aging interval."""

    bucket_label: str = Field(..., description="0-30 Days, 31-60 Days, 61-90 Days, 90+ Days")
    bucket_code: str = Field(..., description="days_1_30, days_31_60, days_61_90, days_90_plus")
    ar_amount_bdt: float = Field(..., description="Accounts Receivable in BDT")
    ap_amount_bdt: float = Field(..., description="Accounts Payable in BDT")
    net_exposure_bdt: float = Field(..., description="Net Working Capital Gap (AR - AP)")
    risk_level: str = Field(..., description="LOW, MODERATE, HIGH, CRITICAL")


class AgingEntityRecord(BaseModel):
    """Individual dealer receivable or supplier payable ledger balance."""

    aging_id: int
    entry_type: str = Field(..., description="RECEIVABLE or PAYABLE")
    entity_code: str = Field(..., description="Dealer code or Supplier code")
    entity_name: str
    depot_id: str
    current_amount_bdt: float
    days_1_30_bdt: float
    days_31_60_bdt: float
    days_61_90_bdt: float
    days_90_plus_bdt: float
    total_outstanding_bdt: float
    as_of_date: date


class ARAPAgingResponse(BaseModel):
    """Sorted 0-30, 31-60, 61-90, 90+ days aging overview."""

    as_of_date: date
    depot_id: str | None = Field(None, description="Depot filter or ALL")
    total_receivables_bdt: float
    total_payables_bdt: float
    net_working_capital_bdt: float
    dso_days: float = Field(..., description="Days Sales Outstanding estimate")
    dpo_days: float = Field(..., description="Days Payable Outstanding estimate")
    buckets: list[AgingBucketSummary]
    entity_records: list[AgingEntityRecord]
    cached: bool = Field(False, description="True if fulfilled from Redis DB 0 query cache")
