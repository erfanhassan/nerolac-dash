"""SAP Material Master (MARA/MARC) Volumetric Unit Conversion Engine.

Converts raw production Kilograms (KG) into liquid sales volumes (Liters) per SKU
referencing SAP Material Master (MARA general data, MARC plant data) density tables.
Supports Decorative, Industrial, and Automotive paint formulations.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("nerolac.analytics.unit_converter")

# Default standard reference temperature in Celsius
STANDARD_TEMP_CELSIUS = 25.0

# Volumetric thermal expansion coefficient for standard paints (~0.0008 per deg C)
THERMAL_EXPANSION_COEFF = 0.0008

# Category fallback densities (kg/L) for unknown or generic items
CATEGORY_FALLBACK_DENSITIES: dict[str, float] = {
    "DECORATIVE": 1.35,
    "INDUSTRIAL": 1.25,
    "AUTOMOTIVE": 1.15,
    "PROTECTIVE": 1.40,
    "COATINGS": 1.30,
    "DEFAULT": 1.20,
}


@dataclass
class MaterialMasterDensity:
    """Represents a SAP Material Master (MARA/MARC) material density definition."""

    sku_code: str
    sku_name: str
    category: str
    density_kg_per_l: float
    sku_id: str | None = None
    plant_id: str | None = None
    sub_category: str | None = None
    tolerance_pct: float = 2.0
    source_table: str = "SAP_MARA_MARC"
    reference_temp_c: float = STANDARD_TEMP_CELSIUS
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.density_kg_per_l <= 0:
            raise ValueError(
                f"Density must be strictly positive (>0 kg/L), got {self.density_kg_per_l}"
            )
        if self.tolerance_pct < 0:
            raise ValueError("Density tolerance percentage cannot be negative")

    @property
    def specific_gravity(self) -> float:
        """Specific gravity relative to pure water at 4°C (1.000 kg/L)."""
        return self.density_kg_per_l


@dataclass
class ConversionResult:
    """Container for unit conversion calculation results."""

    sku_code: str
    sku_name: str
    category: str
    input_value: float
    output_value: float
    density_applied_kg_per_l: float
    conversion_direction: str  # "KG_TO_L" or "L_TO_KG"
    plant_id: str | None = None
    temperature_c: float = STANDARD_TEMP_CELSIUS
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def mass_kg(self) -> float:
        """Normalized mass in Kilograms."""
        return self.input_value if self.conversion_direction == "KG_TO_L" else self.output_value

    @property
    def volume_liters(self) -> float:
        """Normalized volume in Liters."""
        return self.output_value if self.conversion_direction == "KG_TO_L" else self.input_value

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary representation."""
        data = asdict(self)
        data["mass_kg"] = self.mass_kg
        data["volume_liters"] = self.volume_liters
        data["timestamp"] = self.timestamp.isoformat()
        return data


