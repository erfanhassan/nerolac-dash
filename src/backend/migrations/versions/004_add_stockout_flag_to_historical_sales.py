"""Add is_stockout_flag to historical_sales for demand distortion prevention in ML models.

Revision ID: 004_add_stockout_flag_to_historical_sales
Revises: 003_sap_trial_balances
Create Date: 2026-10-27 02:57:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_sales_stockout_flag"
down_revision: str | None = "003_sap_trial_balances"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "nerolac_ops"


def upgrade() -> None:
    # 1. Add is_stockout_flag column to historical_sales
    op.add_column(
        "historical_sales",
        sa.Column(
            "is_stockout_flag",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        schema=SCHEMA,
    )

    # 2. Add index for stockout date filtering in downstream ML forecasting
    op.create_index(
        "idx_sales_stockout_date",
        "historical_sales",
        ["is_stockout_flag", "sales_date"],
        schema=SCHEMA,
    )

    # 3. Add composite lookup index for depot/sku stockout queries
    op.create_index(
        "idx_sales_depot_sku_stockout",
        "historical_sales",
        ["depot_id", "sku_id", "is_stockout_flag"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_sales_depot_sku_stockout",
        table_name="historical_sales",
        schema=SCHEMA,
    )
    op.drop_index(
        "idx_sales_stockout_date",
        table_name="historical_sales",
        schema=SCHEMA,
    )
    op.drop_column("historical_sales", "is_stockout_flag", schema=SCHEMA)
