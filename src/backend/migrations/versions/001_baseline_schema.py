"""Baseline migration establishing PostgreSQL 16 schema.

Revision ID: 001_baseline_schema
Revises: None
Create Date: 2026-10-27 01:30:00.000000

Matching: knowledge/Backend_Database_Schema_(PostgreSQL_16_DDL).md
- Enums: user_role_enum, message_status_enum, forecast_type_enum, ar_ap_type_enum
- Master Tables: depots, users, audit_logs, chart_of_accounts, territories, employees, skus, dealers
- Transactional Tables: financial_actuals, financial_budgets, procurement_register, ar_ap_aging,
  employee_kpi_scores, manpower_capacity_models, historical_sales, demand_forecasts,
  whatsapp_raw_messages, whatsapp_parsed_sales, daily_sales_reconciliations
- Composite Indexes: idx_fin_act_depot_time, idx_proc_mat_date, idx_emp_kpi_lookup,
  idx_sales_depot_sku_date, idx_forecast_lookup, idx_wa_status_received
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_baseline_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "nerolac_ops"


def upgrade() -> None:
    # 0. Ensure schema exists
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA};")

    # 1. Enums created via idempotent DO blocks
    op.execute(f"""
    DO $$ BEGIN
        CREATE TYPE {SCHEMA}.user_role_enum AS ENUM (
            'SUPER_ADMIN',
            'FINANCE_MANAGER',
            'SUPPLY_CHAIN_PLANNER',
            'SALES_DIRECTOR',
            'DEPOT_MANAGER',
            'FIELD_OFFICER',
            'AUDITOR'
        );
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """)

    op.execute(f"""
    DO $$ BEGIN
        CREATE TYPE {SCHEMA}.message_status_enum AS ENUM (
            'RECEIVED',
            'PROCESSING',
            'PARSED',
            'RECONCILED',
            'FAILED',
            'FLAGGED'
        );
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """)

    op.execute(f"""
    DO $$ BEGIN
        CREATE TYPE {SCHEMA}.forecast_type_enum AS ENUM (
            'STATISTICAL',
            'ML_ENSEMBLE',
            'EXECUTIVE_OVERRIDE',
            'FINAL_CONSENSUS'
        );
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """)

    op.execute(f"""
    DO $$ BEGIN
        CREATE TYPE {SCHEMA}.ar_ap_type_enum AS ENUM (
            'RECEIVABLE',
            'PAYABLE'
        );
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
    """)

    # Enum references for column typing (create_type=False to avoid recreation)
    user_role_enum = postgresql.ENUM(
        "SUPER_ADMIN",
        "FINANCE_MANAGER",
        "SUPPLY_CHAIN_PLANNER",
        "SALES_DIRECTOR",
        "DEPOT_MANAGER",
        "FIELD_OFFICER",
        "AUDITOR",
        name="user_role_enum",
        schema=SCHEMA,
        create_type=False,
    )

    message_status_enum = postgresql.ENUM(
        "RECEIVED",
        "PROCESSING",
        "PARSED",
        "RECONCILED",
        "FAILED",
        "FLAGGED",
        name="message_status_enum",
        schema=SCHEMA,
        create_type=False,
    )

    forecast_type_enum = postgresql.ENUM(
        "STATISTICAL",
        "ML_ENSEMBLE",
        "EXECUTIVE_OVERRIDE",
        "FINAL_CONSENSUS",
        name="forecast_type_enum",
        schema=SCHEMA,
        create_type=False,
    )

    ar_ap_type_enum = postgresql.ENUM(
        "RECEIVABLE",
        "PAYABLE",
        name="ar_ap_type_enum",
        schema=SCHEMA,
        create_type=False,
    )

    # 2. Master Tables
    # 2.1 Depots
    op.create_table(
        "depots",
        sa.Column("depot_id", sa.String(32), primary_key=True),
        sa.Column("depot_code", sa.String(32), nullable=False, unique=True),
        sa.Column("depot_name", sa.String(128), nullable=False),
        sa.Column("region", sa.String(64), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        schema=SCHEMA,
    )

    # 2.2 Users
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(128), nullable=False),
        sa.Column("role", user_role_enum, nullable=False, server_default="FIELD_OFFICER"),
        sa.Column(
            "depot_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.depots.depot_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("hashed_password", sa.String(255), nullable=False),
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
        schema=SCHEMA,
    )

    # 2.3 Audit Logs
    op.create_table(
        "audit_logs",
        sa.Column("log_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey(f"{SCHEMA}.users.user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("changes", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=SCHEMA,
    )

    # 2.4 Chart of Accounts
    op.create_table(
        "chart_of_accounts",
        sa.Column("account_id", sa.String(32), primary_key=True),
        sa.Column("account_code", sa.String(32), nullable=False, unique=True),
        sa.Column("account_name", sa.String(128), nullable=False),
        sa.Column("account_type", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=SCHEMA,
    )

    # 2.5 Territories
    op.create_table(
        "territories",
        sa.Column("territory_id", sa.String(32), primary_key=True),
        sa.Column("territory_code", sa.String(32), nullable=False, unique=True),
        sa.Column("territory_name", sa.String(128), nullable=False),
        sa.Column(
            "depot_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.depots.depot_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("district", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=SCHEMA,
    )

    # 2.6 Employees
    op.create_table(
        "employees",
        sa.Column("employee_id", sa.String(32), primary_key=True),
        sa.Column("employee_code", sa.String(32), nullable=False, unique=True),
        sa.Column("full_name", sa.String(128), nullable=False),
        sa.Column("department", sa.String(64), nullable=False),
        sa.Column("designation", sa.String(64), nullable=False),
        sa.Column(
            "depot_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.depots.depot_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "territory_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.territories.territory_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=SCHEMA,
    )

    # 2.7 SKUs
    op.create_table(
        "skus",
        sa.Column("sku_id", sa.String(32), primary_key=True),
        sa.Column("sku_code", sa.String(32), nullable=False, unique=True),
        sa.Column("sku_name", sa.String(256), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("sub_category", sa.String(64), nullable=True),
        sa.Column("unit_of_measure", sa.String(16), nullable=False, server_default="LITERS"),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=SCHEMA,
    )

    # 2.8 Dealers
    op.create_table(
        "dealers",
        sa.Column("dealer_id", sa.String(32), primary_key=True),
        sa.Column("dealer_code", sa.String(32), nullable=False, unique=True),
        sa.Column("trade_name", sa.String(256), nullable=False),
        sa.Column(
            "territory_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.territories.territory_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "depot_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.depots.depot_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("phone_number", sa.String(32), nullable=True),
        sa.Column(
            "credit_limit", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0.00")
        ),
        sa.Column(
            "outstanding_balance",
            sa.Numeric(14, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
        sa.Column("tier", sa.String(16), nullable=False, server_default="GOLD"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=SCHEMA,
    )

    # 3. Transactional Tables
    # 3.1 Financial Actuals
    op.create_table(
        "financial_actuals",
        sa.Column("actual_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "depot_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.depots.depot_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.chart_of_accounts.account_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("fiscal_month", sa.Integer(), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=SCHEMA,
    )

    # 3.2 Financial Budgets
    op.create_table(
        "financial_budgets",
        sa.Column("budget_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "depot_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.depots.depot_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.chart_of_accounts.account_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("budgeted_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("fiscal_month", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=SCHEMA,
    )

    # 3.3 Procurement Register
    op.create_table(
        "procurement_register",
        sa.Column("procurement_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "depot_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.depots.depot_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("material_code", sa.String(64), nullable=False),
        sa.Column("material_name", sa.String(128), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("supplier_name", sa.String(128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=SCHEMA,
    )

    # 3.4 AR / AP Aging
    op.create_table(
        "ar_ap_aging",
        sa.Column("aging_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("entry_type", ar_ap_type_enum, nullable=False),
        sa.Column("entity_code", sa.String(64), nullable=False),
        sa.Column(
            "depot_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.depots.depot_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "current_amount",
            sa.Numeric(14, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
        sa.Column("days_1_30", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("days_31_60", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("days_61_90", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0.00")),
        sa.Column(
            "days_90_plus",
            sa.Numeric(14, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=SCHEMA,
    )

    # 3.5 Employee KPI Scores
    op.create_table(
        "employee_kpi_scores",
        sa.Column("score_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "employee_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.employees.employee_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("assessment_period", sa.String(32), nullable=False),
        sa.Column("target_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("achieved_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("weightage", sa.Numeric(5, 2), nullable=False, server_default=sa.text("1.00")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=SCHEMA,
    )

    # 3.6 Manpower Capacity Models
    op.create_table(
        "manpower_capacity_models",
        sa.Column("capacity_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "depot_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.depots.depot_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("department", sa.String(64), nullable=False),
        sa.Column("required_headcount", sa.Integer(), nullable=False),
        sa.Column("active_headcount", sa.Integer(), nullable=False),
        sa.Column("model_period", sa.String(32), nullable=False),
        sa.Column(
            "utilization_rate",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("100.00"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=SCHEMA,
    )

    # 3.7 Historical Sales
    op.create_table(
        "historical_sales",
        sa.Column("sale_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "depot_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.depots.depot_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "sku_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.skus.sku_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "dealer_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.dealers.dealer_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("quantity_liters", sa.Numeric(14, 2), nullable=False),
        sa.Column("net_revenue", sa.Numeric(14, 2), nullable=False),
        sa.Column("sales_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=SCHEMA,
    )

    # 3.8 Demand Forecasts
    op.create_table(
        "demand_forecasts",
        sa.Column("forecast_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "depot_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.depots.depot_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "sku_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.skus.sku_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("forecast_date", sa.Date(), nullable=False),
        sa.Column(
            "forecast_type",
            forecast_type_enum,
            nullable=False,
            server_default="STATISTICAL",
        ),
        sa.Column("projected_quantity_liters", sa.Numeric(14, 2), nullable=False),
        sa.Column("confidence_lower", sa.Numeric(14, 2), nullable=True),
        sa.Column("confidence_upper", sa.Numeric(14, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=SCHEMA,
    )

    # 3.9 WhatsApp Raw Messages
    op.create_table(
        "whatsapp_raw_messages",
        sa.Column("raw_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("waba_message_id", sa.String(128), nullable=False, unique=True),
        sa.Column("sender_phone", sa.String(32), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", message_status_enum, nullable=False, server_default="RECEIVED"),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )

    # 3.10 WhatsApp Parsed Sales
    op.create_table(
        "whatsapp_parsed_sales",
        sa.Column("parsed_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "raw_message_id",
            sa.BigInteger(),
            sa.ForeignKey(f"{SCHEMA}.whatsapp_raw_messages.raw_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dealer_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.dealers.dealer_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "sku_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.skus.sku_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("parsed_quantity", sa.Numeric(14, 2), nullable=False),
        sa.Column("parsed_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=SCHEMA,
    )

    # 3.11 Daily Sales Reconciliations
    op.create_table(
        "daily_sales_reconciliations",
        sa.Column("reconciliation_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("reconciliation_date", sa.Date(), nullable=False),
        sa.Column(
            "depot_id",
            sa.String(32),
            sa.ForeignKey(f"{SCHEMA}.depots.depot_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "sap_reported_sales",
            sa.Numeric(14, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
        sa.Column(
            "whatsapp_parsed_sales",
            sa.Numeric(14, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
        sa.Column("variance", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("status", sa.String(32), nullable=False, server_default="BALANCED"),
        sa.Column(
            "reconciled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=SCHEMA,
    )

    # 4. Composite Indexes
    # 4.1 idx_fin_act_depot_time on financial_actuals (depot_id, fiscal_year, fiscal_month)
    op.create_index(
        "idx_fin_act_depot_time",
        "financial_actuals",
        ["depot_id", "fiscal_year", "fiscal_month"],
        schema=SCHEMA,
    )

    # 4.2 idx_proc_mat_date on procurement_register (material_code, purchase_date)
    op.create_index(
        "idx_proc_mat_date",
        "procurement_register",
        ["material_code", "purchase_date"],
        schema=SCHEMA,
    )

    # 4.3 idx_emp_kpi_lookup on employee_kpi_scores (employee_id, assessment_period)
    op.create_index(
        "idx_emp_kpi_lookup",
        "employee_kpi_scores",
        ["employee_id", "assessment_period"],
        schema=SCHEMA,
    )

    # 4.4 idx_sales_depot_sku_date on historical_sales (depot_id, sku_id, sales_date)
    op.create_index(
        "idx_sales_depot_sku_date",
        "historical_sales",
        ["depot_id", "sku_id", "sales_date"],
        schema=SCHEMA,
    )

    # 4.5 idx_forecast_lookup on demand_forecasts (depot_id, sku_id, forecast_date, forecast_type)
    op.create_index(
        "idx_forecast_lookup",
        "demand_forecasts",
        ["depot_id", "sku_id", "forecast_date", "forecast_type"],
        schema=SCHEMA,
    )

    # 4.6 idx_wa_status_received on whatsapp_raw_messages (status, received_at)
    op.create_index(
        "idx_wa_status_received",
        "whatsapp_raw_messages",
        ["status", "received_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    # 1. Drop composite indexes
    op.drop_index("idx_wa_status_received", table_name="whatsapp_raw_messages", schema=SCHEMA)
    op.drop_index("idx_forecast_lookup", table_name="demand_forecasts", schema=SCHEMA)
    op.drop_index("idx_sales_depot_sku_date", table_name="historical_sales", schema=SCHEMA)
    op.drop_index("idx_emp_kpi_lookup", table_name="employee_kpi_scores", schema=SCHEMA)
    op.drop_index("idx_proc_mat_date", table_name="procurement_register", schema=SCHEMA)
    op.drop_index("idx_fin_act_depot_time", table_name="financial_actuals", schema=SCHEMA)

    # 2. Drop Transactional Tables
    op.drop_table("daily_sales_reconciliations", schema=SCHEMA)
    op.drop_table("whatsapp_parsed_sales", schema=SCHEMA)
    op.drop_table("whatsapp_raw_messages", schema=SCHEMA)
    op.drop_table("demand_forecasts", schema=SCHEMA)
    op.drop_table("historical_sales", schema=SCHEMA)
    op.drop_table("manpower_capacity_models", schema=SCHEMA)
    op.drop_table("employee_kpi_scores", schema=SCHEMA)
    op.drop_table("ar_ap_aging", schema=SCHEMA)
    op.drop_table("procurement_register", schema=SCHEMA)
    op.drop_table("financial_budgets", schema=SCHEMA)
    op.drop_table("financial_actuals", schema=SCHEMA)

    # 3. Drop Master Tables
    op.drop_table("dealers", schema=SCHEMA)
    op.drop_table("skus", schema=SCHEMA)
    op.drop_table("employees", schema=SCHEMA)
    op.drop_table("territories", schema=SCHEMA)
    op.drop_table("chart_of_accounts", schema=SCHEMA)
    op.drop_table("audit_logs", schema=SCHEMA)
    op.drop_table("users", schema=SCHEMA)
    op.drop_table("depots", schema=SCHEMA)

    # 4. Drop Enums
    op.execute(f"DROP TYPE IF EXISTS {SCHEMA}.ar_ap_type_enum CASCADE;")
    op.execute(f"DROP TYPE IF EXISTS {SCHEMA}.forecast_type_enum CASCADE;")
    op.execute(f"DROP TYPE IF EXISTS {SCHEMA}.message_status_enum CASCADE;")
    op.execute(f"DROP TYPE IF EXISTS {SCHEMA}.user_role_enum CASCADE;")