class SAPUnitConverter:
    """Enterprise converter from raw production KG to liquid sales Liters."""

    def __init__(self) -> None:
        self._registry: dict[str, MaterialMasterDensity] = {}
        self._load_canonical_sap_density_master()

    def _load_canonical_sap_density_master(self) -> None:
        """Pre-load canonical Nerolac Decorative and Industrial paint densities."""
        canonical_records = [
            # 1. Decorative Emulsions & Finishes
            MaterialMasterDensity(
                sku_code="DEC_EXT_EXCEL_WHITE",
                sku_name="Nerolac Excel Mica Marble Exterior White",
                category="DECORATIVE",
                sub_category="EXTERIOR_EMULSION",
                density_kg_per_l=1.42,
            ),
            MaterialMasterDensity(
                sku_code="DEC_INT_BEAUTY_GOLD",
                sku_name="Nerolac Beauty Gold Washable Interior Emulsion",
                category="DECORATIVE",
                sub_category="INTERIOR_EMULSION",
                density_kg_per_l=1.36,
            ),
            MaterialMasterDensity(
                sku_code="DEC_INT_IMPRESSIONS",
                sku_name="Nerolac Impressions Ultra HD Luxury Emulsion",
                category="DECORATIVE",
                sub_category="LUXURY_EMULSION",
                density_kg_per_l=1.32,
            ),
            MaterialMasterDensity(
                sku_code="DEC_SYN_GLOSS_ENAMEL",
                sku_name="Nerolac Synthetic Gloss Enamel Brilliant White",
                category="DECORATIVE",
                sub_category="SOLVENT_ENAMEL",
                density_kg_per_l=1.08,
            ),
            MaterialMasterDensity(
                sku_code="DEC_DIST_POPULAR",
                sku_name="Nerolac Popular Acrylic Distemper",
                category="DECORATIVE",
                sub_category="DISTEMPER",
                density_kg_per_l=1.48,
            ),
            MaterialMasterDensity(
                sku_code="DEC_PRIME_EXT_ACRYLIC",
                sku_name="Nerolac Exterior Wall Primer",
                category="DECORATIVE",
                sub_category="PRIMER",
                density_kg_per_l=1.30,
            ),
            # 2. Industrial Protective & Floor Coatings
            MaterialMasterDensity(
                sku_code="IND_EPOXY_FLOOR_GR",
                sku_name="Neropoxy High Build Floor Coating Grey",
                category="INDUSTRIAL",
                sub_category="EPOXY_FLOOR",
                density_kg_per_l=1.52,
            ),
            MaterialMasterDensity(
                sku_code="IND_EPOXY_PRIME_ZN",
                sku_name="Nerolac Epoxy Zinc Phosphate Primer",
                category="INDUSTRIAL",
                sub_category="EPOXY_PRIMER",
                density_kg_per_l=1.45,
            ),
            MaterialMasterDensity(
                sku_code="IND_PU_TOPCOAT_WHITE",
                sku_name="Nerolac Polyurethane Two-Pack Topcoat White",
                category="INDUSTRIAL",
                sub_category="PU_COATING",
                density_kg_per_l=1.18,
            ),
            MaterialMasterDensity(
                sku_code="IND_THINNER_PU",
                sku_name="Nerolac Industrial General PU Thinner",
                category="INDUSTRIAL",
                sub_category="SOLVENT_THINNER",
                density_kg_per_l=0.84,
            ),
            # 3. Automotive OEM & Refinish Coatings
            MaterialMasterDensity(
                sku_code="AUTO_CLEAR_2K",
                sku_name="Nerolac 2K Automotive OEM Clearcoat",
                category="AUTOMOTIVE",
                sub_category="CLEARCOAT",
                density_kg_per_l=0.98,
            ),
            MaterialMasterDensity(
                sku_code="AUTO_SURFACER_GREY",
                sku_name="Nerolac 2K High Build Surfacer Grey",
                category="AUTOMOTIVE",
                sub_category="SURFACER",
                density_kg_per_l=1.38,
            ),
        ]
        for item in canonical_records:
            self.register_density(item)

    def register_density(self, record: MaterialMasterDensity) -> None:
        """Register or update a SKU density specification from SAP MARA/MARC."""
        key = self._format_key(record.sku_code, record.plant_id)
        self._registry[key] = record
        # Also map without plant_id as universal fallback
        if record.plant_id:
            universal_key = self._format_key(record.sku_code, None)
            if universal_key not in self._registry:
                self._registry[universal_key] = record

    @staticmethod
    def _format_key(sku_code: str, plant_id: str | None) -> str:
        code_clean = sku_code.strip().upper()
        return f"{code_clean}@{plant_id.strip().upper()}" if plant_id else code_clean

    def get_sku_density(
        self,
        sku_code: str,
        plant_id: str | None = None,
        category_hint: str | None = None,
    ) -> MaterialMasterDensity:
        """Lookup SKU density record from registry with fallback support."""
        # 1. Exact match with plant_id
        if plant_id:
            key_plant = self._format_key(sku_code, plant_id)
            if key_plant in self._registry:
                return self._registry[key_plant]

        # 2. Universal match without plant_id
        key_universal = self._format_key(sku_code, None)
        if key_universal in self._registry:
            return self._registry[key_universal]

        # 3. Category fallback
        cat = (category_hint or "DEFAULT").strip().upper()
        fallback_val = CATEGORY_FALLBACK_DENSITIES.get(cat, CATEGORY_FALLBACK_DENSITIES["DEFAULT"])
        logger.info(
            "SKU '%s' not found in SAP Material Master density table. "
            "Applying category fallback (%s: %.2f kg/L)",
            sku_code,
            cat,
            fallback_val,
        )
        return MaterialMasterDensity(
            sku_code=sku_code.strip().upper(),
            sku_name=f"Generic {cat.capitalize()} Paint SKU",
            category=cat,
            density_kg_per_l=fallback_val,
            plant_id=plant_id,
            source_table="CATEGORY_FALLBACK",
        )

    def compute_temperature_adjusted_density(
        self,
        base_density: float,
        temperature_c: float,
        reference_temp_c: float = STANDARD_TEMP_CELSIUS,
    ) -> float:
        """Adjust density for liquid thermal expansion at non-standard temperatures."""
        if temperature_c < -10.0 or temperature_c > 80.0:
            raise ValueError(
                f"Operating temperature {temperature_c}°C outside operational bounds (-10°C..80°C)"
            )
        delta_t = temperature_c - reference_temp_c
        adjusted = base_density / (1.0 + THERMAL_EXPANSION_COEFF * delta_t)
        return round(adjusted, 4)

    def convert_kg_to_liters(
        self,
        mass_kg: float,
        sku_code: str,
        plant_id: str | None = None,
        override_density: float | None = None,
        temperature_c: float = STANDARD_TEMP_CELSIUS,
        category_hint: str | None = None,
    ) -> ConversionResult:
        """Convert production mass in Kilograms to liquid sales volume in Liters.

        Formula: Liters = Mass (KG) / Density (kg/L)
        """
        if mass_kg < 0:
            raise ValueError(f"Mass in KG cannot be negative, got {mass_kg}")

        if override_density is not None:
            if override_density <= 0:
                raise ValueError("Override density must be strictly positive (>0 kg/L)")
            effective_density = override_density
            master_record = MaterialMasterDensity(
                sku_code=sku_code.strip().upper(),
                sku_name=f"Custom Density SKU ({override_density} kg/L)",
                category=category_hint or "CUSTOM",
                density_kg_per_l=override_density,
                plant_id=plant_id,
                source_table="MANUAL_OVERRIDE",
            )
        else:
            master_record = self.get_sku_density(
                sku_code, plant_id=plant_id, category_hint=category_hint
            )
            effective_density = master_record.density_kg_per_l

        if temperature_c != master_record.reference_temp_c:
            effective_density = self.compute_temperature_adjusted_density(
                effective_density, temperature_c, master_record.reference_temp_c
            )

        liters = round(mass_kg / effective_density, 4) if effective_density > 0 else 0.0

        return ConversionResult(
            sku_code=master_record.sku_code,
            sku_name=master_record.sku_name,
            category=master_record.category,
            input_value=round(mass_kg, 4),
            output_value=liters,
            density_applied_kg_per_l=effective_density,
            conversion_direction="KG_TO_L",
            plant_id=plant_id,
            temperature_c=temperature_c,
        )

    def convert_liters_to_kg(
        self,
        volume_liters: float,
        sku_code: str,
        plant_id: str | None = None,
        override_density: float | None = None,
        temperature_c: float = STANDARD_TEMP_CELSIUS,
        category_hint: str | None = None,
    ) -> ConversionResult:
        """Convert sales volume in Liters to production mass in Kilograms.

        Formula: Mass (KG) = Volume (Liters) * Density (kg/L)
        """
        if volume_liters < 0:
            raise ValueError(f"Volume in Liters cannot be negative, got {volume_liters}")

        if override_density is not None:
            if override_density <= 0:
                raise ValueError("Override density must be strictly positive (>0 kg/L)")
            effective_density = override_density
            master_record = MaterialMasterDensity(
                sku_code=sku_code.strip().upper(),
                sku_name=f"Custom Density SKU ({override_density} kg/L)",
                category=category_hint or "CUSTOM",
                density_kg_per_l=override_density,
                plant_id=plant_id,
                source_table="MANUAL_OVERRIDE",
            )
        else:
            master_record = self.get_sku_density(
                sku_code, plant_id=plant_id, category_hint=category_hint
            )
            effective_density = master_record.density_kg_per_l

        if temperature_c != master_record.reference_temp_c:
            effective_density = self.compute_temperature_adjusted_density(
                effective_density, temperature_c, master_record.reference_temp_c
            )

        mass_kg = round(volume_liters * effective_density, 4)

        return ConversionResult(
            sku_code=master_record.sku_code,
            sku_name=master_record.sku_name,
            category=master_record.category,
            input_value=round(volume_liters, 4),
            output_value=mass_kg,
            density_applied_kg_per_l=effective_density,
            conversion_direction="L_TO_KG",
            plant_id=plant_id,
            temperature_c=temperature_c,
        )

    def batch_convert_kg_to_liters(
        self,
        items: Sequence[tuple[float, str] | dict[str, Any]],
        plant_id: str | None = None,
    ) -> list[ConversionResult]:
        """Convert a batch sequence of (mass_kg, sku_code) to liquid liters."""
        results: list[ConversionResult] = []
        for item in items:
            if isinstance(item, (tuple, list)):
                mass_val = float(item[0])
                sku_val = str(item[1])
                results.append(self.convert_kg_to_liters(mass_val, sku_val, plant_id=plant_id))
            elif isinstance(item, dict):
                raw_mass = item.get("mass_kg")
                if raw_mass is None:
                    raw_mass = item.get("quantity_kg", 0.0)
                mass_val = float(raw_mass if raw_mass is not None else 0.0)
                sku_val = str(item.get("sku_code") or item.get("sku_id") or "")
                p_id = item.get("plant_id", plant_id)
                results.append(self.convert_kg_to_liters(mass_val, sku_val, plant_id=p_id))
        return results
