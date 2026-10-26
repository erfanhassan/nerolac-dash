"""Historical Sales (SAP VA05) Validation Schemas.

Enforces:
1. Valid calendar sales date.
2. Non-empty depot identifier.
3. Non-empty SKU code.
4. Paint volume in liters (non-negative numeric).
5. Net revenue in Bangladeshi Taka (BDT, non-negative numeric).
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


class HistoricalSalesSchema(BaseModel):
    """Pydantic v2 row validation model for SAP VA05 Historical Sales."""

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )

    sales_date: date = Field(
        ...,
        validation_alias=AliasChoices(
            "sales_date",
            "sale_date",
            "date",
            "SALES_DATE",
            "SALE_DATE",
            "DATE",
        ),
        description="Transaction or dispatch sales date",
    )
    depot_id: str = Field(
        ...,
        validation_alias=AliasChoices("depot_id", "plant_id", "DEPOT_ID", "PLANT_ID"),
        description="Fulfilling depot or distribution center identifier",
    )
    sku_code: str = Field(
        ...,
        validation_alias=AliasChoices("sku_code", "sku_id", "material_code", "SKU_CODE", "SKU_ID"),
        description="Product SKU code",
    )
    liters: float = Field(
        ...,
        validation_alias=AliasChoices(
            "liters",
            "quantity_liters",
            "volume_liters",
            "qty_liters",
            "LITERS",
            "QUANTITY_LITERS",
        ),
        description="Paint sales volume in liters (>= 0)",
    )
    net_revenue: float = Field(
        ...,
        validation_alias=AliasChoices(
            "net_revenue",
            "net_revenue_bdt",
            "revenue",
            "revenue_bdt",
            "NET_REVENUE",
            "NET_REVENUE_BDT",
        ),
        description="Net sales revenue in BDT (>= 0)",
    )

    @field_validator("depot_id", "sku_code")
    @classmethod
    def validate_non_empty_strings(cls, v: str, info: Any) -> str:
        """Validate string identifiers are non-empty."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError(f"{info.field_name} cannot be empty.")
        return cleaned

    @field_validator("liters", mode="before")
    @classmethod
    def validate_liters(cls, v: Any) -> float:
        """Validate paint volume in liters is non-negative and finite."""
        try:
            val = float(str(v).strip().replace(",", ""))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Sales volume in liters must be a valid number, got '{v}'") from exc

        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"Liters must be a finite number, got '{val}'")
        if val < 0.0:
            raise ValueError(f"Liters cannot be negative, got '{val}'")
        return val

    @field_validator("net_revenue", mode="before")
    @classmethod
    def validate_net_revenue(cls, v: Any) -> float:
        """Validate net revenue in BDT is non-negative and finite."""
        try:
            val = float(str(v).strip().replace(",", ""))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Net revenue in BDT must be a valid number, got '{v}'") from exc

        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"Net revenue must be a finite number, got '{val}'")
        if val < 0.0:
            raise ValueError(f"Net revenue in BDT cannot be negative, got '{val}'")
        return val


class HistoricalSalesPanderaModel(pa.DataFrameModel):
    """Pandera DataFrame model for batch validation of SAP VA05 sales drops."""

    depot_id: Series[str] = pa.Field(
        str_length={"min_value": 1},
        description="Depot identifier",
    )
    sku_code: Series[str] = pa.Field(
        str_length={"min_value": 1},
        description="SKU identifier",
    )
    liters: Series[float] = pa.Field(
        ge=0.0,
        description="Volume in liters (>= 0)",
    )
    net_revenue: Series[float] = pa.Field(
        ge=0.0,
        description="Net revenue in BDT (>= 0)",
    )

    class Config:
        strict = False
        coerce = True


historical_sales_pandera_schema = pa.DataFrameSchema(
    columns={
        "depot_id": pa.Column(
            str,
            checks=[pa.Check.str_length(min_value=1)],
            nullable=False,
            coerce=True,
        ),
        "sku_code": pa.Column(
            str,
            checks=[pa.Check.str_length(min_value=1)],
            nullable=False,
            coerce=True,
        ),
        "liters": pa.Column(
            float,
            checks=[pa.Check.ge(0.0)],
            nullable=False,
            coerce=True,
        ),
        "net_revenue": pa.Column(
            float,
            checks=[pa.Check.ge(0.0)],
            nullable=False,
            coerce=True,
        ),
    },
    strict=False,
    coerce=True,
)
