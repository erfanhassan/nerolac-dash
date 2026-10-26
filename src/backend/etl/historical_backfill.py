"""Automated Historical SAP Backfill Worker with Idempotent Upserts.

Requirements:
1. Automated historical backfill worker executing a one-time import of 12–24 months
   of historical SAP trial balances and sales records upon SAP connection.
2. Chunked SQL processing (batch size 5,000 rows) and idempotent
   `ON CONFLICT (fiscal_year, fiscal_month, depot_id, gl_code, segment_code) DO UPDATE`
   queries preventing duplicate records during re-runs.
3. Automated logging of execution performance metrics to `nerolac_ops.audit_logs`.
"""

from __future__ import annotations

import csv
import json
import logging
import math
import time
import uuid
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg

from src.backend.config.vault import get_vault_client

logger = logging.getLogger("nerolac.etl.historical_backfill")

DEFAULT_BATCH_SIZE = 5000
MIN_GL_CODE = 10000
MAX_GL_CODE = 10017


@dataclass
class TrialBalanceRecord:
    """Represents a single SAP Trial Balance ledger item."""

    fiscal_year: int
    fiscal_month: int
    depot_id: str
    gl_code: str
    segment_code: str
    amount: float

    def to_tuple(self) -> tuple[int, int, str, str, str, float]:
        """Convert to ordered tuple for asyncpg parameterized execution."""
        return (
            self.fiscal_year,
            self.fiscal_month,
            self.depot_id,
            self.gl_code,
            self.segment_code,
            float(self.amount),
        )


@dataclass
class HistoricalSalesRecord:
    """Represents a single historical SAP sales transaction."""

    depot_id: str
    sku_id: str
    sales_date: date
    quantity_liters: float
    net_revenue: float
    dealer_id: str | None = None

    def to_tuple(self) -> tuple[str, str, date, float, float, str | None]:
        """Convert to ordered tuple for asyncpg parameterized execution."""
        return (
            self.depot_id,
            self.sku_id,
            self.sales_date,
            float(self.quantity_liters),
            float(self.net_revenue),
            self.dealer_id,
        )


