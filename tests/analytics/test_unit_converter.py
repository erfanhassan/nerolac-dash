"""Comprehensive Test Suite for Volumetric Unit Converter and Raw Material BOM Cost Mapper.

Verifies:
1. SAP Material Master (MARA/MARC) density lookup and KG-to-Liter conversion across
   Decorative, Industrial, and Automotive paint SKUs.
2. Reverse Liter-to-KG conversion and temperature expansion adjustments.
3. Raw Material BOM Cost mapping for global crude derivatives (resins, solvents)
   and Titanium Dioxide (TiO2).
4. Accurate net contribution margin and margin ratio percentage calculation per SKU.
5. Executive market shock sensitivity simulations (Crude and TiO2 shocks).
"""

from __future__ import annotations

import pytest

from src.backend.analytics.bom_cost_mapper import (
    BOMCostMapper,
    CommodityMarketPrices,
)
from src.backend.analytics.unit_converter import (
    MaterialMasterDensity,
    SAPUnitConverter,
)


class TestSAPUnitConverter:
    """Test suite for SAP Material Master volumetric unit conversions."""

    @pytest.fixture
    def converter(self) -> SAPUnitConverter:
        return SAPUnitConverter()

    # 1. Decorative Paint SKUs Conversion
    def test_decorative_emulsion_kg_to_liters(self, converter: SAPUnitConverter) -> None:
        """Verify Nerolac Excel Mica Marble Exterior White (density 1.42 kg/L)."""
        mass_kg = 1420.0
        result = converter.convert_kg_to_liters(mass_kg, "DEC_EXT_EXCEL_WHITE")

        assert result.sku_code == "DEC_EXT_EXCEL_WHITE"
        assert result.category == "DECORATIVE"
        assert result.density_applied_kg_per_l == 1.42
        assert result.input_value == 1420.0
        assert result.output_value == 1000.0  # 1420 / 1.42 = 1000 Liters
        assert result.volume_liters == 1000.0
        assert result.mass_kg == 1420.0

    def test_decorative_interior_washable_emulsion(
        self, converter: SAPUnitConverter
    ) -> None:
        """Verify Nerolac Beauty Gold Washable Interior Emulsion (density 1.36 kg/L)."""
        mass_kg = 2720.0
        result = converter.convert_kg_to_liters(mass_kg, "DEC_INT_BEAUTY_GOLD")

        assert result.density_applied_kg_per_l == 1.36
        assert result.output_value == 2000.0  # 2720 / 1.36 = 2000 Liters

    def test_decorative_synthetic_gloss_enamel(
        self, converter: SAPUnitConverter
    ) -> None:
        """Verify Nerolac Synthetic Gloss Enamel Brilliant White (density 1.08 kg/L)."""
        mass_kg = 1080.0
        result = converter.convert_kg_to_liters(mass_kg, "DEC_SYN_GLOSS_ENAMEL")

        assert result.density_applied_kg_per_l == 1.08
        assert result.output_value == 1000.0  # 1080 / 1.08 = 1000 Liters

    # 2. Industrial Paint SKUs Conversion
    def test_industrial_heavy_duty_epoxy_floor_coating(
        self, converter: SAPUnitConverter
    ) -> None:
        """Verify Neropoxy High Build Floor Coating Grey (density 1.52 kg/L)."""
        mass_kg = 7600.0
        result = converter.convert_kg_to_liters(mass_kg, "IND_EPOXY_FLOOR_GR")

        assert result.category == "INDUSTRIAL"
        assert result.density_applied_kg_per_l == 1.52
        assert result.output_value == 5000.0  # 7600 / 1.52 = 5000 Liters

    def test_industrial_polyurethane_topcoat(
        self, converter: SAPUnitConverter
    ) -> None:
        """Verify Nerolac Polyurethane (PU) Two-Pack Topcoat (density 1.18 kg/L)."""
        mass_kg = 2360.0
        result = converter.convert_kg_to_liters(mass_kg, "IND_PU_TOPCOAT_WHITE")

        assert result.density_applied_kg_per_l == 1.18
        assert result.output_value == 2000.0  # 2360 / 1.18 = 2000 Liters

    def test_industrial_general_pu_thinner(
        self, converter: SAPUnitConverter
    ) -> None:
        """Verify Nerolac Industrial General PU Thinner (density 0.84 kg/L)."""
        mass_kg = 840.0
        result = converter.convert_kg_to_liters(mass_kg, "IND_THINNER_PU")

        assert result.density_applied_kg_per_l == 0.84
        assert result.output_value == 1000.0  # 840 / 0.84 = 1000 Liters

    def test_automotive_2k_clearcoat(self, converter: SAPUnitConverter) -> None:
        """Verify Automotive OEM Clearcoat (density 0.98 kg/L)."""
        mass_kg = 980.0
        result = converter.convert_kg_to_liters(mass_kg, "AUTO_CLEAR_2K")

        assert result.category == "AUTOMOTIVE"
        assert result.density_applied_kg_per_l == 0.98
        assert result.output_value == 1000.0

    # 3. Reverse Liter-to-KG Conversion
    def test_liters_to_kg_reverse_conversion(
        self, converter: SAPUnitConverter
    ) -> None:
        """Verify reverse conversion from sales volume (Liters) to production mass (KG)."""
        # 1000 L of Excel White -> 1420 KG
        res_dec = converter.convert_liters_to_kg(1000.0, "DEC_EXT_EXCEL_WHITE")
        assert res_dec.output_value == 1420.0
        assert res_dec.conversion_direction == "L_TO_KG"

        # 500 L of Epoxy Floor -> 760 KG
        res_ind = converter.convert_liters_to_kg(500.0, "IND_EPOXY_FLOOR_GR")
        assert res_ind.output_value == 760.0

    # 4. Temperature Compensation
    def test_temperature_expansion_effect_on_density(
        self, converter: SAPUnitConverter
    ) -> None:
        """Verify volume expands at elevated summer plant temperatures (35°C vs 25°C)."""
        mass_kg = 1420.0
        res_std = converter.convert_kg_to_liters(
            mass_kg, "DEC_EXT_EXCEL_WHITE", temperature_c=25.0
        )
        res_hot = converter.convert_kg_to_liters(
            mass_kg, "DEC_EXT_EXCEL_WHITE", temperature_c=35.0
        )

        # Higher temp -> lower density -> higher volume
        assert res_hot.density_applied_kg_per_l < res_std.density_applied_kg_per_l
        assert res_hot.output_value > res_std.output_value

    # 5. Fallback for Unregistered SKU
    def test_fallback_category_density(self, converter: SAPUnitConverter) -> None:
        """Verify fallback behavior for unknown SKU with category hint."""
        res = converter.convert_kg_to_liters(
            1350.0, "UNKNOWN_DECORATIVE_SKU", category_hint="DECORATIVE"
        )
        assert res.density_applied_kg_per_l == 1.35
        assert res.output_value == 1000.0

    # 6. Batch Conversion
    def test_batch_convert_kg_to_liters(self, converter: SAPUnitConverter) -> None:
        """Verify batch list processing."""
        batch = [
            (1420.0, "DEC_EXT_EXCEL_WHITE"),
            (7600.0, "IND_EPOXY_FLOOR_GR"),
            (840.0, "IND_THINNER_PU"),
        ]
        results = converter.batch_convert_kg_to_liters(batch)
        assert len(results) == 3
        assert results[0].output_value == 1000.0
        assert results[1].output_value == 5000.0
        assert results[2].output_value == 1000.0

    # 7. Error Handling & Guardrails
    def test_negative_mass_rejected(self, converter: SAPUnitConverter) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            converter.convert_kg_to_liters(-10.0, "DEC_EXT_EXCEL_WHITE")

    def test_negative_volume_rejected(self, converter: SAPUnitConverter) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            converter.convert_liters_to_kg(-50.0, "DEC_EXT_EXCEL_WHITE")

    def test_non_positive_density_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be strictly positive"):
            MaterialMasterDensity(
                sku_code="BAD_DENSITY",
                sku_name="Bad SKU",
                category="DECORATIVE",
                density_kg_per_l=0.0,
            )

    def test_extreme_temperature_rejected(self, converter: SAPUnitConverter) -> None:
        with pytest.raises(ValueError, match="outside operational bounds"):
            converter.convert_kg_to_liters(
                100.0, "DEC_EXT_EXCEL_WHITE", temperature_c=120.0
            )


