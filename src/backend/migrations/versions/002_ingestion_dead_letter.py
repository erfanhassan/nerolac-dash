"""Add ingestion_dead_letter table for quarantined malformed ETL rows.

Revision ID: 002_ingestion_dead_letter
Revises: 001_baseline_schema
Create Date: 2026-10-27 02:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_ingestion_dead_letter"
down_revision: str | None = "001_baseline_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "nerolac_ops"


def upgrade() -> None:
    op.create_table(
        "ingestion_dead_letter",
        sa.Column("dead_letter_id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("batch_id", sa.String(length=64), nullable=False),
        sa.Column("report_type", sa.String(length=32), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("validation_errors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="QUARANTINED", nullable=False),
        sa.Column(
            "quarantined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_dead_letter_batch_report",
        "ingestion_dead_letter",
        ["batch_id", "report_type"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_dead_letter_status_time",
        "ingestion_dead_letter",
        ["status", "quarantined_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_dead_letter_status_time",
        table_name="ingestion_dead_letter",
        schema=SCHEMA,
    )
    op.drop_index(
        "idx_dead_letter_batch_report",
        table_name="ingestion_dead_letter",
        schema=SCHEMA,
    )
    op.drop_table("ingestion_dead_letter", schema=SCHEMA)
