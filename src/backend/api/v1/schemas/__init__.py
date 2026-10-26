"""Pydantic API schemas for Nerolac Dashboard modules."""

from src.backend.api.v1.schemas.finance_schemas import (
    AgingBucketSummary,
    AgingEntityRecord,
    ARAPAgingResponse,
    CashflowSimulationRequest,
    CashflowSimulationResponse,
    PnLTreeGridNode,
    SegmentPnLResponse,
    SupplierPurchaseRecord,
    SupplierVarianceResponse,
    WaterfallDataPoint,
)
from src.backend.api.v1.schemas.hr_schemas import (
    CTCScatterPlotResponse,
    CTCScatterPoint,
    EmployeeScorecard,
    KPIScoreBreakdown,
    KPIScorecardResponse,
    ManpowerCapacityResponse,
    QuadrantSummary,
    RadarAxisIndicator,
    VacantTerritoryModel,
)
from src.backend.api.v1.schemas.supply_chain_schemas import (
    DemandForecastResponse,
    MRPProposalItem,
    MRPProposalsResponse,
    TimeSeriesDataPoint,
)
from src.backend.api.v1.schemas.whatsapp_schemas import (
    DailyReconciliationResponse,
    DepotReconSummary,
    MetaWebhookPayload,
    ParsedCollectionItem,
    ParsedSKULineItem,
    ReconciliationExceptionItem,
    ResolvedDealerItem,
    WebhookIngestResponse,
    WhatsAppMessageFeedResponse,
    WhatsAppMessageRecord,
)

__all__ = [
    # Finance
    "WaterfallDataPoint",
    "PnLTreeGridNode",
    "SegmentPnLResponse",
    "SupplierPurchaseRecord",
    "SupplierVarianceResponse",
    "CashflowSimulationRequest",
    "CashflowSimulationResponse",
    "AgingBucketSummary",
    "AgingEntityRecord",
    "ARAPAgingResponse",
    # HR
    "VacantTerritoryModel",
    "ManpowerCapacityResponse",
    "KPIScoreBreakdown",
    "RadarAxisIndicator",
    "EmployeeScorecard",
    "KPIScorecardResponse",
    "CTCScatterPoint",
    "QuadrantSummary",
    "CTCScatterPlotResponse",
    # Supply Chain
    "TimeSeriesDataPoint",
    "DemandForecastResponse",
    "MRPProposalItem",
    "MRPProposalsResponse",
    # WhatsApp & Recon
    "MetaWebhookPayload",
    "WebhookIngestResponse",
    "ParsedSKULineItem",
    "ParsedCollectionItem",
    "ResolvedDealerItem",
    "WhatsAppMessageRecord",
    "WhatsAppMessageFeedResponse",
    "ReconciliationExceptionItem",
    "DepotReconSummary",
    "DailyReconciliationResponse",
]
