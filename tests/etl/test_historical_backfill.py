"""Unit & Integration Test Suite for Historical SAP Backfill Worker.

Verifies:
1. Synthetic SAP Trial Balance generation across 12-24 months.
2. Chunked processing with 5,000-row batching.
3. Idempotent ON CONFLICT (fiscal_year, fiscal_month, depot_id, gl_code, segment_code) DO UPDATE.
4. Execution performance metrics persisted to `nerolac_ops.audit_logs`.
5. High-volume 50,000-row execution completes in < 10.0 seconds with zero duplicates.
"""

from __future__ import annotations

import csv
import uuid
from pathlib import Path

import asyncpg
import pytest

from src.backend.config.vault import get_vault_client
from src.backend.etl.historical_backfill import (
    DEFAULT_BATCH_SIZE,
    MAX_GL_CODE,
    MIN_GL_CODE,
    HistoricalSAPBackfillWorker,
    TrialBalanceRecord,
)


@pytest.fixture
async def db_conn() -> asyncpg.Connection:
    """Provide an asyncpg connection to the Nerolac test database."""
    vault = get_vault_client()
    creds = vault.get_database_credentials()
    dsn = (
        f"postgresql://{creds['user']}:{creds['password']}@"
        f"{creds['host']}:{creds['port']}/{creds['database']}"
    )
    conn = await asyncpg.connect(dsn)
    try:
        yield conn
    finally:
        await conn.close()


class TestSyntheticDataGeneration:
    """Test synthetic SAP trial balance generator."""

    def test_generate_synthetic_trial_balances(self) -> None:
        records = HistoricalSAPBackfillWorker.generate_synthetic_trial_balances(
            count=1000,
            start_year=2024,
            months_span=12,
        )
        assert len(records) == 1000

        # Check unique keys
        keys = {
            (r.fiscal_year, r.fiscal_month, r.depot_id, r.gl_code, r.segment_code) for r in records
        }
        assert len(keys) == 1000

        # Check GL ranges
        for r in records:
            gl = int(r.gl_code)
            assert MIN_GL_CODE <= gl <= MAX_GL_CODE
            assert 1 <= r.fiscal_month <= 12
            assert r.fiscal_year >= 2024
            assert r.amount > 0


