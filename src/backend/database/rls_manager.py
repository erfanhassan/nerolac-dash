"""PostgreSQL Row-Level Security (RLS) Manager.

Enforces:
1. Enabling and forcing RLS on sensitive operational tables:
   - nerolac_ops.financial_actuals
   - nerolac_ops.historical_sales
   - nerolac_ops.employee_kpi_scores
   - nerolac_ops.whatsapp_parsed_sales
2. Session variable evaluation via:
   - current_setting('app.current_depot_id', true)
   - current_setting('app.current_user_role', true)
3. Regional data isolation: Depot Managers and Field Officers are restricted to their depot.
4. Executive bypass for corporate roles (SUPER_ADMIN, FINANCE_MANAGER, SALES_DIRECTOR, etc.).
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from src.backend.config.vault import get_vault_client
from src.backend.database.session_router import get_routing_manager

logger = logging.getLogger("nerolac.database.rls")

# SQL DDL for PostgreSQL 16 Row-Level Security Setup
RLS_SETUP_SQL = """
-- 0. Ensure non-superuser RLS enforcement role exists
DO $$ BEGIN
    CREATE ROLE nerolac_rls_user WITH NOSUPERUSER NOBYPASSRLS;
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;
GRANT USAGE ON SCHEMA nerolac_ops TO nerolac_rls_user;
GRANT ALL ON ALL TABLES IN SCHEMA nerolac_ops TO nerolac_rls_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA nerolac_ops TO nerolac_rls_user;
GRANT ALL ON ALL ROUTINES IN SCHEMA nerolac_ops TO nerolac_rls_user;
GRANT nerolac_rls_user TO nerolac_app;

-- 1. Ensure depot code mappings for CTG and DHK exist in depots table
INSERT INTO nerolac_ops.depots (depot_id, depot_code, depot_name, region)
VALUES
    ('CTG', 'CTG', 'Chittagong Regional Depot', 'CHITTAGONG'),
    ('DHK', 'DHK', 'Dhaka Central Depot', 'DHAKA')
ON CONFLICT (depot_id) DO NOTHING;

-- 2. Define Helper Functions in nerolac_ops schema
CREATE OR REPLACE FUNCTION nerolac_ops.check_depot_access(row_depot_id VARCHAR)
RETURNS BOOLEAN AS $$
DECLARE
    curr_role VARCHAR;
    curr_depot VARCHAR;
BEGIN
    curr_role := current_setting('app.current_user_role', true);

    -- Corporate executive roles have unrestricted global access
    IF curr_role IN (
        'SUPER_ADMIN', 'FINANCE_MANAGER', 'SALES_DIRECTOR',
        'AUDITOR', 'SUPPLY_CHAIN_PLANNER'
    ) THEN
        RETURN TRUE;
    END IF;

    -- If no role is set (e.g. automated ETL scripts, direct superuser DB connection) allow access
    IF curr_role IS NULL OR curr_role = '' THEN
        RETURN TRUE;
    END IF;

    -- Regional roles: DEPOT_MANAGER and FIELD_OFFICER
    IF curr_role IN ('DEPOT_MANAGER', 'FIELD_OFFICER') THEN
        curr_depot := current_setting('app.current_depot_id', true);
        IF curr_depot IS NULL OR curr_depot = '' THEN
            RETURN FALSE;
        END IF;

        -- Exact depot match
        IF row_depot_id = curr_depot THEN
            RETURN TRUE;
        END IF;

        -- Alias / code resolution (CTG <-> DEPOT_02, DHK <-> DEPOT_01, SYL <-> DEPOT_03, etc.)
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

        -- Check if row_depot_id matches depot_code or region in depots table
        IF EXISTS (
            SELECT 1 FROM nerolac_ops.depots d
            WHERE d.depot_id = row_depot_id
              AND (d.depot_code = curr_depot OR d.region = curr_depot)
        ) THEN
            RETURN TRUE;
        END IF;

        RETURN FALSE;
    END IF;

    -- Unrecognized role defaults to denied
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;


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

