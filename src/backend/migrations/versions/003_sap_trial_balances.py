"""Add sap_trial_balances table and historical_sales unique index for historical backfills.

Revision ID: 003_sap_trial_balances
Revises: 002_ingestion_dead_letter
Create Date: 2026-10-27 02:45:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_sap_trial_balances"
down_revision: str | None = "002_ingestion_dead_letter"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "nerolac_ops"


def upgrade() -> None:
    # 1. Create sap_trial_balances table for 12-24 month historical SAP trial balance imports
    op.create_table(
        "sap_trial_balances",
        sa.Column(
            "trial_balance_id",
            sa.BigInteger(),
            sa.Identity(always=False),
            primary_key=True,
        ),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("fiscal_month", sa.Integer(), nullable=False),
        sa.Column("depot_id", sa.String(length=32), nullable=False),
        sa.Column("gl_code", sa.String(length=32), nullable=False),
        sa.Column("segment_code", sa.String(length=64), nullable=False),
        sa.Column(
            "amount",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "fiscal_year",
            "fiscal_month",
            "depot_id",
            "gl_code",
            "segment_code",
            name="uq_trial_balance_composite",
        ),
        schema=SCHEMA,
    )

    # 2. Add performance lookup index on sap_trial_balances
    op.create_index(
        "idx_sap_tb_lookup",
        "sap_trial_balances",
        ["depot_id", "fiscal_year", "fiscal_month", "gl_code"],
        schema=SCHEMA,
    )

    # 3. Ensure unique index on historical_sales for idempotent sales backfill
    op.create_index(
        "uq_historical_sales_depot_sku_date",
        "historical_sales",
        ["depot_id", "sku_id", "sales_date"],
        unique=True,
        if_not_exists=True,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_historical_sales_depot_sku_date",
        table_name="historical_sales",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_index(
        "idx_sap_tb_lookup",
        table_name="sap_trial_balances",
        schema=SCHEMA,
    )
    op.drop_table("sap_trial_balances", schema=SCHEMA)
