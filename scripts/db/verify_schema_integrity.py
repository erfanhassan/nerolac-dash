#!/usr/bin/env python3
"""PostgreSQL 16 Schema Integrity Verification Harness.

Validates:
1. Schema existence: `nerolac_ops`
2. Enums (4): user_role_enum, message_status_enum, forecast_type_enum, ar_ap_type_enum
3. Master Tables (8): depots, users, audit_logs, chart_of_accounts, territories,
   employees, skus, dealers
4. Transactional Tables (11): financial_actuals, financial_budgets, procurement_register,
   ar_ap_aging, employee_kpi_scores, manpower_capacity_models, historical_sales,
   demand_forecasts, whatsapp_raw_messages, whatsapp_parsed_sales,
   daily_sales_reconciliations
5. Composite Indexes (6):
   - idx_fin_act_depot_time on financial_actuals
   - idx_proc_mat_date on procurement_register
   - idx_emp_kpi_lookup on employee_kpi_scores
   - idx_sales_depot_sku_date on historical_sales
   - idx_forecast_lookup on demand_forecasts
   - idx_wa_status_received on whatsapp_raw_messages
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

# Ensure project root and virtualenv packages are accessible
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
venv_site_packages = REPO_ROOT / ".venv" / "lib" / py_ver / "site-packages"
if venv_site_packages.is_dir() and str(venv_site_packages) not in sys.path:
    sys.path.insert(0, str(venv_site_packages))

try:
    import asyncpg  # type: ignore[import-untyped]
except ImportError:
    # If invoked directly via system python3 without active venv, re-exec via venv python
    venv_py = REPO_ROOT / ".venv" / "bin" / "python3"
    if venv_py.is_file() and sys.executable != str(venv_py):
        os.execv(str(venv_py), [str(venv_py), *sys.argv])
    raise

from src.backend.config.vault import get_vault_client  # noqa: E402

SCHEMA = "nerolac_ops"

EXPECTED_ENUMS: dict[str, list[str]] = {
    "user_role_enum": [
        "SUPER_ADMIN",
        "FINANCE_MANAGER",
        "SUPPLY_CHAIN_PLANNER",
        "SALES_DIRECTOR",
        "DEPOT_MANAGER",
        "FIELD_OFFICER",
        "AUDITOR",
    ],
    "message_status_enum": [
        "RECEIVED",
        "PROCESSING",
        "PARSED",
        "RECONCILED",
        "FAILED",
        "FLAGGED",
    ],
    "forecast_type_enum": [
        "STATISTICAL",
        "ML_ENSEMBLE",
        "EXECUTIVE_OVERRIDE",
        "FINAL_CONSENSUS",
    ],
    "ar_ap_type_enum": [
        "RECEIVABLE",
        "PAYABLE",
    ],
}

EXPECTED_MASTER_TABLES: list[str] = [
    "depots",
    "users",
    "audit_logs",
    "chart_of_accounts",
    "territories",
    "employees",
    "skus",
    "dealers",
]

EXPECTED_TRANSACTIONAL_TABLES: list[str] = [
    "financial_actuals",
    "financial_budgets",
    "procurement_register",
    "ar_ap_aging",
    "employee_kpi_scores",
    "manpower_capacity_models",
    "historical_sales",
    "demand_forecasts",
    "whatsapp_raw_messages",
    "whatsapp_parsed_sales",
    "daily_sales_reconciliations",
]

EXPECTED_COMPOSITE_INDEXES: dict[str, str] = {
    "idx_fin_act_depot_time": "financial_actuals",
    "idx_proc_mat_date": "procurement_register",
    "idx_emp_kpi_lookup": "employee_kpi_scores",
    "idx_sales_depot_sku_date": "historical_sales",
    "idx_forecast_lookup": "demand_forecasts",
    "idx_wa_status_received": "whatsapp_raw_messages",
}


async def verify_schema() -> bool:
    print("=" * 70)
    print("  POSTGRESQL 16 - NEROLAC OPS SCHEMA INTEGRITY VERIFICATION")
    print("=" * 70)

    vault = get_vault_client()
    creds = vault.get_database_credentials()

    print(
        f"Connecting to PostgreSQL 16 at {creds['host']}:{creds['port']}/{creds['database']}..."
    )
    conn: asyncpg.Connection = await asyncpg.connect(
        host=creds["host"],
        port=int(creds["port"]),
        user=creds["user"],
        password=creds["password"],
        database=creds["database"],
    )

    all_passed = True

    try:
        # 1. Verify Schema
        print(f"\n[1/4] Checking Schema '{SCHEMA}'...")
        schema_exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = $1);",
            SCHEMA,
        )
        if schema_exists:
            print(f"  ✅ Schema '{SCHEMA}' exists.")
        else:
            print(f"  ❌ Schema '{SCHEMA}' NOT found!")
            all_passed = False

        # 2. Verify Enums
        print("\n[2/4] Checking Enum Types (4 Enums)...")
        enum_records = await conn.fetch(
            """
            SELECT t.typname, array_agg(e.enumlabel ORDER BY e.enumsortorder) AS labels
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            JOIN pg_namespace n ON n.oid = t.typnamespace
            WHERE n.nspname = $1
            GROUP BY t.typname;
            """,
            SCHEMA,
        )
        found_enums = {r["typname"]: list(r["labels"]) for r in enum_records}

        for enum_name, expected_labels in EXPECTED_ENUMS.items():
            if enum_name not in found_enums:
                print(f"  ❌ Missing enum: '{enum_name}'")
                all_passed = False
            else:
                actual_labels = found_enums[enum_name]
                if set(expected_labels) == set(actual_labels):
                    print(f"  ✅ Enum '{enum_name}': {len(actual_labels)} labels verified.")
                else:
                    print(
                        f"  ❌ Enum '{enum_name}' labels mismatch! Expected {expected_labels}, "
                        f"got {actual_labels}"
                    )
                    all_passed = False

        # 3. Verify Tables (Master + Transactional)
        print("\n[3/4] Checking Tables (8 Master + 11 Transactional = 19 Tables)...")
        table_records = await conn.fetch(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname = $1;
            """,
            SCHEMA,
        )
        found_tables = {r["tablename"] for r in table_records}

        print("  --> Master Tables:")
        for tbl in EXPECTED_MASTER_TABLES:
            if tbl in found_tables:
                print(f"    ✅ Master table '{tbl}' found.")
            else:
                print(f"    ❌ Missing master table: '{tbl}'")
                all_passed = False

        print("  --> Transactional Tables:")
        for tbl in EXPECTED_TRANSACTIONAL_TABLES:
            if tbl in found_tables:
                print(f"    ✅ Transactional table '{tbl}' found.")
            else:
                print(f"    ❌ Missing transactional table: '{tbl}'")
                all_passed = False

        # 4. Verify Composite Indexes
        print("\n[4/4] Checking Composite Indexes (6 Composite Indexes)...")
        index_records = await conn.fetch(
            """
            SELECT indexname, tablename, indexdef
            FROM pg_indexes
            WHERE schemaname = $1 AND indexname LIKE 'idx_%';
            """,
            SCHEMA,
        )
        found_indexes: dict[str, dict[str, Any]] = {
            r["indexname"]: {"table": r["tablename"], "def": r["indexdef"]} for r in index_records
        }

        for idx_name, expected_tbl in EXPECTED_COMPOSITE_INDEXES.items():
            if idx_name in found_indexes:
                info = found_indexes[idx_name]
                if info["table"] == expected_tbl:
                    print(f"  ✅ Index '{idx_name}' verified on table '{expected_tbl}'.")
                else:
                    msg = (
                        f"  ❌ Index '{idx_name}' is on '{info['table']}', "
                        f"expected '{expected_tbl}'"
                    )
                    print(msg)
                    all_passed = False
            else:
                print(f"  ❌ Missing composite index: '{idx_name}'")
                all_passed = False

    finally:
        await conn.close()

    print("-" * 70)
    if all_passed:
        print("SUCCESS: 100% Schema Integrity Verified against PostgreSQL 16 DDL! ✨")
        print("  - Schema: nerolac_ops")
        print(f"  - Enums Verified: {len(EXPECTED_ENUMS)}")
        print(f"  - Master Tables Verified: {len(EXPECTED_MASTER_TABLES)}")
        print(f"  - Transactional Tables Verified: {len(EXPECTED_TRANSACTIONAL_TABLES)}")
        print(f"  - Composite Indexes Verified: {len(EXPECTED_COMPOSITE_INDEXES)}")
        print("=" * 70)
        return True
    else:
        print("FAILURE: Schema verification detected discrepancies with DDL!")
        print("=" * 70)
        return False


def main() -> None:
    success = asyncio.run(verify_schema())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
