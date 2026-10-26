"""Pydantic v2 Schemas for Module 2: HR Workforce Intelligence API.

Defines contracts for:
1. /manpower-capacity: 2-Factor Capacity (Sales Revenue Target / 15 Lacs BDT &
   Workload Active Dealers x Visit Frequency / 24 Days) for 39 vacant territories.
2. /kpi-scorecard: 0–100 weighted index across 6 core KPIs (Sales %, Collections %,
   Coverage, Conversions, Reviews, WhatsApp Discipline) & ECharts 6-axis Radar.
3. /ctc-scatter-plot: Fully-loaded CTC (Base + TA/DA + Incentives + Overhead)
   vs. Contribution Margin & ECharts 4-Quadrant classification.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# 1. 2-Factor Capacity & 39 Vacant Territory Justification Models
# ============================================================================


class VacantTerritoryModel(BaseModel):
    """Vacant territory business case with 2-Factor Capacity and ROI payback metrics."""

    model_config = ConfigDict(populate_by_name=True)

    territory_id: str = Field(..., description="Unique territory code (e.g. TERR_V01)")
    territory_code: str = Field(..., description="ERP territory identifier")
    territory_name: str = Field(..., description="Human-readable territory title")
    depot_id: str = Field(..., description="Assigned supply hub depot code")
    depot_name: str = Field(..., description="Regional hub name")
    district: str = Field(..., description="Administrative district of Bangladesh")
    territory_target_bdt: float = Field(
        ..., description="Monthly sales target in BDT (tabular-nums)"
    )
    active_dealers: int = Field(..., description="Count of registered hardware/paint dealers")
    visit_frequency: float = Field(..., description="Monthly required visit frequency per dealer")
    sales_revenue_capacity: float = Field(
        ...,
        description="Territory Target / 15 Lacs BDT (1,500,000 BDT) capacity quotient",
    )
    workload_capacity: float = Field(
        ...,
        description="Active Dealers x Visit Frequency / 24 Days workload quotient",
    )
    combined_capacity: float = Field(
        ..., description="Blended 2-Factor capacity (Sales + Workload / 2)"
    )
    recommended_headcount: int = Field(
        ..., description="Recommended sales officer headcount (minimum 1)"
    )
    current_headcount: int = Field(
        0, description="Active on-ground headcount (0 for vacant territories)"
    )
    gap_headcount: int = Field(..., description="Manpower deficit (Recommended - Current)")
    estimated_monthly_cost_bdt: float = Field(
        ..., description="Total monthly fully loaded CTC per recommended headcount"
    )
    projected_monthly_revenue_bdt: float = Field(
        ..., description="Projected monthly incremental gross sales in BDT"
    )
    projected_contribution_margin_bdt: float = Field(
        ..., description="Projected monthly contribution margin in BDT (after COGS & Freight)"
    )
    roi_payback_months: float = Field(
        ...,
        description="Estimated investment payback period in months (ROI Payback Chip)",
    )
    priority: str = Field(
        "HIGH",
        description="Territory prioritization tier: HIGH, MEDIUM, STRATEGIC",
    )
    justification_summary: str = Field(
        ..., description="Executive narrative justifying territory activation"
    )


class ManpowerCapacityResponse(BaseModel):
    """Summary and complete catalog of 39 Vacant Territories with 2-Factor Capacity."""

    total_vacant_territories: int = Field(
        39, description="Total identified vacant territories across Bangladesh"
    )
    total_recommended_headcount: int = Field(
        ..., description="Sum of recommended sales reps across all 39 territories"
    )
    total_monthly_target_bdt: float = Field(
        ..., description="Combined monthly sales potential across vacant territories"
    )
    total_projected_margin_bdt: float = Field(
        ..., description="Combined projected monthly contribution margin in BDT"
    )
    average_payback_months: float = Field(
        ..., description="Weighted average ROI payback period in months"
    )
    benchmark_sales_capacity_lac_bdt: float = Field(
        15.0, description="Benchmark capacity target in Lacs BDT (1,500,000 BDT)"
    )
    benchmark_working_days: int = Field(24, description="Standard field working days per month")
    territories: list[VacantTerritoryModel] = Field(
        ..., description="List of 39 vacant territories"
    )


# ============================================================================
# 2. KPI Scorecard Models (0–100 Weighted Index & 6-Axis Radar)
# ============================================================================


class KPIScoreBreakdown(BaseModel):
    """Core 6 KPI dimensions evaluated on a 0–100 normalized performance scale."""

    sales_score: float = Field(
        ..., ge=0.0, le=100.0, description="Sales Target vs Actual % (Weight: 30%)"
    )
    collections_score: float = Field(
        ..., ge=0.0, le=100.0, description="Cash/Cheque Collection % (Weight: 20%)"
    )
    coverage_score: float = Field(
        ..., ge=0.0, le=100.0, description="Dealer Beat Route Coverage % (Weight: 15%)"
    )
    conversions_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="New Dealer Onboarding & SKU Conversions % (Weight: 15%)",
    )
    reviews_score: float = Field(
        ..., ge=0.0, le=100.0, description="Quarterly Supervisory Review % (Weight: 10%)"
    )
    whatsapp_discipline_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="WhatsApp Daily Sales & Stock Reporting Discipline % (Weight: 10%)",
    )


class RadarAxisIndicator(BaseModel):
    """ECharts Radar axis dimension spec."""

    name: str = Field(..., description="Axis title")
    max: float = Field(100.0, description="Maximum scale limit")


class EmployeeScorecard(BaseModel):
    """Individual sales rep performance scorecard with 6-axis radar values."""

    employee_id: str = Field(..., description="Unique employee identifier")
    employee_code: str = Field(..., description="ERP staff identifier")
    full_name: str = Field(..., description="Officer full legal name")
    designation: str = Field(..., description="Corporate role title")
    department: str = Field("Sales & Field Operations", description="Functional department")
    depot_id: str = Field(..., description="Base depot code")
    depot_name: str = Field(..., description="Regional depot name")
    territory_name: str = Field(..., description="Assigned sales territory")
    kpi_breakdown: KPIScoreBreakdown = Field(..., description="Raw 0-100 scores for 6 KPIs")
    overall_score: float = Field(
        ..., ge=0.0, le=100.0, description="0–100 composite weighted productivity index"
    )
    performance_tier: str = Field(
        ...,
        description="Tier ranking: TOP_PERFORMER, SOLID_PERFORMER, NEEDS_IMPROVEMENT, CRITICAL",
    )
    radar_values: list[float] = Field(
        ...,
        description=(
            "6-element list in axis order "
            "[Sales, Collections, Coverage, Conversions, Reviews, WhatsApp]"
        ),
    )


class KPIScorecardResponse(BaseModel):
    """Complete KPI scorecard response for team and individual radar analytics."""

    assessment_period: str = Field(..., description="Evaluation cycle (e.g. 2024-M03 / Q1)")
    weights: dict[str, float] = Field(
        ...,
        description="Weight distribution across 6 core KPIs summing to 1.0",
    )
    indicators: list[RadarAxisIndicator] = Field(
        ..., description="ECharts radar chart indicator definitions"
    )
    team_benchmark_radar_values: list[float] = Field(
        ..., description="Depot/Team median scores for radar comparison"
    )
    total_reps_evaluated: int = Field(..., description="Count of evaluated sales officers")
    top_performers_count: int = Field(..., description="Reps scoring >= 85.0")
    solid_performers_count: int = Field(..., description="Reps scoring 70.0 - 84.9")
    needs_improvement_count: int = Field(..., description="Reps scoring 55.0 - 69.9")
    critical_count: int = Field(..., description="Reps scoring < 55.0")
    scorecards: list[EmployeeScorecard] = Field(..., description="List of employee scorecards")


# ============================================================================
# 3. CTC vs. Contribution Margin (4-Quadrant Scatter Plot) Models
# ============================================================================


class CTCScatterPoint(BaseModel):
    """Single sales officer coordinate point in CTC vs Contribution Margin space."""

    employee_id: str = Field(..., description="Unique employee identifier")
    employee_code: str = Field(..., description="ERP staff identifier")
    full_name: str = Field(..., description="Officer name")
    designation: str = Field(..., description="Corporate role title")
    depot_id: str = Field(..., description="Base depot code")
    depot_name: str = Field(..., description="Regional depot name")
    territory_name: str = Field(..., description="Assigned territory name")
    base_salary_bdt: float = Field(..., description="Monthly base salary in BDT")
    tada_bdt: float = Field(..., description="Travel & Daily Allowance in BDT")
    incentives_bdt: float = Field(..., description="Commission & performance incentives in BDT")
    overhead_bdt: float = Field(
        ..., description="Company overhead (mobile, training, tooling) in BDT"
    )
    fully_loaded_ctc_bdt: float = Field(
        ...,
        description="Total Monthly CTC = Base + TA/DA + Incentives + Overhead (tabular-nums)",
    )
    gross_sales_bdt: float = Field(..., description="Monthly gross sales volume in BDT")
    contribution_margin_bdt: float = Field(
        ...,
        description=(
            "Net Contribution Margin delivered after COGS & Direct Cost in BDT (tabular-nums)"
        ),
    )
    roi_multiple: float = Field(
        ...,
        description="Contribution Margin / Fully Loaded CTC ratio multiple (e.g. 5.8x)",
    )
    quadrant: str = Field(
        ...,
        description="Quadrant label: STARS, HEAVY_HITTERS, RAMP_UP, VALUE_DESTROYERS",
    )
    coordinates: list[float] = Field(
        ...,
        description="Coordinates [ctc_bdt, margin_bdt] for ECharts series",
    )


class QuadrantSummary(BaseModel):
    """Aggregate statistics for a single scatter plot quadrant."""

    quadrant: str = Field(..., description="Quadrant code")
    label: str = Field(..., description="Human display name")
    count: int = Field(..., description="Number of sales reps in quadrant")
    percentage: float = Field(..., description="Share of sales force %")
    avg_ctc_bdt: float = Field(..., description="Average fully-loaded CTC in BDT")
    avg_margin_bdt: float = Field(..., description="Average contribution margin in BDT")
    avg_roi_multiple: float = Field(..., description="Average ROI multiple")


class CTCScatterPlotResponse(BaseModel):
    """Complete 4-Quadrant Scatter Plot dataset pre-formatted for Apache ECharts."""

    period: str = Field(..., description="Analysis period (e.g. 2024-M03)")
    total_reps: int = Field(..., description="Total active sales representatives analyzed")
    median_ctc_bdt: float = Field(..., description="Median CTC partition threshold (X-axis split)")
    median_contribution_margin_bdt: float = Field(
        ..., description="Median Contribution Margin partition threshold (Y-axis split)"
    )
    quadrants: list[QuadrantSummary] = Field(
        ..., description="Summary metrics for the 4 performance quadrants"
    )
    points: list[CTCScatterPoint] = Field(
        ..., description="List of all sales officer scatter points"
    )
