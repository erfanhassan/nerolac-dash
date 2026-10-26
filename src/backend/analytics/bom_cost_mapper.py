"""Raw Material BOM Cost Mapper & Contribution Margin Engine.

Maps global crude derivative prices (solvents, resins) and Titanium Dioxide (TiO2)
import commodity costs to SKU production Bill of Materials (BOM) for accurate
contribution margin tracking and margin sensitivity simulations.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("nerolac.analytics.bom_cost_mapper")


class RawMaterialCategory(str, Enum):
    """Classification of raw material inputs for paint manufacturing."""

    TIO2 = "TIO2"  # Titanium Dioxide white pigment
    RESIN = "RESIN"  # Synthetic binders (Acrylic, Alkyd, Epoxy, PU)
    SOLVENT = "SOLVENT"  # Petrochemical solvents (MTO, Xylene, Toluene)
    EXTENDER = "EXTENDER"  # Mineral extenders (Calcite, Talc, Barytes)
    ADDITIVE = "ADDITIVE"  # Functional additives (Defoamers, Biocides, Driers)
    PACKAGING = "PACKAGING"  # Cans, pails, labels
    WATER = "WATER"  # Demineralized process water


@dataclass
class CommodityMarketPrices:
    """Spot commodity market benchmarks and foreign exchange rates."""

    brent_crude_usd_per_barrel: float = 78.50  # USD per barrel (Brent benchmark)
    tio2_usd_per_mt: float = 2850.00  # USD per metric ton (Rutile TiO2)
    usd_to_bdt_exchange_rate: float = 120.00  # BDT per 1 USD
    import_duty_and_freight_pct: float = 8.50  # Port handling, freight & customs (%)
    baseline_brent_crude_usd: float = 75.00  # Baseline calibration crude price
    baseline_tio2_usd_per_mt: float = 2800.00  # Baseline calibration TiO2 price
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.brent_crude_usd_per_barrel <= 0:
            raise ValueError("Brent crude price must be strictly positive")
        if self.tio2_usd_per_mt <= 0:
            raise ValueError("TiO2 price must be strictly positive")
        if self.usd_to_bdt_exchange_rate <= 0:
            raise ValueError("USD to BDT exchange rate must be strictly positive")
        if self.import_duty_and_freight_pct < 0:
            raise ValueError("Import duty and freight percentage cannot be negative")

    @property
    def crude_price_ratio(self) -> float:
        """Ratio of current Brent crude price to baseline."""
        return self.brent_crude_usd_per_barrel / self.baseline_brent_crude_usd

    @property
    def tio2_price_ratio(self) -> float:
        """Ratio of current TiO2 price to baseline."""
        return self.tio2_usd_per_mt / self.baseline_tio2_usd_per_mt

    @property
    def effective_tio2_bdt_per_kg(self) -> float:
        """Landed cost of imported Titanium Dioxide in BDT per KG."""
        base_usd_per_kg = self.tio2_usd_per_mt / 1000.0
        duty_multiplier = 1.0 + (self.import_duty_and_freight_pct / 100.0)
        return round(base_usd_per_kg * self.usd_to_bdt_exchange_rate * duty_multiplier, 2)


@dataclass
class RawMaterial:
    """Definition of a raw material commodity."""

    material_code: str
    material_name: str
    category: RawMaterialCategory
    base_cost_bdt_per_kg: float
    crude_oil_elasticity: float = 0.0  # Sensitivity to Brent crude price changes (0.0 to 1.0)
    is_imported: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        if self.base_cost_bdt_per_kg < 0:
            raise ValueError("Raw material base cost cannot be negative")
        if not (0.0 <= self.crude_oil_elasticity <= 1.5):
            raise ValueError("Crude oil elasticity factor must be between 0.0 and 1.5")


@dataclass
class BOMComponent:
    """Component line item in a Product Bill of Materials."""

    material_code: str
    material_name: str
    category: RawMaterialCategory
    quantity_kg_per_liter: float
    scrap_factor_pct: float = 0.50  # 0.5% manufacturing loss

    def __post_init__(self) -> None:
        if self.quantity_kg_per_liter <= 0:
            raise ValueError("Component quantity per liter must be strictly positive")
        if self.scrap_factor_pct < 0:
            raise ValueError("Scrap factor percentage cannot be negative")

    @property
    def effective_quantity_kg(self) -> float:
        """Effective quantity required including scrap allowance."""
        return self.quantity_kg_per_liter * (1.0 + self.scrap_factor_pct / 100.0)


@dataclass
class ProductBOM:
    """Bill of Materials specification for a finished paint SKU."""

    sku_code: str
    sku_name: str
    category: str  # "DECORATIVE", "INDUSTRIAL", "AUTOMOTIVE"
    components: list[BOMComponent]
    selling_price_bdt_per_liter: float
    conversion_cost_bdt_per_liter: float = 18.50  # Direct labor & grinding power
    distribution_cost_bdt_per_liter: float = 8.00  # Variable logistics & freight
    packaging_cost_bdt_per_liter: float = 12.00  # Tin/pail packaging

    def __post_init__(self) -> None:
        if self.selling_price_bdt_per_liter <= 0:
            raise ValueError("Selling price per liter must be strictly positive")
        if self.conversion_cost_bdt_per_liter < 0:
            raise ValueError("Conversion cost cannot be negative")
        if self.distribution_cost_bdt_per_liter < 0:
            raise ValueError("Distribution cost cannot be negative")
        if self.packaging_cost_bdt_per_liter < 0:
            raise ValueError("Packaging cost cannot be negative")


@dataclass
class ContributionMarginReport:
    """Detailed contribution margin and cost breakdown for a paint SKU."""

    sku_code: str
    sku_name: str
    category: str
    selling_price_per_liter: float
    total_bom_rm_cost_per_liter: float
    conversion_cost_per_liter: float
    distribution_cost_per_liter: float
    packaging_cost_per_liter: float
    total_cogs_per_liter: float
    contribution_margin_bdt: float
    contribution_margin_ratio_pct: float
    cost_breakdown_by_category: dict[str, float]
    tio2_cost_per_liter: float
    resin_cost_per_liter: float
    solvent_cost_per_liter: float
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary representation."""
        data = asdict(self)
        data["calculated_at"] = self.calculated_at.isoformat()
        return data


