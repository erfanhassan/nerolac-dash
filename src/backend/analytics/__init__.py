"""Nerolac Dash Operational Analytics Package.

Modules:
- unit_converter: SAP Material Master (MARA/MARC) density conversion (KG to Liters).
- bom_cost_mapper: Raw material BOM cost mapping (Crude, TiO2) & Contribution Margin engine.
- stockout_masker: SAP MB52/MSEG zero-stock preprocessing to prevent demand distortion.
"""

from src.backend.analytics.bom_cost_mapper import (
    BOMComponent,
    BOMCostMapper,
    CommodityMarketPrices,
    ContributionMarginReport,
    ProductBOM,
    RawMaterial,
    RawMaterialCategory,
)
from src.backend.analytics.daily_reconciliation import (
    DailyReconciliationEngine,
    get_daily_reconciler,
)
from src.backend.analytics.stockout_masker import (
    NEROLAC_DEPOTS,
    RevenueIntegrityViolationError,
    StockoutEvent,
    StockoutMasker,
    StockoutMaskingReport,
    StockoutPeriod,
)
from src.backend.analytics.unit_converter import (
    ConversionResult,
    MaterialMasterDensity,
    SAPUnitConverter,
)

__all__ = [
    "SAPUnitConverter",
    "MaterialMasterDensity",
    "ConversionResult",
    "BOMCostMapper",
    "ProductBOM",
    "BOMComponent",
    "RawMaterial",
    "RawMaterialCategory",
    "CommodityMarketPrices",
    "ContributionMarginReport",
    "StockoutMasker",
    "StockoutEvent",
    "StockoutPeriod",
    "StockoutMaskingReport",
    "NEROLAC_DEPOTS",
    "RevenueIntegrityViolationError",
    "DailyReconciliationEngine",
    "get_daily_reconciler",
]
