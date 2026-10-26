"""Financial Actuals (SAP FAGLL03) Validation Schemas.

Enforces:
1. General Ledger (GL) Codes strictly within 10000–10017 range.
2. Fiscal Year (2000–2100) and Fiscal Month (1–12).
3. Segment codes (non-empty string, e.g., DECORATIVE, INDUSTRIAL, AUTO, POWDER).
4. Monetary amounts in Bangladeshi Taka (BDT).
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

MIN_GL_CODE = 10000
MAX_GL_CODE = 10017


class FinancialActualsSchema(BaseModel):
    """Pydantic v2 row validation model for SAP FAGLL03 Financial Actuals."""

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )

    gl_code: int = Field(
        ...,
        validation_alias=AliasChoices(
            "gl_code",
            "account_id",
            "account_code",
            "gl_account",
            "GL_CODE",
            "ACCOUNT_ID",
        ),
        description="SAP General Ledger Account Code (range 10000–10017)",
    )
    fiscal_year: int = Field(
        ...,
        validation_alias=AliasChoices("fiscal_year", "year", "FISCAL_YEAR", "YEAR"),
        description="Accounting fiscal year (2000–2100)",
    )
    fiscal_month: int = Field(
        ...,
        validation_alias=AliasChoices("fiscal_month", "month", "FISCAL_MONTH", "MONTH"),
        description="Accounting fiscal month (1–12)",
    )
    segment_code: str = Field(
        ...,
        validation_alias=AliasChoices("segment_code", "segment", "SEGMENT_CODE", "SEGMENT"),
        description="Business operational segment code",
    )
    amount: float = Field(
        ...,
        validation_alias=AliasChoices("amount", "amount_bdt", "AMOUNT", "AMOUNT_BDT"),
        description="Financial actual transaction amount in BDT",
    )
    depot_id: str = Field(
        default="DEPOT_01",
        validation_alias=AliasChoices("depot_id", "DEPOT_ID", "plant_id"),
        description="Target depot / plant identifier",
    )
    transaction_date: date | None = Field(
        default=None,
        validation_alias=AliasChoices("transaction_date", "date", "TRANSACTION_DATE", "DATE"),
        description="Calendar date of transaction",
    )

    @field_validator("gl_code", mode="before")
    @classmethod
    def validate_gl_code(cls, v: Any) -> int:
        """Validate GL code is strictly between 10000 and 10017."""
        try:
            val = int(str(v).strip())
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"GL code must be an integer between {MIN_GL_CODE} and {MAX_GL_CODE}, got '{v}'"
            ) from exc

        if not (MIN_GL_CODE <= val <= MAX_GL_CODE):
            raise ValueError(
                f"GL code '{val}' is outside authorized SAP Chart of Accounts range "
                f"({MIN_GL_CODE}–{MAX_GL_CODE})."
            )
        return val

    @field_validator("fiscal_year", mode="before")
    @classmethod
    def validate_fiscal_year(cls, v: Any) -> int:
        """Validate fiscal year is within reasonable bounds."""
        val = int(str(v).strip())
        if not (2000 <= val <= 2100):
            raise ValueError(f"Fiscal year '{val}' is outside allowed range 2000–2100.")
        return val

    @field_validator("fiscal_month", mode="before")
    @classmethod
    def validate_fiscal_month(cls, v: Any) -> int:
        """Validate fiscal month is between 1 and 12."""
        val = int(str(v).strip())
        if not (1 <= val <= 12):
            raise ValueError(f"Fiscal month '{val}' is invalid. Must be between 1 and 12.")
        return val

    @field_validator("segment_code")
    @classmethod
    def validate_segment_code(cls, v: str) -> str:
        """Ensure segment code is non-empty string."""
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("Segment code cannot be empty.")
        return cleaned

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v: Any) -> float:
        """Validate monetary amount is finite number."""
        try:
            val = float(str(v).strip().replace(",", ""))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Amount in BDT must be a valid numeric figure, got '{v}'") from exc

        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"Amount must be a finite number, got '{val}'")
        return val


class FinancialActualsPanderaModel(pa.DataFrameModel):
    """Pandera DataFrame model for batch validation of SAP FAGLL03 tabular drops."""

    gl_code: Series[int] = pa.Field(
        in_range={"min_value": MIN_GL_CODE, "max_value": MAX_GL_CODE},
        description="GL codes in range 10000–10017",
    )
    fiscal_year: Series[int] = pa.Field(
        in_range={"min_value": 2000, "max_value": 2100},
        description="Fiscal year",
    )
    fiscal_month: Series[int] = pa.Field(
        in_range={"min_value": 1, "max_value": 12},
        description="Fiscal month (1–12)",
    )
    segment_code: Series[str] = pa.Field(
        str_length={"min_value": 1},
        description="Operational business segment",
    )
    amount: Series[float] = pa.Field(
        description="Monetary transaction amount in BDT",
    )

    class Config:
        strict = False
        coerce = True


financial_actuals_pandera_schema = pa.DataFrameSchema(
    columns={
        "gl_code": pa.Column(
            int,
            checks=[pa.Check.in_range(MIN_GL_CODE, MAX_GL_CODE)],
            nullable=False,
            coerce=True,
        ),
        "fiscal_year": pa.Column(
            int,
            checks=[pa.Check.in_range(2000, 2100)],
            nullable=False,
            coerce=True,
        ),
        "fiscal_month": pa.Column(
            int,
            checks=[pa.Check.in_range(1, 12)],
            nullable=False,
            coerce=True,
        ),
        "segment_code": pa.Column(
            str,
            checks=[pa.Check.str_length(min_value=1)],
            nullable=False,
            coerce=True,
        ),
        "amount": pa.Column(
            float,
            nullable=False,
            coerce=True,
        ),
    },
    strict=False,
    coerce=True,
)