class TestBOMCostMapper:
    """Test suite for Raw Material BOM Cost Mapper and Contribution Margin tracking."""

    @pytest.fixture
    def mapper(self) -> BOMCostMapper:
        market = CommodityMarketPrices(
            brent_crude_usd_per_barrel=78.50,
            tio2_usd_per_mt=2850.00,
            usd_to_bdt_exchange_rate=120.00,
            import_duty_and_freight_pct=8.50,
        )
        return BOMCostMapper(market_prices=market)

    # 1. Commodity Pricing
    def test_tio2_landed_cost_calculation(self, mapper: BOMCostMapper) -> None:
        """Verify Titanium Dioxide landed cost calculation in BDT/KG."""
        # 2850 USD/MT = 2.85 USD/KG * 120 BDT/USD * 1.085 duty/freight = 371.07 BDT/KG
        expected_tio2_bdt = round(2.85 * 120.00 * 1.085, 2)
        assert mapper.market_prices.effective_tio2_bdt_per_kg == expected_tio2_bdt

        actual_unit_cost = mapper.calculate_raw_material_unit_cost("RM_TIO2_RUTILE")
        assert actual_unit_cost == expected_tio2_bdt

    def test_crude_oil_elasticity_on_resins_and_solvents(
        self, mapper: BOMCostMapper
    ) -> None:
        """Verify resin and solvent price adjustments when Brent crude rises."""
        # Baseline crude is $75.00, current crude is $78.50 -> +4.667%
        # Resin has elasticity 0.55 -> price rises by ~2.567%
        base_resin = 240.00
        expected_resin = round(base_resin * (1.0 + 0.55 * (78.50 - 75.00) / 75.00), 2)
        actual_resin = mapper.calculate_raw_material_unit_cost("RM_RESIN_ACRYLIC_PURE")
        assert actual_resin == expected_resin

        # Solvent MTO has elasticity 0.85 -> price rises by ~3.967%
        base_mto = 150.00
        expected_mto = round(base_mto * (1.0 + 0.85 * (78.50 - 75.00) / 75.00), 2)
        actual_mto = mapper.calculate_raw_material_unit_cost("RM_SOLVENT_MTO")
        assert actual_mto == expected_mto

    # 2. Net Contribution Margin per SKU: Decorative Paint
    def test_decorative_excel_mica_marble_contribution_margin(
        self, mapper: BOMCostMapper
    ) -> None:
        """Verify contribution margin calculation for Excel Mica Marble Exterior White."""
        report = mapper.calculate_contribution_margin("DEC_EXT_EXCEL_WHITE")

        assert report.sku_code == "DEC_EXT_EXCEL_WHITE"
        assert report.category == "DECORATIVE"
        assert report.selling_price_per_liter == 450.00

        # Assert BOM cost components are positive and realistic
        assert report.total_bom_rm_cost_per_liter > 0
        assert report.tio2_cost_per_liter > 50.0  # Significant TiO2 component
        assert report.resin_cost_per_liter > 60.0  # Pure acrylic binder component
        assert report.total_cogs_per_liter > report.total_bom_rm_cost_per_liter

        # Contribution Margin = Selling Price - Total COGS
        expected_cm = round(report.selling_price_per_liter - report.total_cogs_per_liter, 2)
        assert report.contribution_margin_bdt == expected_cm
        assert report.contribution_margin_bdt > 0  # Profitable product

        # Contribution Margin Ratio (%)
        expected_ratio = round((expected_cm / 450.00) * 100.0, 2)
        assert report.contribution_margin_ratio_pct == expected_ratio
        assert 25.0 <= report.contribution_margin_ratio_pct <= 60.0  # Healthy margin

    def test_decorative_synthetic_enamel_contribution_margin(
        self, mapper: BOMCostMapper
    ) -> None:
        """Verify contribution margin for solvent-borne Synthetic Gloss Enamel."""
        report = mapper.calculate_contribution_margin("DEC_SYN_GLOSS_ENAMEL")

        assert report.selling_price_per_liter == 395.00
        assert report.solvent_cost_per_liter > 40.0  # Contains significant MTO
        assert report.resin_cost_per_liter > 100.0  # Alkyd resin
        assert report.contribution_margin_bdt > 0
        assert report.contribution_margin_ratio_pct > 20.0

    # 3. Net Contribution Margin per SKU: Industrial Paint
    def test_industrial_epoxy_floor_coating_contribution_margin(
        self, mapper: BOMCostMapper
    ) -> None:
        """Verify contribution margin for Neropoxy Floor Coating."""
        report = mapper.calculate_contribution_margin("IND_EPOXY_FLOOR_GR")

        assert report.sku_code == "IND_EPOXY_FLOOR_GR"
        assert report.category == "INDUSTRIAL"
        assert report.selling_price_per_liter == 620.00
        assert report.resin_cost_per_liter > 150.0  # Heavy epoxy resin component
        assert report.contribution_margin_bdt > 100.0
        assert report.contribution_margin_ratio_pct > 25.0

    def test_industrial_polyurethane_white_contribution_margin(
        self, mapper: BOMCostMapper
    ) -> None:
        """Verify contribution margin for PU Two-Pack White."""
        report = mapper.calculate_contribution_margin("IND_PU_TOPCOAT_WHITE")

        assert report.selling_price_per_liter == 750.00
        assert report.tio2_cost_per_liter > 75.0
        assert report.resin_cost_per_liter > 150.0
        assert report.contribution_margin_bdt > 150.0
        assert report.contribution_margin_ratio_pct > 30.0

    # 4. Selling Price Override
    def test_selling_price_override(self, mapper: BOMCostMapper) -> None:
        """Verify contribution margin adjusts when a custom contract selling price is used."""
        standard_report = mapper.calculate_contribution_margin("DEC_EXT_EXCEL_WHITE")
        discounted_report = mapper.calculate_contribution_margin(
            "DEC_EXT_EXCEL_WHITE", selling_price_override=400.00
        )

        assert discounted_report.selling_price_per_liter == 400.00
        assert discounted_report.total_cogs_per_liter == standard_report.total_cogs_per_liter
        assert discounted_report.contribution_margin_bdt < standard_report.contribution_margin_bdt
        assert (
            discounted_report.contribution_margin_ratio_pct
            < standard_report.contribution_margin_ratio_pct
        )

    # 5. Commodity Market Shock Sensitivity Simulation
    def test_simulate_crude_and_tio2_commodity_shocks(
        self, mapper: BOMCostMapper
    ) -> None:
        """Verify commodity price shocks reduce contribution margin."""
        baseline_report = mapper.calculate_contribution_margin("DEC_EXT_EXCEL_WHITE")

        # Simulate +25% Brent Crude spike and +15% TiO2 surge
        shocked_reports = mapper.simulate_commodity_shocks(
            crude_shock_pct=25.0,
            tio2_shock_pct=15.0,
        )
        shocked_excel = next(r for r in shocked_reports if r.sku_code == "DEC_EXT_EXCEL_WHITE")

        # Cost should increase, margin should compress
        assert (
            shocked_excel.total_bom_rm_cost_per_liter
            > baseline_report.total_bom_rm_cost_per_liter
        )
        assert (
            shocked_excel.contribution_margin_bdt
            < baseline_report.contribution_margin_bdt
        )
        assert (
            shocked_excel.contribution_margin_ratio_pct
            < baseline_report.contribution_margin_ratio_pct
        )

    # 6. Breakeven Selling Price Calculation
    def test_calculate_breakeven_selling_price(self, mapper: BOMCostMapper) -> None:
        """Verify target margin selling price calculation."""
        target_margin = 40.0  # 40% target margin
        req_price = mapper.calculate_breakeven_selling_price(
            "DEC_EXT_EXCEL_WHITE", target_margin_pct=target_margin
        )

        # At this price, margin ratio should be approximately 40.0%
        sim_report = mapper.calculate_contribution_margin(
            "DEC_EXT_EXCEL_WHITE", selling_price_override=req_price
        )
        assert abs(sim_report.contribution_margin_ratio_pct - target_margin) < 0.1

    # 7. Error Handling & Validation
    def test_unknown_sku_raises_key_error(self, mapper: BOMCostMapper) -> None:
        with pytest.raises(KeyError, match="not found in registry"):
            mapper.calculate_contribution_margin("NON_EXISTENT_SKU")

    def test_negative_crude_price_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be strictly positive"):
            CommodityMarketPrices(brent_crude_usd_per_barrel=-10.0)

    def test_invalid_target_margin_rejected(self, mapper: BOMCostMapper) -> None:
        with pytest.raises(ValueError, match="must be between 0.0% and 99.9%"):
            mapper.calculate_breakeven_selling_price("DEC_EXT_EXCEL_WHITE", target_margin_pct=110.0)