@pytest.mark.asyncio
class TestHistoricalBackfillExecution:
    """Integration test suite for HistoricalSAPBackfillWorker with PostgreSQL."""

    async def test_empty_records_backfill(self) -> None:
        worker = HistoricalSAPBackfillWorker()
        result = await worker.backfill_trial_balances(records=[])
        assert result.total_rows == 0
        assert result.batches_processed == 0
        assert result.status == "COMPLETED"

    async def test_small_batch_idempotent_upsert(self, db_conn: asyncpg.Connection) -> None:
        worker = HistoricalSAPBackfillWorker(batch_size=10)
        batch_id = f"TEST_SMALL_{uuid.uuid4().hex[:8]}"

        # 15 distinct records
        records = [
            TrialBalanceRecord(
                fiscal_year=2025,
                fiscal_month=1,
                depot_id="DEPOT_01",
                gl_code=str(10000 + i),
                segment_code="DECORATIVE",
                amount=1000.0 + (i * 10),
            )
            for i in range(15)
        ]

        # Initial backfill
        res1 = await worker.backfill_trial_balances(records, batch_id=batch_id)
        assert res1.total_rows == 15
        assert res1.batches_processed == 2  # 10 + 5
        assert res1.status == "COMPLETED"
        assert res1.audit_log_id is not None

        # Verify audit log was created
        audit_row = await db_conn.fetchrow(
            "SELECT * FROM nerolac_ops.audit_logs WHERE log_id = $1;",
            res1.audit_log_id,
        )
        assert audit_row is not None
        assert audit_row["action"] == "HISTORICAL_BACKFILL"
        assert audit_row["entity_type"] == "SAP_TRIAL_BALANCES"

        # Check in DB
        cnt1 = await db_conn.fetchval(
            """
            SELECT count(*) FROM nerolac_ops.sap_trial_balances
            WHERE fiscal_year = 2025 AND fiscal_month = 1 AND depot_id = 'DEPOT_01';
            """
        )
        assert cnt1 >= 15

        # Re-run with updated amounts
        updated_records = [
            TrialBalanceRecord(
                fiscal_year=2025,
                fiscal_month=1,
                depot_id="DEPOT_01",
                gl_code=str(10000 + i),
                segment_code="DECORATIVE",
                amount=9999.00,
            )
            for i in range(15)
        ]

        res2 = await worker.backfill_trial_balances(updated_records, batch_id=f"{batch_id}_RERUN")
        assert res2.total_rows == 15

        # Verify no duplicate rows were added
        cnt2 = await db_conn.fetchval(
            """
            SELECT count(*) FROM nerolac_ops.sap_trial_balances
            WHERE fiscal_year = 2025 AND fiscal_month = 1 AND depot_id = 'DEPOT_01';
            """
        )
        assert cnt2 == cnt1  # Count strictly equal (zero duplicates)

        # Verify amount updated to 9999.00
        val = await db_conn.fetchval(
            """
            SELECT amount FROM nerolac_ops.sap_trial_balances
            WHERE fiscal_year = 2025 AND fiscal_month = 1 AND depot_id = 'DEPOT_01'
              AND gl_code = '10000' AND segment_code = 'DECORATIVE';
            """
        )
        assert float(val) == 9999.00

    async def test_csv_file_backfill(self, tmp_path: Path, db_conn: asyncpg.Connection) -> None:
        csv_file = tmp_path / "sap_tb_import.csv"
        rows = [
            {
                "fiscal_year": "2024",
                "fiscal_month": "6",
                "depot_id": "DEPOT_TEST",
                "gl_code": "10005",
                "segment_code": "AUTO",
                "amount": "250000.50",
            },
            {
                "fiscal_year": "2024",
                "fiscal_month": "7",
                "depot_id": "DEPOT_TEST",
                "gl_code": "10005",
                "segment_code": "AUTO",
                "amount": "350000.75",
            },
        ]
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        worker = HistoricalSAPBackfillWorker()
        result = await worker.backfill_trial_balances(csv_file)
        assert result.total_rows == 2
        assert result.status == "COMPLETED"

        db_val = await db_conn.fetchval(
            """
            SELECT amount FROM nerolac_ops.sap_trial_balances
            WHERE depot_id = 'DEPOT_TEST' AND fiscal_month = 6;
            """
        )
        assert float(db_val) == 250000.50

    async def test_fifty_thousand_performance_sla(self, db_conn: asyncpg.Connection) -> None:
        """Assert 50,000 synthetic rows backfill completes in < 10 seconds."""
        # Generate 50,000 synthetic rows
        records = HistoricalSAPBackfillWorker.generate_synthetic_trial_balances(
            count=50000,
            start_year=2024,
            months_span=24,
        )
        assert len(records) == 50000

        # Truncate table for isolated performance assertion
        await db_conn.execute("TRUNCATE TABLE nerolac_ops.sap_trial_balances;")

        worker = HistoricalSAPBackfillWorker(batch_size=DEFAULT_BATCH_SIZE)

        # 1. Backfill 50,000 rows
        res1 = await worker.backfill_trial_balances(records)
        assert res1.total_rows == 50000
        assert res1.batches_processed == 10  # 50,000 / 5,000 = 10
        assert res1.duration_seconds < 10.0  # Must be strictly under 10 seconds!

        db_count_1 = await db_conn.fetchval("SELECT count(*) FROM nerolac_ops.sap_trial_balances;")
        assert db_count_1 == 50000

        # 2. Re-run 50,000 rows (idempotency)
        res2 = await worker.backfill_trial_balances(records)
        assert res2.total_rows == 50000
        assert res2.duration_seconds < 10.0

        db_count_2 = await db_conn.fetchval("SELECT count(*) FROM nerolac_ops.sap_trial_balances;")
        # Assert zero duplicate rows created on re-run
        assert db_count_2 == 50000
