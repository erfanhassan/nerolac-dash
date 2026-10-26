"""Pydantic v2 Schemas for Module 3: Supply Chain Control Center API.

Contracts for:
1. /forecast: Month 0 firm SAP orders + Months +1/+2 ML predictions with 80% & 95% confidence bands.
2. /mrp-proposals: Automated raw material purchase reorder indents and safety stock alerts.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# 1. Demand Forecasting & Fan Chart Schemas
# ============================================================================


class TimeSeriesDataPoint(BaseModel):
    """Single monthly demand or forecast data point in Liters."""

    model_config = ConfigDict(populate_by_name=True)

    period: str = Field(..., description="Month identifier (e.g. '2024-01' or 'M+1')")
    period_label: str = Field(..., description="Display label (e.g. 'Jan 2024', 'Apr 2024 (M+1)')")
    actual_liters: float | None = Field(None, description="Realized sales volume in Liters")
    is_firm_order: bool = Field(False, description="True for Month 0 firm SAP committed order")
    forecast_liters: float | None = Field(None, description="Ensemble ML forecasted liters")
    lower_80: float | None = Field(None, description="Lower bound of 80% confidence interval")
    upper_80: float | None = Field(None, description="Upper bound of 80% confidence interval")
    lower_95: float | None = Field(None, description="Lower bound of 95% confidence interval")
    upper_95: float | None = Field(None, description="Upper bound of 95% confidence interval")


class DemandForecastResponse(BaseModel):
    """Demand forecasting payload pre-formatted for Apache ECharts Fan Chart rendering."""

    depot_id: str = Field("ALL", description="Selected regional depot or ALL")
    depot_name: str = Field("All Hubs (Bangladesh Operations)", description="Hub title")
    sku_id: str = Field("ALL", description="Selected SKU or ALL catalog")
    sku_name: str = Field("All Product Categories", description="Product title")
    unit_of_measure: str = Field("LITERS", description="Volume unit")
    model_name: str = Field(
        "Ensemble (LightGBM 55% + Prophet 45%)",
        description="ML algorithm identifier",
    )
    training_period_months: int = Field(24, description="Training historical depth")
    mape_score_pct: float = Field(..., description="Mean Absolute Percentage Error on test fold")
    month_0_firm_liters: float = Field(..., description="Current Month 0 firm committed SAP order")
    month_1_forecast_liters: float = Field(..., description="Month +1 ML projected volume")
    month_2_forecast_liters: float = Field(..., description="Month +2 ML projected volume")
    series: list[TimeSeriesDataPoint] = Field(
        ..., description="Sequential monthly fan chart points"
    )


# ============================================================================
# 2. MRP Reorder Proposals & Safety Stock Alerts Schemas
# ============================================================================


class MRPProposalItem(BaseModel):
    """Raw material procurement indent and safety stock action line item."""

    model_config = ConfigDict(populate_by_name=True)

    indent_id: str = Field(..., description="Unique purchase requisition indent code")
    material_code: str = Field(..., description="SAP Material Master code (e.g. RM_TIO2_RUTILE)")
    material_name: str = Field(..., description="Human-readable raw material title")
    category: str = Field(..., description="TIO2, RESIN, SOLVENT, EXTENDER, ADDITIVE, PACKAGING")
    current_stock_kg: float = Field(..., description="Current warehouse physical stock in KG")
    safety_stock_kg: float = Field(..., description="Calculated safety stock threshold in KG")
    lead_time_days: int = Field(..., description="Supplier replenishment lead time in days")
    gross_requirement_kg: float = Field(
        ..., description="Total raw material required for 2-month demand"
    )
    net_shortfall_kg: float = Field(..., description="Net deficit considering current buffer stock")
    recommended_reorder_kg: float = Field(
        ..., description="Recommended purchase order quantity in KG"
    )
    unit_cost_bdt: float = Field(..., description="Current commodity price in BDT per KG")
    estimated_po_cost_bdt: float = Field(..., description="Total purchase commitment in BDT")
    supplier_name: str = Field(..., description="Primary contracted vendor")
    country_of_origin: str = Field(..., description="Manufacturing country / domestic")
    alert_level: str = Field(
        ...,
        description="Status: CRITICAL_STOCKOUT_RISK, REORDER_REQUIRED, ADEQUATE_STOCK, OVERSTOCKED",
    )
    action_notes: str = Field(..., description="Procurement executive guidance")


class MRPProposalsResponse(BaseModel):
    """Aggregated Material Requirements Planning proposal schedule with inline export data."""

    evaluation_date: str = Field(..., description="Date of calculation (YYYY-MM-DD)")
    total_materials_monitored: int = Field(..., description="Count of monitored BOM raw materials")
    critical_alerts_count: int = Field(..., description="Items with stock below safety threshold")
    total_recommended_po_bdt: float = Field(
        ..., description="Total committed purchase value across all indents"
    )
    proposals: list[MRPProposalItem] = Field(..., description="List of raw material indent items")