class BOMCostMapper:
    """Enterprise mapper linking global commodities to SKU BOM and contribution margin."""

    def __init__(
        self,
        market_prices: CommodityMarketPrices | None = None,
    ) -> None:
        self.market_prices = market_prices or CommodityMarketPrices()
        self._raw_materials: dict[str, RawMaterial] = {}
        self._product_boms: dict[str, ProductBOM] = {}
        self._load_canonical_raw_materials()
        self._load_canonical_product_boms()

    def _load_canonical_raw_materials(self) -> None:
        """Register canonical raw materials used in paint production."""
        materials = [
            # 1. Titanium Dioxide Pigments
            RawMaterial(
                material_code="RM_TIO2_RUTILE",
                material_name="Titanium Dioxide Rutile Grade (R-902+)",
                category=RawMaterialCategory.TIO2,
                base_cost_bdt_per_kg=370.00,
                crude_oil_elasticity=0.0,
                is_imported=True,
            ),
            # 2. Resins and Binders (Petrochemical derivatives)
            RawMaterial(
                material_code="RM_RESIN_ACRYLIC_PURE",
                material_name="Pure Acrylic Emulsion Polymer (50% solids)",
                category=RawMaterialCategory.RESIN,
                base_cost_bdt_per_kg=240.00,
                crude_oil_elasticity=0.55,  # 55% elasticity to crude oil
                is_imported=True,
            ),
            RawMaterial(
                material_code="RM_RESIN_STYRENE_ACR",
                material_name="Styrene Acrylic Emulsion Polymer",
                category=RawMaterialCategory.RESIN,
                base_cost_bdt_per_kg=210.00,
                crude_oil_elasticity=0.60,
                is_imported=True,
            ),
            RawMaterial(
                material_code="RM_RESIN_ALKYD",
                material_name="Long Oil Alkyd Resin (Linseed/Soya)",
                category=RawMaterialCategory.RESIN,
                base_cost_bdt_per_kg=260.00,
                crude_oil_elasticity=0.50,
                is_imported=False,
            ),
            RawMaterial(
                material_code="RM_RESIN_EPOXY",
                material_name="Liquid Epoxy Resin (Bisphenol-A base)",
                category=RawMaterialCategory.RESIN,
                base_cost_bdt_per_kg=350.00,
                crude_oil_elasticity=0.65,
                is_imported=True,
            ),
            RawMaterial(
                material_code="RM_RESIN_PU_ACRYLIC",
                material_name="Hydroxyl Acrylic Resin for 2K PU",
                category=RawMaterialCategory.RESIN,
                base_cost_bdt_per_kg=380.00,
                crude_oil_elasticity=0.60,
                is_imported=True,
            ),
            # 3. Solvents & Hydrocarbons (High crude elasticity)
            RawMaterial(
                material_code="RM_SOLVENT_MTO",
                material_name="Mineral Turpentine Oil (MTO)",
                category=RawMaterialCategory.SOLVENT,
                base_cost_bdt_per_kg=150.00,
                crude_oil_elasticity=0.85,  # 85% elasticity to crude oil
                is_imported=False,
            ),
            RawMaterial(
                material_code="RM_SOLVENT_XYLENE",
                material_name="Commercial Xylene Isomer Mix",
                category=RawMaterialCategory.SOLVENT,
                base_cost_bdt_per_kg=175.00,
                crude_oil_elasticity=0.80,
                is_imported=True,
            ),
            RawMaterial(
                material_code="RM_SOLVENT_BUTYL_ACETATE",
                material_name="Normal Butyl Acetate (99%)",
                category=RawMaterialCategory.SOLVENT,
                base_cost_bdt_per_kg=210.00,
                crude_oil_elasticity=0.75,
                is_imported=True,
            ),
            # 4. Extenders and Fillers (Domestic mineral sources)
            RawMaterial(
                material_code="RM_EXT_CALCITE",
                material_name="Micronized Calcium Carbonate (Calcite 5 Microns)",
                category=RawMaterialCategory.EXTENDER,
                base_cost_bdt_per_kg=18.00,
                crude_oil_elasticity=0.0,
            ),
            RawMaterial(
                material_code="RM_EXT_TALC",
                material_name="Micro Talc Powder (Magnesium Silicate)",
                category=RawMaterialCategory.EXTENDER,
                base_cost_bdt_per_kg=24.00,
                crude_oil_elasticity=0.0,
            ),
            RawMaterial(
                material_code="RM_EXT_BARYTES",
                material_name="Precipitated Barium Sulfate (Barytes)",
                category=RawMaterialCategory.EXTENDER,
                base_cost_bdt_per_kg=35.00,
                crude_oil_elasticity=0.0,
            ),
            # 5. Additives & Process Inputs
            RawMaterial(
                material_code="RM_ADD_SPECIALTY",
                material_name="Specialty Additives Pack (Dispersant, Defoamer, Biocide)",
                category=RawMaterialCategory.ADDITIVE,
                base_cost_bdt_per_kg=480.00,
                crude_oil_elasticity=0.20,
            ),
            RawMaterial(
                material_code="RM_WATER",
                material_name="Demineralized Treated Process Water",
                category=RawMaterialCategory.WATER,
                base_cost_bdt_per_kg=1.50,
                crude_oil_elasticity=0.0,
            ),
        ]
        for m in materials:
            self._raw_materials[m.material_code] = m

    def _load_canonical_product_boms(self) -> None:
        """Register canonical Nerolac Product Bills of Material."""
        # 1. Decorative Exterior Emulsion: Excel Mica Marble White
        excel_components = [
            BOMComponent(
                material_code="RM_TIO2_RUTILE",
                material_name="Titanium Dioxide Rutile Grade",
                category=RawMaterialCategory.TIO2,
                quantity_kg_per_liter=0.180,
            ),
            BOMComponent(
                material_code="RM_RESIN_ACRYLIC_PURE",
                material_name="Pure Acrylic Emulsion",
                category=RawMaterialCategory.RESIN,
                quantity_kg_per_liter=0.320,
            ),
            BOMComponent(
                material_code="RM_EXT_CALCITE",
                material_name="Micronized Calcite",
                category=RawMaterialCategory.EXTENDER,
                quantity_kg_per_liter=0.450,
            ),
            BOMComponent(
                material_code="RM_ADD_SPECIALTY",
                material_name="Specialty Additives Pack",
                category=RawMaterialCategory.ADDITIVE,
                quantity_kg_per_liter=0.045,
            ),
            BOMComponent(
                material_code="RM_WATER",
                material_name="Process Water",
                category=RawMaterialCategory.WATER,
                quantity_kg_per_liter=0.420,
            ),
        ]
        self.register_bom(
            ProductBOM(
                sku_code="DEC_EXT_EXCEL_WHITE",
                sku_name="Nerolac Excel Mica Marble Exterior White",
                category="DECORATIVE",
                components=excel_components,
                selling_price_bdt_per_liter=450.00,
                conversion_cost_bdt_per_liter=18.00,
                distribution_cost_bdt_per_liter=9.00,
                packaging_cost_bdt_per_liter=14.00,
            )
        )

        # 2. Decorative Interior Emulsion: Beauty Gold Interior White
        beauty_gold_components = [
            BOMComponent(
                material_code="RM_TIO2_RUTILE",
                material_name="Titanium Dioxide Rutile Grade",
                category=RawMaterialCategory.TIO2,
                quantity_kg_per_liter=0.220,
            ),
            BOMComponent(
                material_code="RM_RESIN_STYRENE_ACR",
                material_name="Styrene Acrylic Emulsion",
                category=RawMaterialCategory.RESIN,
                quantity_kg_per_liter=0.280,
            ),
            BOMComponent(
                material_code="RM_EXT_CALCITE",
                material_name="Micronized Calcite",
                category=RawMaterialCategory.EXTENDER,
                quantity_kg_per_liter=0.420,
            ),
            BOMComponent(
                material_code="RM_EXT_TALC",
                material_name="Micro Talc Powder",
                category=RawMaterialCategory.EXTENDER,
                quantity_kg_per_liter=0.080,
            ),
            BOMComponent(
                material_code="RM_ADD_SPECIALTY",
                material_name="Specialty Additives Pack",
                category=RawMaterialCategory.ADDITIVE,
                quantity_kg_per_liter=0.035,
            ),
            BOMComponent(
                material_code="RM_WATER",
                material_name="Process Water",
                category=RawMaterialCategory.WATER,
                quantity_kg_per_liter=0.380,
            ),
        ]
        self.register_bom(
            ProductBOM(
                sku_code="DEC_INT_BEAUTY_GOLD",
                sku_name="Nerolac Beauty Gold Washable Interior Emulsion",
                category="DECORATIVE",
                components=beauty_gold_components,
                selling_price_bdt_per_liter=380.00,
                conversion_cost_bdt_per_liter=16.00,
                distribution_cost_bdt_per_liter=8.00,
                packaging_cost_bdt_per_liter=12.00,
            )
        )

        # 3. Decorative Solvent Enamel: Synthetic Gloss Enamel
        enamel_components = [
            BOMComponent(
                material_code="RM_TIO2_RUTILE",
                material_name="Titanium Dioxide Rutile Grade",
                category=RawMaterialCategory.TIO2,
                quantity_kg_per_liter=0.150,
            ),
            BOMComponent(
                material_code="RM_RESIN_ALKYD",
                material_name="Long Oil Alkyd Resin",
                category=RawMaterialCategory.RESIN,
                quantity_kg_per_liter=0.450,
            ),
            BOMComponent(
                material_code="RM_SOLVENT_MTO",
                material_name="Mineral Turpentine Oil",
                category=RawMaterialCategory.SOLVENT,
                quantity_kg_per_liter=0.350,
            ),
            BOMComponent(
                material_code="RM_EXT_CALCITE",
                material_name="Micronized Calcite",
                category=RawMaterialCategory.EXTENDER,
                quantity_kg_per_liter=0.100,
            ),
            BOMComponent(
                material_code="RM_ADD_SPECIALTY",
                material_name="Driers and Anti-Skinning Agent",
                category=RawMaterialCategory.ADDITIVE,
                quantity_kg_per_liter=0.025,
            ),
        ]
        self.register_bom(
            ProductBOM(
                sku_code="DEC_SYN_GLOSS_ENAMEL",
                sku_name="Nerolac Synthetic Gloss Enamel Brilliant White",
                category="DECORATIVE",
                components=enamel_components,
                selling_price_bdt_per_liter=395.00,
                conversion_cost_bdt_per_liter=17.00,
                distribution_cost_bdt_per_liter=8.50,
                packaging_cost_bdt_per_liter=15.00,
            )
        )

        # 4. Industrial Epoxy Coating: Neropoxy High Build Floor Grey
        epoxy_components = [
            BOMComponent(
                material_code="RM_TIO2_RUTILE",
                material_name="Titanium Dioxide Rutile Grade",
                category=RawMaterialCategory.TIO2,
                quantity_kg_per_liter=0.090,
            ),
            BOMComponent(
                material_code="RM_RESIN_EPOXY",
                material_name="Liquid Epoxy Resin",
                category=RawMaterialCategory.RESIN,
                quantity_kg_per_liter=0.520,
            ),
            BOMComponent(
                material_code="RM_SOLVENT_XYLENE",
                material_name="Xylene Solvent",
                category=RawMaterialCategory.SOLVENT,
                quantity_kg_per_liter=0.180,
            ),
            BOMComponent(
                material_code="RM_EXT_BARYTES",
                material_name="Barytes Heavy Mineral Filler",
                category=RawMaterialCategory.EXTENDER,
                quantity_kg_per_liter=0.680,
            ),
            BOMComponent(
                material_code="RM_ADD_SPECIALTY",
                material_name="Epoxy Flow & Leveling Additive",
                category=RawMaterialCategory.ADDITIVE,
                quantity_kg_per_liter=0.030,
            ),
        ]
        self.register_bom(
            ProductBOM(
                sku_code="IND_EPOXY_FLOOR_GR",
                sku_name="Neropoxy High Build Floor Coating Grey",
                category="INDUSTRIAL",
                components=epoxy_components,
                selling_price_bdt_per_liter=620.00,
                conversion_cost_bdt_per_liter=22.00,
                distribution_cost_bdt_per_liter=11.00,
                packaging_cost_bdt_per_liter=18.00,
            )
        )

        # 5. Industrial PU Two-Pack White
        pu_components = [
            BOMComponent(
                material_code="RM_TIO2_RUTILE",
                material_name="Titanium Dioxide Rutile Grade",
                category=RawMaterialCategory.TIO2,
                quantity_kg_per_liter=0.240,
            ),
            BOMComponent(
                material_code="RM_RESIN_PU_ACRYLIC",
                material_name="Hydroxyl Acrylic Resin",
                category=RawMaterialCategory.RESIN,
                quantity_kg_per_liter=0.480,
            ),
            BOMComponent(
                material_code="RM_SOLVENT_BUTYL_ACETATE",
                material_name="Butyl Acetate Solvent",
                category=RawMaterialCategory.SOLVENT,
                quantity_kg_per_liter=0.280,
            ),
            BOMComponent(
                material_code="RM_ADD_SPECIALTY",
                material_name="PU UV Stabilizer & Wetting Agent",
                category=RawMaterialCategory.ADDITIVE,
                quantity_kg_per_liter=0.040,
            ),
        ]
        self.register_bom(
            ProductBOM(
                sku_code="IND_PU_TOPCOAT_WHITE",
                sku_name="Nerolac Polyurethane Two-Pack Topcoat White",
                category="INDUSTRIAL",
                components=pu_components,
                selling_price_bdt_per_liter=750.00,
                conversion_cost_bdt_per_liter=25.00,
                distribution_cost_bdt_per_liter=12.00,
                packaging_cost_bdt_per_liter=20.00,
            )
        )

    def register_bom(self, bom: ProductBOM) -> None:
        """Register a new or updated product Bill of Materials."""
        self._product_boms[bom.sku_code.strip().upper()] = bom

    def register_raw_material(self, material: RawMaterial) -> None:
        """Register a raw material definition."""
        self._raw_materials[material.material_code.strip().upper()] = material

    def calculate_raw_material_unit_cost(
        self,
        material_code: str,
        market_prices: CommodityMarketPrices | None = None,
    ) -> float:
        """Calculate dynamic spot cost (BDT per KG) for a raw material.

        Considers:
        - For TiO2: Global commodity spot price in USD/MT converted to BDT/KG with duty.
        - For Resins and Solvents: Base cost scaled by crude oil elasticity.
        - For Minerals/Water: Stable domestic costs.
        """
        prices = market_prices or self.market_prices
        code = material_code.strip().upper()

        if code not in self._raw_materials:
            raise KeyError(f"Raw material '{code}' not found in registry.")

        mat = self._raw_materials[code]

        if mat.category == RawMaterialCategory.TIO2:
            return prices.effective_tio2_bdt_per_kg

        # Elasticity scaling for crude derivatives (resins, solvents)
        if mat.crude_oil_elasticity > 0.0:
            crude_delta_ratio = (
                prices.brent_crude_usd_per_barrel - prices.baseline_brent_crude_usd
            ) / prices.baseline_brent_crude_usd
            multiplier = 1.0 + (mat.crude_oil_elasticity * crude_delta_ratio)
            cost = mat.base_cost_bdt_per_kg * max(multiplier, 0.20)
            return round(cost, 2)

        return mat.base_cost_bdt_per_kg

    def compute_sku_bom_cost(
        self,
        sku_code: str,
        market_prices: CommodityMarketPrices | None = None,
    ) -> float:
        """Compute the total raw material BOM cost per liter of paint SKU."""
        prices = market_prices or self.market_prices
        code = sku_code.strip().upper()

        if code not in self._product_boms:
            raise KeyError(f"Product BOM for SKU '{code}' not found in registry.")

        bom = self._product_boms[code]
        total_rm_cost = 0.0

        for comp in bom.components:
            unit_cost = self.calculate_raw_material_unit_cost(comp.material_code, prices)
            comp_cost = comp.effective_quantity_kg * unit_cost
            total_rm_cost += comp_cost

        return round(total_rm_cost, 2)

    def calculate_contribution_margin(
        self,
        sku_code: str,
        selling_price_override: float | None = None,
        market_prices: CommodityMarketPrices | None = None,
    ) -> ContributionMarginReport:
        """Calculate net contribution margin and itemized cost breakdown per SKU.

        Formula:
          Total COGS = Total BOM RM Cost + Conversion Cost + Packaging Cost + Distribution Cost
          Contribution Margin (BDT) = Selling Price - Total COGS
          Contribution Margin Ratio (%) = (Contribution Margin / Selling Price) * 100
        """
        prices = market_prices or self.market_prices
        code = sku_code.strip().upper()

        if code not in self._product_boms:
            raise KeyError(f"Product BOM for SKU '{code}' not found in registry.")

        bom = self._product_boms[code]
        selling_price = (
            selling_price_override
            if selling_price_override is not None
            else bom.selling_price_bdt_per_liter
        )
        if selling_price <= 0:
            raise ValueError(f"Selling price must be strictly positive, got {selling_price}")

        total_rm_cost = 0.0
        breakdown_by_cat: dict[str, float] = {cat.value: 0.0 for cat in RawMaterialCategory}

        for comp in bom.components:
            unit_cost = self.calculate_raw_material_unit_cost(comp.material_code, prices)
            comp_cost = comp.effective_quantity_kg * unit_cost
            total_rm_cost += comp_cost
            breakdown_by_cat[comp.category.value] = round(
                breakdown_by_cat[comp.category.value] + comp_cost, 2
            )

        total_rm_cost = round(total_rm_cost, 2)
        conversion = bom.conversion_cost_bdt_per_liter
        distribution = bom.distribution_cost_bdt_per_liter
        packaging = bom.packaging_cost_bdt_per_liter

        total_cogs = round(total_rm_cost + conversion + distribution + packaging, 2)
        contribution_margin = round(selling_price - total_cogs, 2)
        margin_ratio = round((contribution_margin / selling_price) * 100.0, 2)

        return ContributionMarginReport(
            sku_code=bom.sku_code,
            sku_name=bom.sku_name,
            category=bom.category,
            selling_price_per_liter=round(selling_price, 2),
            total_bom_rm_cost_per_liter=total_rm_cost,
            conversion_cost_per_liter=conversion,
            distribution_cost_per_liter=distribution,
            packaging_cost_per_liter=packaging,
            total_cogs_per_liter=total_cogs,
            contribution_margin_bdt=contribution_margin,
            contribution_margin_ratio_pct=margin_ratio,
            cost_breakdown_by_category=breakdown_by_cat,
            tio2_cost_per_liter=breakdown_by_cat.get(RawMaterialCategory.TIO2.value, 0.0),
            resin_cost_per_liter=breakdown_by_cat.get(RawMaterialCategory.RESIN.value, 0.0),
            solvent_cost_per_liter=breakdown_by_cat.get(RawMaterialCategory.SOLVENT.value, 0.0),
        )

    def simulate_commodity_shocks(
        self,
        crude_shock_pct: float,
        tio2_shock_pct: float,
        usd_to_bdt_shock_pct: float = 0.0,
    ) -> list[ContributionMarginReport]:
        """Simulate executive market shock scenarios across all registered product SKUs.

        Args:
            crude_shock_pct: Percentage change in Brent crude price (+15% = 15.0).
            tio2_shock_pct: Percentage change in global TiO2 price (+10% = 10.0).
            usd_to_bdt_shock_pct: Percentage depreciation in BDT against USD (+5% = 5.0).
        """
        sim_crude = self.market_prices.brent_crude_usd_per_barrel * (1.0 + crude_shock_pct / 100.0)
        sim_tio2 = self.market_prices.tio2_usd_per_mt * (1.0 + tio2_shock_pct / 100.0)
        sim_fx = self.market_prices.usd_to_bdt_exchange_rate * (1.0 + usd_to_bdt_shock_pct / 100.0)

        sim_market = CommodityMarketPrices(
            brent_crude_usd_per_barrel=round(sim_crude, 2),
            tio2_usd_per_mt=round(sim_tio2, 2),
            usd_to_bdt_exchange_rate=round(sim_fx, 2),
            import_duty_and_freight_pct=self.market_prices.import_duty_and_freight_pct,
            baseline_brent_crude_usd=self.market_prices.baseline_brent_crude_usd,
            baseline_tio2_usd_per_mt=self.market_prices.baseline_tio2_usd_per_mt,
        )

        reports: list[ContributionMarginReport] = []
        for sku_code in self._product_boms:
            report = self.calculate_contribution_margin(sku_code, market_prices=sim_market)
            reports.append(report)

        return reports

    def calculate_breakeven_selling_price(
        self,
        sku_code: str,
        target_margin_pct: float = 35.0,
        market_prices: CommodityMarketPrices | None = None,
    ) -> float:
        """Calculate required selling price to achieve target contribution margin percentage.

        Formula:
          Required Price = Total COGS / (1 - Target Margin Ratio)
        """
        if target_margin_pct >= 100.0 or target_margin_pct < 0.0:
            raise ValueError("Target margin percentage must be between 0.0% and 99.9%")

        report = self.calculate_contribution_margin(sku_code, market_prices=market_prices)
        total_cogs = report.total_cogs_per_liter
        margin_decimal = target_margin_pct / 100.0
        req_price = total_cogs / (1.0 - margin_decimal)
        return round(req_price, 2)
