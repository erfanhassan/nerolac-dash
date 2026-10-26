"""Procurement Register (SAP ME2L) Validation Schemas.

Enforces:
1. Valid calendar purchase order (PO) date.
2. Non-empty vendor identifier or supplier name.
3. Non-empty material code.
4. Unit price in Bangladeshi Taka (BDT, strictly positive numeric > 0).
5. Purchase quantity (strictly positive numeric > 0).
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any

import pandera.pandas as pa
from pandera.typing import Series
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class ProcurementSchema(BaseModel):
    """Pydantic v2 row validation model for SAP ME2L Procurement Register."""

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )

    po_date: date = Field(
        ...,
        validation_alias=AliasChoices(
            "po_date",
            "purchase_date",
            "date",
            "PO_DATE",
            "PURCHASE_DATE",
            "DATE",
        ),
        description="Purchase order / transaction date",
    )
    vendor_name: str = Field(
        ...,
        validation_alias=AliasChoices(
            "vendor_name",
            "vendor_id",
            "supplier_name",
            "supplier_id",
            "VENDOR_NAME",
            "VENDOR_ID",
            "SUPPLIER_NAME",
        ),
        description="Supplier / vendor trade name or ID",
    )
    material_code: str = Field(
        ...,
        validation_alias=AliasChoices(
            "material_code",
            "material_id",
            "item_code",
            "MATERIAL_CODE",
            "MATERIAL_ID",
        ),
        description="Raw material or chemical catalog code",
    )
    unit_price: float = Field(
        ...,
        validation_alias=AliasChoices(
            "unit_price",
            "unit_price_bdt",
            "unit_cost",
            "UNIT_PRICE",
            "UNIT_PRICE_BDT",
            "UNIT_COST",
        ),
        description="Unit cost/price in BDT (> 0)",
    )
    quantity: float = Field(
        ...,
        validation_alias=AliasChoices("quantity", "qty", "QUANTITY", "QTY"),
        description="Purchased material quantity (> 0)",
    )
    depot_id: str = Field(
        default="DEPOT_01",
        validation_alias=AliasChoices("depot_id", "plant_id", "DEPOT_ID", "PLANT_ID"),
        description="Receiving plant / depot identifier",
    )

    @field_validator("vendor_name", "material_code", "depot_id")
    @classmethod
    def validate_non_empty_strings(cls, v: str, info: Any) -> str:
        """Ensure string identifiers are non-empty."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError(f"{info.field_name} cannot be empty.")
        return cleaned

    @field_validator("unit_price", mode="before")
    @classmethod
    def validate_unit_price(cls, v: Any) -> float:
        """Validate unit price in BDT is strictly positive and finite."""
        try:
            val = float(str(v).strip().replace(",", ""))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Unit price must be a valid number, got '{v}'") from exc

        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"Unit price must be a finite number, got '{val}'")
        if val <= 0.0:
            raise ValueError(f"Unit price in BDT must be strictly positive (> 0), got '{val}'")
        return val

    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity(cls, v: Any) -> float:
        """Validate quantity is strictly positive and finite."""
        try:
            val = float(str(v).strip().replace(",", ""))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Quantity must be a valid number, got '{v}'") from exc

        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"Quantity must be a finite number, got '{val}'")
        if val <= 0.0:
            raise ValueError(f"Quantity must be strictly positive (> 0), got '{val}'")
        return val


class ProcurementPanderaModel(pa.DataFrameModel):
    """Pandera DataFrame model for batch validation of SAP ME2L procurement drops."""

    vendor_name: Series[str] = pa.Field(
        str_length={"min_value": 1},
        description="Supplier / vendor name",
    )
    material_code: Series[str] = pa.Field(
        str_length={"min_value": 1},
        description="Material code",
    )
    unit_price: Series[float] = pa.Field(
        gt=0.0,
        description="Unit price in BDT (> 0)",
    )
    quantity: Series[float] = pa.Field(
        gt=0.0,
        description="Quantity (> 0)",
    )

    class Config:
        strict = False
        coerce = True


procurement_pandera_schema = pa.DataFrameSchema(
    columns={
        "vendor_name": pa.Column(
            str,
            checks=[pa.Check.str_length(min_value=1)],
            nullable=False,
            coerce=True,
        ),
        "material_code": pa.Column(
            str,
            checks=[pa.Check.str_length(min_value=1)],
            nullable=False,
            coerce=True,
        ),
        "unit_price": pa.Column(
            float,
            checks=[pa.Check.gt(0.0)],
            nullable=False,
            coerce=True,
        ),
        "quantity": pa.Column(
            float,
            checks=[pa.Check.gt(0.0)],
            nullable=False,
            coerce=True,
        ),
    },
    strict=False,
    coerce=True,
)