@dataclass
class BackfillResult:
    """Performance and execution metrics summary for a backfill operation."""

    batch_id: str
    target_table: str
    total_rows: int
    batch_size: int
    batches_processed: int
    duration_seconds: float
    throughput_rows_per_sec: float
    status: str
    audit_log_id: int | None = None
    error_message: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Serialize metrics to dictionary for JSON audit logging."""
        data = asdict(self)
        data["started_at"] = self.started_at.isoformat()
        data["completed_at"] = self.completed_at.isoformat()
        return data


class HistoricalSAPBackfillWorker:
    """High-throughput historical SAP backfill worker with chunked idempotent upserts."""

    def __init__(
        self,
        batch_size: int = DEFAULT_BATCH_SIZE,
        dsn: str | None = None,
    ) -> None:
        self.batch_size = batch_size
        if dsn:
            self._dsn = dsn
        else:
            vault = get_vault_client()
            creds = vault.get_database_credentials()
            user = creds["user"]
            password = creds["password"]
            host = creds["host"]
            port = creds["port"]
            database = creds["database"]
            self._dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"

    async def _get_connection(self) -> asyncpg.Connection:
        """Establish direct asyncpg connection."""
        return await asyncpg.connect(self._dsn)

    async def log_metrics_to_audit_logs(
        self,
        conn: asyncpg.Connection,
        result: BackfillResult,
        user_id: str | None = None,
        ip_address: str = "127.0.0.1",
    ) -> int:
        """Persist execution performance metrics into nerolac_ops.audit_logs table."""
        action = "HISTORICAL_BACKFILL"
        entity_type = (
            "SAP_TRIAL_BALANCES" if "trial_balance" in result.target_table else "HISTORICAL_SALES"
        )
        entity_id = result.batch_id

        changes_payload = json.dumps(result.to_dict())

        sql = """
            INSERT INTO nerolac_ops.audit_logs (
                user_id, action, entity_type, entity_id, changes, ip_address, created_at
            ) VALUES ($1, $2, $3, $4, $5::jsonb, $6, CURRENT_TIMESTAMP)
            RETURNING log_id;
        """
        log_id: int = await conn.fetchval(
            sql,
            user_id,
            action,
            entity_type,
            entity_id,
            changes_payload,
            ip_address,
        )
        logger.info(
            "Logged historical backfill metrics to audit_logs [log_id=%d, batch_id=%s, rows=%d]",
            log_id,
            result.batch_id,
            result.total_rows,
        )
        return log_id

    async def backfill_trial_balances(
        self,
        records: (Sequence[dict[str, Any] | TrialBalanceRecord | tuple[Any, ...]] | Path | str),
        batch_id: str | None = None,
        user_id: str | None = None,
        ip_address: str = "127.0.0.1",
    ) -> BackfillResult:
        """Execute chunked idempotent backfill of SAP trial balances.

        Uses:
        `ON CONFLICT (fiscal_year, fiscal_month, depot_id, gl_code, segment_code)
         DO UPDATE SET amount = EXCLUDED.amount, updated_at = CURRENT_TIMESTAMP`
        """
        run_id = batch_id or f"TB_BACKFILL_{uuid.uuid4().hex[:12].upper()}"
        started_at = datetime.now(timezone.utc)

        # 1. Parse / normalize records into uniform list of tuples
        raw_tuples: list[tuple[int, int, str, str, str, float]] = []

        if isinstance(records, (Path, str)):
            csv_path = Path(records)
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    raw_tuples.append(
                        (
                            int(row["fiscal_year"]),
                            int(row["fiscal_month"]),
                            str(row["depot_id"]).strip(),
                            str(row["gl_code"]).strip(),
                            str(row["segment_code"]).strip().upper(),
                            float(row["amount"]),
                        )
                    )
        else:
            for item in records:
                if isinstance(item, TrialBalanceRecord):
                    raw_tuples.append(item.to_tuple())
                elif isinstance(item, dict):
                    raw_tuples.append(
                        (
                            int(item["fiscal_year"]),
                            int(item["fiscal_month"]),
                            str(item["depot_id"]).strip(),
                            str(item["gl_code"]).strip(),
                            str(item["segment_code"]).strip().upper(),
                            float(item["amount"]),
                        )
                    )
                elif isinstance(item, (tuple, list)):
                    raw_tuples.append(
                        (
                            int(item[0]),
                            int(item[1]),
                            str(item[2]).strip(),
                            str(item[3]).strip(),
                            str(item[4]).strip().upper(),
                            float(item[5]),
                        )
                    )

        total_rows = len(raw_tuples)
        if total_rows == 0:
            logger.warning("Empty records supplied for trial balance backfill.")
            return BackfillResult(
                batch_id=run_id,
                target_table="nerolac_ops.sap_trial_balances",
                total_rows=0,
                batch_size=self.batch_size,
                batches_processed=0,
                duration_seconds=0.0,
                throughput_rows_per_sec=0.0,
                status="COMPLETED",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )

        upsert_sql = """
            INSERT INTO nerolac_ops.sap_trial_balances (
                fiscal_year,
                fiscal_month,
                depot_id,
                gl_code,
                segment_code,
                amount
            ) VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (fiscal_year, fiscal_month, depot_id, gl_code, segment_code)
            DO UPDATE SET
                amount = EXCLUDED.amount,
                updated_at = CURRENT_TIMESTAMP;
        """

        conn = await self._get_connection()
        batches_processed = 0
        t0 = time.perf_counter()

        try:
            total_batches = math.ceil(total_rows / self.batch_size)
            logger.info(
                "Starting trial balance backfill [batch_id=%s, rows=%d, batches=%d, chunk_size=%d]",
                run_id,
                total_rows,
                total_batches,
                self.batch_size,
            )

            for i in range(0, total_rows, self.batch_size):
                chunk = raw_tuples[i : i + self.batch_size]
                async with conn.transaction():
                    await conn.executemany(upsert_sql, chunk)
                batches_processed += 1

            duration = time.perf_counter() - t0
            throughput = round(total_rows / duration, 2) if duration > 0 else float(total_rows)

            result = BackfillResult(
                batch_id=run_id,
                target_table="nerolac_ops.sap_trial_balances",
                total_rows=total_rows,
                batch_size=self.batch_size,
                batches_processed=batches_processed,
                duration_seconds=round(duration, 4),
                throughput_rows_per_sec=throughput,
                status="COMPLETED",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )

            # Persist performance metrics to audit_logs
            audit_id = await self.log_metrics_to_audit_logs(
                conn=conn,
                result=result,
                user_id=user_id,
                ip_address=ip_address,
            )
            result.audit_log_id = audit_id

            logger.info(
                "Completed trial balance backfill [batch_id=%s, rows=%d, "
                "time=%.3fs, throughput=%.1f rows/s]",
                run_id,
                total_rows,
                duration,
                throughput,
            )
            return result

        except Exception as exc:
            duration = time.perf_counter() - t0
            throughput = (
                round(batches_processed * self.batch_size / duration, 2) if duration > 0 else 0.0
            )
            err_result = BackfillResult(
                batch_id=run_id,
                target_table="nerolac_ops.sap_trial_balances",
                total_rows=total_rows,
                batch_size=self.batch_size,
                batches_processed=batches_processed,
                duration_seconds=round(duration, 4),
                throughput_rows_per_sec=throughput,
                status="FAILED",
                error_message=str(exc),
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
            try:
                audit_id = await self.log_metrics_to_audit_logs(
                    conn=conn,
                    result=err_result,
                    user_id=user_id,
                    ip_address=ip_address,
                )
                err_result.audit_log_id = audit_id
            except Exception:
                logger.exception("Failed to write failure record to audit_logs.")
            raise exc

        finally:
            await conn.close()

    async def backfill_historical_sales(
        self,
        records: (Sequence[dict[str, Any] | HistoricalSalesRecord | tuple[Any, ...]] | Path | str),
        batch_id: str | None = None,
        user_id: str | None = None,
        ip_address: str = "127.0.0.1",
    ) -> BackfillResult:
        """Execute chunked idempotent backfill of historical SAP sales records.

        Uses:
        `ON CONFLICT (depot_id, sku_id, sales_date)
         DO UPDATE SET quantity_liters = EXCLUDED.quantity_liters,
                       net_revenue = EXCLUDED.net_revenue`
        """
        run_id = batch_id or f"SALES_BACKFILL_{uuid.uuid4().hex[:12].upper()}"
        started_at = datetime.now(timezone.utc)

        raw_tuples: list[tuple[str, str, date, float, float, str | None]] = []

        if isinstance(records, (Path, str)):
            csv_path = Path(records)
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    s_date = (
                        datetime.strptime(row["sales_date"], "%Y-%m-%d").date()
                        if isinstance(row["sales_date"], str)
                        else row["sales_date"]
                    )
                    raw_tuples.append(
                        (
                            str(row["depot_id"]).strip(),
                            str(row["sku_id"]).strip(),
                            s_date,
                            float(row["quantity_liters"]),
                            float(row["net_revenue"]),
                            row.get("dealer_id"),
                        )
                    )
        else:
            for item in records:
                if isinstance(item, HistoricalSalesRecord):
                    raw_tuples.append(item.to_tuple())
                elif isinstance(item, dict):
                    raw_d = item["sales_date"]
                    s_date = (
                        datetime.strptime(raw_d, "%Y-%m-%d").date()
                        if isinstance(raw_d, str)
                        else raw_d
                    )
                    raw_tuples.append(
                        (
                            str(item["depot_id"]).strip(),
                            str(item["sku_id"]).strip(),
                            s_date,
                            float(item["quantity_liters"]),
                            float(item["net_revenue"]),
                            item.get("dealer_id"),
                        )
                    )
                elif isinstance(item, (tuple, list)):
                    raw_d = item[2]
                    s_date = (
                        datetime.strptime(raw_d, "%Y-%m-%d").date()
                        if isinstance(raw_d, str)
                        else raw_d
                    )
                    dealer_id = item[5] if len(item) > 5 else None
                    raw_tuples.append(
                        (
                            str(item[0]).strip(),
                            str(item[1]).strip(),
                            s_date,
                            float(item[3]),
                            float(item[4]),
                            dealer_id,
                        )
                    )

        total_rows = len(raw_tuples)
        if total_rows == 0:
            return BackfillResult(
                batch_id=run_id,
                target_table="nerolac_ops.historical_sales",
                total_rows=0,
                batch_size=self.batch_size,
                batches_processed=0,
                duration_seconds=0.0,
                throughput_rows_per_sec=0.0,
                status="COMPLETED",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )

        upsert_sql = """
            INSERT INTO nerolac_ops.historical_sales (
                depot_id,
                sku_id,
                sales_date,
                quantity_liters,
                net_revenue,
                dealer_id
            ) VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (depot_id, sku_id, sales_date)
            DO UPDATE SET
                quantity_liters = EXCLUDED.quantity_liters,
                net_revenue = EXCLUDED.net_revenue;
        """

        conn = await self._get_connection()
        batches_processed = 0
        t0 = time.perf_counter()

        try:
            for i in range(0, total_rows, self.batch_size):
                chunk = raw_tuples[i : i + self.batch_size]
                async with conn.transaction():
                    await conn.executemany(upsert_sql, chunk)
                batches_processed += 1

            duration = time.perf_counter() - t0
            throughput = round(total_rows / duration, 2) if duration > 0 else float(total_rows)

            result = BackfillResult(
                batch_id=run_id,
                target_table="nerolac_ops.historical_sales",
                total_rows=total_rows,
                batch_size=self.batch_size,
                batches_processed=batches_processed,
                duration_seconds=round(duration, 4),
                throughput_rows_per_sec=throughput,
                status="COMPLETED",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )

            audit_id = await self.log_metrics_to_audit_logs(
                conn=conn,
                result=result,
                user_id=user_id,
                ip_address=ip_address,
            )
            result.audit_log_id = audit_id
            return result

        finally:
            await conn.close()

    @staticmethod
    def generate_synthetic_trial_balances(
        count: int = 50000,
        start_year: int = 2024,
        months_span: int = 24,
    ) -> list[TrialBalanceRecord]:
        """Generate high-cardinality synthetic SAP trial balances across 12-24 historical months.

        Each row is uniquely keyed by (fiscal_year, fiscal_month, depot_id, gl_code, segment_code).
        GL codes strictly adhere to authorized 10000-10017 range.
        """
        depots = [f"DEPOT_{d:02d}" for d in range(1, 11)]  # 10 depots
        segments = [
            "DECORATIVE",
            "INDUSTRIAL",
            "AUTOMOTIVE",
            "POWDER",
            "COATINGS",
            "PROTECTIVE",
            "WOOD_FINISH",
            "REFINISH",
            "CONSTRUCTION",
            "SPECIALTY",
            "MARINE",
            "AEROSPACE",
        ]  # 12 segments
        gl_codes = [str(g) for g in range(MIN_GL_CODE, MAX_GL_CODE + 1)]  # 18 GLs

        # Generate months across span (e.g. 24 months = 2 years)
        periods: list[tuple[int, int]] = []
        for m_idx in range(months_span):
            yr = start_year + (m_idx // 12)
            mo = (m_idx % 12) + 1
            periods.append((yr, mo))

        records: list[TrialBalanceRecord] = []
        rec_idx = 0

        # Total combinations: 24 * 10 * 18 * 12 = 51,840 distinct keys
        for yr, mo in periods:
            for depot in depots:
                for gl in gl_codes:
                    for seg in segments:
                        if rec_idx >= count:
                            return records
                        amt = round(150000.00 + (rec_idx * 13.37) % 750000.0, 2)
                        records.append(
                            TrialBalanceRecord(
                                fiscal_year=yr,
                                fiscal_month=mo,
                                depot_id=depot,
                                gl_code=gl,
                                segment_code=seg,
                                amount=amt,
                            )
                        )
                        rec_idx += 1

        return records