-- 3. Table 1: nerolac_ops.financial_actuals
ALTER TABLE nerolac_ops.financial_actuals ENABLE ROW LEVEL SECURITY;
ALTER TABLE nerolac_ops.financial_actuals FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rls_financial_actuals_depot_isolation ON nerolac_ops.financial_actuals;
CREATE POLICY rls_financial_actuals_depot_isolation ON nerolac_ops.financial_actuals
FOR ALL
USING (nerolac_ops.check_depot_access(depot_id))
WITH CHECK (nerolac_ops.check_depot_access(depot_id));

-- 4. Table 2: nerolac_ops.historical_sales
ALTER TABLE nerolac_ops.historical_sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE nerolac_ops.historical_sales FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rls_historical_sales_depot_isolation ON nerolac_ops.historical_sales;
CREATE POLICY rls_historical_sales_depot_isolation ON nerolac_ops.historical_sales
FOR ALL
USING (nerolac_ops.check_depot_access(depot_id))
WITH CHECK (nerolac_ops.check_depot_access(depot_id));

-- 5. Table 3: nerolac_ops.employee_kpi_scores
ALTER TABLE nerolac_ops.employee_kpi_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE nerolac_ops.employee_kpi_scores FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rls_employee_kpi_scores_depot_isolation ON nerolac_ops.employee_kpi_scores;
CREATE POLICY rls_employee_kpi_scores_depot_isolation ON nerolac_ops.employee_kpi_scores
FOR ALL
USING (nerolac_ops.check_employee_kpi_access(employee_id))
WITH CHECK (nerolac_ops.check_employee_kpi_access(employee_id));

-- 6. Table 4: nerolac_ops.whatsapp_parsed_sales
ALTER TABLE nerolac_ops.whatsapp_parsed_sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE nerolac_ops.whatsapp_parsed_sales FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rls_whatsapp_parsed_sales_depot_isolation
    ON nerolac_ops.whatsapp_parsed_sales;
CREATE POLICY rls_whatsapp_parsed_sales_depot_isolation ON nerolac_ops.whatsapp_parsed_sales
FOR ALL
USING (nerolac_ops.check_whatsapp_sales_access(dealer_id))
WITH CHECK (nerolac_ops.check_whatsapp_sales_access(dealer_id));
"""


async def setup_row_level_security(connection: Any = None) -> bool:
    """Execute Row-Level Security DDL on PostgreSQL 16 database."""
    logger.info("Enforcing PostgreSQL 16 Row-Level Security policies across operational tables...")

    if connection is not None:
        if hasattr(connection, "execute"):
            await connection.execute(RLS_SETUP_SQL)
            return True

    # Use direct asyncpg connection for multi-statement DDL execution
    import asyncpg  # type: ignore[import-untyped]

    vault = get_vault_client()
    creds = vault.get_database_credentials()

    conn = await asyncpg.connect(
        host=creds["host"],
        port=int(creds["port"]),
        user=creds["user"],
        password=creds["password"],
        database=creds["database"],
    )
    try:
        await conn.execute(RLS_SETUP_SQL)
    finally:
        await conn.close()

    logger.info("PostgreSQL Row-Level Security policies applied successfully.")
    return True


async def verify_rls_status() -> dict[str, Any]:
    """Verify RLS configuration and policy state across the 4 isolated tables."""
    tables = [
        "financial_actuals",
        "historical_sales",
        "employee_kpi_scores",
        "whatsapp_parsed_sales",
    ]
    query = text(
        """
        SELECT
            c.relname AS table_name,
            c.relrowsecurity AS rls_enabled,
            c.relforcerowsecurity AS rls_forced,
            count(p.polname) AS policy_count
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        LEFT JOIN pg_policy p ON p.polrelid = c.oid
        WHERE n.nspname = 'nerolac_ops' AND c.relname = ANY(:tables)
        GROUP BY c.relname, c.relrowsecurity, c.relforcerowsecurity;
        """
    )
    router = get_routing_manager()
    async with router.primary_engine.connect() as conn:
        result = await conn.execute(query, {"tables": tables})
        rows = result.fetchall()

    status_map = {}
    for r in rows:
        status_map[r[0]] = {
            "rls_enabled": bool(r[1]),
            "rls_forced": bool(r[2]),
            "policy_count": int(r[3]),
        }

    all_secure = len(status_map) == 4 and all(
        v["rls_enabled"] and v["rls_forced"] and v["policy_count"] > 0 for v in status_map.values()
    )

    return {
        "all_secure": all_secure,
        "tables": status_map,
    }
