"""Enforce PostgreSQL Row-Level Security (RLS) policies on operational tables.

Revision ID: 005_enforce_row_level_security
Revises: 004_sales_stockout_flag
Create Date: 2026-10-27 04:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_enforce_row_level_security"
down_revision: str | None = "004_sales_stockout_flag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "nerolac_ops"


def upgrade() -> None:
    # 1. Seed CTG and DHK depot aliases
    op.execute(
        """
        INSERT INTO nerolac_ops.depots (depot_id, depot_code, depot_name, region)
        VALUES
            ('CTG', 'CTG', 'Chittagong Regional Depot', 'CHITTAGONG'),
            ('DHK', 'DHK', 'Dhaka Central Depot', 'DHAKA')
        ON CONFLICT (depot_id) DO NOTHING;
        """
    )

    # 2. Create Helper Functions
    op.execute(
        """
        CREATE OR REPLACE FUNCTION nerolac_ops.check_depot_access(row_depot_id VARCHAR)
        RETURNS BOOLEAN AS $$
        DECLARE
            curr_role VARCHAR;
            curr_depot VARCHAR;
        BEGIN
            curr_role := current_setting('app.current_user_role', true);
            IF curr_role IN (
                'SUPER_ADMIN', 'FINANCE_MANAGER', 'SALES_DIRECTOR',
                'AUDITOR', 'SUPPLY_CHAIN_PLANNER'
            ) THEN
                RETURN TRUE;
            END IF;

            IF curr_role IS NULL OR curr_role = '' THEN
                RETURN TRUE;
            END IF;

            IF curr_role IN ('DEPOT_MANAGER', 'FIELD_OFFICER') THEN
                curr_depot := current_setting('app.current_depot_id', true);
                IF curr_depot IS NULL OR curr_depot = '' THEN
                    RETURN FALSE;
                END IF;

                IF row_depot_id = curr_depot THEN
                    RETURN TRUE;
                END IF;

                IF (curr_depot = 'CTG' AND row_depot_id = 'DEPOT_02') OR
                   (curr_depot = 'DEPOT_02' AND row_depot_id = 'CTG') OR
                   (curr_depot = 'DHK' AND row_depot_id = 'DEPOT_01') OR
                   (curr_depot = 'DEPOT_01' AND row_depot_id = 'DHK') OR
                   (curr_depot = 'SYL' AND row_depot_id = 'DEPOT_03') OR
                   (curr_depot = 'DEPOT_03' AND row_depot_id = 'SYL') OR
                   (curr_depot = 'BGR' AND row_depot_id = 'DEPOT_04') OR
                   (curr_depot = 'DEPOT_04' AND row_depot_id = 'BGR') OR
                   (curr_depot = 'KLN' AND row_depot_id = 'DEPOT_05') OR
                   (curr_depot = 'DEPOT_05' AND row_depot_id = 'KLN') OR
                   (curr_depot = 'BAR' AND row_depot_id = 'DEPOT_06') OR
                   (curr_depot = 'DEPOT_06' AND row_depot_id = 'BAR') OR
                   (curr_depot = 'RNG' AND row_depot_id = 'DEPOT_07') OR
                   (curr_depot = 'DEPOT_07' AND row_depot_id = 'RNG') OR
                   (curr_depot = 'MYM' AND row_depot_id = 'DEPOT_08') OR
                   (curr_depot = 'DEPOT_08' AND row_depot_id = 'MYM') THEN
                    RETURN TRUE;
                END IF;

                IF EXISTS (
                    SELECT 1 FROM nerolac_ops.depots d
                    WHERE d.depot_id = row_depot_id
                      AND (d.depot_code = curr_depot OR d.region = curr_depot)
                ) THEN
                    RETURN TRUE;
                END IF;

                RETURN FALSE;
            END IF;

            RETURN FALSE;
        END;
        $$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION nerolac_ops.check_employee_kpi_access(target_employee_id VARCHAR)
        RETURNS BOOLEAN AS $$
        DECLARE
            curr_role VARCHAR;
            emp_depot VARCHAR;
        BEGIN
            curr_role := current_setting('app.current_user_role', true);
            IF curr_role IN (
                'SUPER_ADMIN', 'FINANCE_MANAGER', 'SALES_DIRECTOR',
                'AUDITOR', 'SUPPLY_CHAIN_PLANNER'
            ) THEN
                RETURN TRUE;
            END IF;

            IF curr_role IS NULL OR curr_role = '' THEN
                RETURN TRUE;
            END IF;

            SELECT depot_id INTO emp_depot
            FROM nerolac_ops.employees
            WHERE employee_id = target_employee_id;
            IF emp_depot IS NULL THEN
                RETURN FALSE;
            END IF;

            RETURN nerolac_ops.check_depot_access(emp_depot);
        END;
        $$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION nerolac_ops.check_whatsapp_sales_access(target_dealer_id VARCHAR)
        RETURNS BOOLEAN AS $$
        DECLARE
            curr_role VARCHAR;
            dlr_depot VARCHAR;
        BEGIN
            curr_role := current_setting('app.current_user_role', true);
            IF curr_role IN (
                'SUPER_ADMIN', 'FINANCE_MANAGER', 'SALES_DIRECTOR',
                'AUDITOR', 'SUPPLY_CHAIN_PLANNER'
            ) THEN
                RETURN TRUE;
            END IF;

            IF curr_role IS NULL OR curr_role = '' THEN
                RETURN TRUE;
            END IF;

            IF target_dealer_id IS NULL THEN
                RETURN FALSE;
            END IF;

            SELECT depot_id INTO dlr_depot
            FROM nerolac_ops.dealers
            WHERE dealer_id = target_dealer_id;
            IF dlr_depot IS NULL THEN
                RETURN FALSE;
            END IF;

            RETURN nerolac_ops.check_depot_access(dlr_depot);
        END;
        $$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
        """
    )

    # 3. Apply RLS on 4 operational tables
    tables = [
        ("financial_actuals", "nerolac_ops.check_depot_access(depot_id)"),
        ("historical_sales", "nerolac_ops.check_depot_access(depot_id)"),
        ("employee_kpi_scores", "nerolac_ops.check_employee_kpi_access(employee_id)"),
        ("whatsapp_parsed_sales", "nerolac_ops.check_whatsapp_sales_access(dealer_id)"),
    ]

    for tbl, condition in tables:
        op.execute(f"ALTER TABLE nerolac_ops.{tbl} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE nerolac_ops.{tbl} FORCE ROW LEVEL SECURITY;")
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_depot_isolation ON nerolac_ops.{tbl};")
        op.execute(
            f"""
            CREATE POLICY rls_{tbl}_depot_isolation ON nerolac_ops.{tbl}
            FOR ALL
            USING ({condition})
            WITH CHECK ({condition});
            """
        )


def downgrade() -> None:
    tables = [
        "financial_actuals",
        "historical_sales",
        "employee_kpi_scores",
        "whatsapp_parsed_sales",
    ]
    for tbl in tables:
        op.execute(f"DROP POLICY IF EXISTS rls_{tbl}_depot_isolation ON nerolac_ops.{tbl};")
        op.execute(f"ALTER TABLE nerolac_ops.{tbl} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE nerolac_ops.{tbl} DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP FUNCTION IF EXISTS nerolac_ops.check_whatsapp_sales_access(VARCHAR);")
    op.execute("DROP FUNCTION IF EXISTS nerolac_ops.check_employee_kpi_access(VARCHAR);")
    op.execute("DROP FUNCTION IF EXISTS nerolac_ops.check_depot_access(VARCHAR);")
