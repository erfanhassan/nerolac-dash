"""Nerolac Dash ETL Dead-Letter Quarantine Engine.

Enforces:
1. Pydantic v2 and Pandera data validation for SAP operational drops.
2. Graceful error handling: separates valid from malformed rows without halting.
3. Automated logging of quarantined records into table `nerolac_ops.ingestion_dead_letter`.
"""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, ValidationError
from sqlalchemy import text

from src.backend.database.session_router import get_write_session
from src.backend.etl.file_verifier import SAPReportType, identify_report_type
from src.backend.etl.schemas.financial_actuals import FinancialActualsSchema
from src.backend.etl.schemas.historical_sales import HistoricalSalesSchema
from src.backend.etl.schemas.procurement import ProcurementSchema

logger = logging.getLogger("nerolac.etl.dead_letter")

SCHEMA_MAP: dict[SAPReportType, type[BaseModel]] = {
    SAPReportType.FAGLL03: FinancialActualsSchema,
    SAPReportType.VA05: HistoricalSalesSchema,
    SAPReportType.ME2L: ProcurementSchema,
}


@dataclass
class DeadLetterEntry:
    """Represents a single malformed row quarantined during ETL ingestion."""

    batch_id: str
    report_type: str
    row_index: int
    raw_payload: dict[str, Any]
    validation_errors: list[dict[str, Any]]
    status: str = "QUARANTINED"
    quarantined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary suitable for JSON serialization or database insert."""
        data = asdict(self)
        data["quarantined_at"] = self.quarantined_at.isoformat()
        return data


@dataclass
class ValidationReport:
    """Summary of data pipeline validation results and quarantine disposition."""

    batch_id: str
    report_type: SAPReportType
    total_rows: int
    valid_rows_count: int
    quarantined_rows_count: int
    valid_records: list[dict[str, Any]]
    dead_letter_records: list[DeadLetterEntry]
    persisted_count: int = 0


def _serialize_for_json(obj: Any) -> Any:
    """Helper to ensure all dictionary elements are JSON-serializable."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_json(x) for x in obj]
    return obj


class DeadLetterHandler:
    """Dead-Letter Quarantine Engine routing malformed rows to PostgreSQL."""

    def __init__(self) -> None:
        pass

    def get_schema_for_report(self, report_type: SAPReportType | str) -> type[BaseModel]:
        """Resolve Pydantic schema model for given SAP report type."""
        if isinstance(report_type, str):
            try:
                rep_enum = SAPReportType(report_type.upper())
            except ValueError:
                rep_enum = SAPReportType.UNKNOWN
        else:
            rep_enum = report_type

        schema = SCHEMA_MAP.get(rep_enum)
        if not schema:
            raise ValueError(f"No validation schema registered for report type '{report_type}'")
        return schema

    def validate_records(
        self,
        records: list[dict[str, Any]],
        report_type: SAPReportType | str,
        batch_id: str | None = None,
    ) -> ValidationReport:
        """Validate a list of raw row dictionaries, isolating malformed entries."""
        if isinstance(report_type, str):
            try:
                rep_enum = SAPReportType(report_type.upper())
            except ValueError:
                rep_enum = SAPReportType.UNKNOWN
        else:
            rep_enum = report_type

        schema_cls = self.get_schema_for_report(rep_enum)
        time_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        rand_token = uuid.uuid4().hex[:6]
        resolved_batch_id = batch_id or f"BATCH_{rep_enum.value}_{time_slug}_{rand_token}"

        valid_records: list[dict[str, Any]] = []
        dead_letter_records: list[DeadLetterEntry] = []

        for idx, row in enumerate(records, start=1):
            clean_row = {
                k.strip(): (v.strip() if isinstance(v, str) else v)
                for k, v in row.items()
                if k is not None
            }
            try:
                validated_model = schema_cls.model_validate(clean_row)
                valid_records.append(validated_model.model_dump())
            except ValidationError as err:
                error_details = [
                    {
                        "loc": ".".join(str(p) for p in e["loc"]),
                        "msg": e["msg"],
                        "type": e["type"],
                    }
                    for e in err.errors()
                ]
                dead_letter = DeadLetterEntry(
                    batch_id=resolved_batch_id,
                    report_type=rep_enum.value,
                    row_index=idx,
                    raw_payload=_serialize_for_json(clean_row),
                    validation_errors=error_details,
                )
                dead_letter_records.append(dead_letter)
            except Exception as exc:
                dead_letter = DeadLetterEntry(
                    batch_id=resolved_batch_id,
                    report_type=rep_enum.value,
                    row_index=idx,
                    raw_payload=_serialize_for_json(clean_row),
                    validation_errors=[{"msg": str(exc), "type": "unexpected_error"}],
                )
                dead_letter_records.append(dead_letter)

        total_rows = len(records)
        valid_count = len(valid_records)
        quarantined_count = len(dead_letter_records)

        logger.info(
            "Batch %s (%s) validation complete: %d total, %d valid, %d quarantined",
            resolved_batch_id,
            rep_enum.value,
            total_rows,
            valid_count,
            quarantined_count,
        )

        return ValidationReport(
            batch_id=resolved_batch_id,
            report_type=rep_enum,
            total_rows=total_rows,
            valid_rows_count=valid_count,
            quarantined_rows_count=quarantined_count,
            valid_records=valid_records,
            dead_letter_records=dead_letter_records,
        )

    def validate_dataframe(
        self,
        df: pd.DataFrame,
        report_type: SAPReportType | str,
        batch_id: str | None = None,
    ) -> ValidationReport:
        raw_records = df.to_dict(orient="records")
        records: list[dict[str, Any]] = [{str(k): v for k, v in r.items()} for r in raw_records]
        return self.validate_records(records, report_type, batch_id=batch_id)

    def validate_csv(
        self,
        csv_path: Path | str,
        report_type: SAPReportType | str | None = None,
        batch_id: str | None = None,
    ) -> ValidationReport:
        """Parse and validate an SAP CSV file directly from disk."""
        path = Path(csv_path)
        if not path.is_file():
            raise FileNotFoundError(f"CSV file not found: '{path}'")

        if report_type is None:
            rep = identify_report_type(path)
        elif isinstance(report_type, str):
            rep = SAPReportType(report_type.upper())
        else:
            rep = report_type

        records: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(dict(row))

        return self.validate_records(records, rep, batch_id=batch_id)

    async def persist_dead_letter_entries(
        self,
        entries: list[DeadLetterEntry],
    ) -> int:
        """Write quarantined dead-letter rows to PostgreSQL `ingestion_dead_letter`."""
        if not entries:
            return 0

        # Ensure table exists idempotently
        create_sql = text(
            """
            CREATE TABLE IF NOT EXISTS nerolac_ops.ingestion_dead_letter (
                dead_letter_id BIGSERIAL PRIMARY KEY,
                batch_id VARCHAR(64) NOT NULL,
                report_type VARCHAR(32) NOT NULL,
                row_index INT NOT NULL,
                raw_payload JSONB NOT NULL,
                validation_errors JSONB NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'QUARANTINED',
                quarantined_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        insert_sql = text(
            """
            INSERT INTO nerolac_ops.ingestion_dead_letter (
                batch_id, report_type, row_index, raw_payload,
                validation_errors, status, quarantined_at
            ) VALUES (
                :batch_id, :report_type, :row_index, :raw_payload,
                :validation_errors, :status, :quarantined_at
            );
            """
        )

        persisted = 0
        async with get_write_session() as session:
            await session.execute(create_sql)
            for entry in entries:
                params = {
                    "batch_id": entry.batch_id,
                    "report_type": entry.report_type,
                    "row_index": entry.row_index,
                    "raw_payload": json.dumps(entry.raw_payload),
                    "validation_errors": json.dumps(entry.validation_errors),
                    "status": entry.status,
                    "quarantined_at": entry.quarantined_at,
                }
                await session.execute(insert_sql, params)
                persisted += 1

        logger.info(
            "Persisted %d dead-letter rows to nerolac_ops.ingestion_dead_letter.",
            persisted,
        )
        return persisted

    async def quarantine_ai_timeout(
        self,
        service_name: str,
        raw_payload: dict[str, Any],
        error_message: str = "AI API request timed out after SLA threshold",
        batch_id: str | None = None,
        persist_to_db: bool = True,
    ) -> DeadLetterEntry:
        """Route timed-out AI/LLM request to the Dead-Letter Queue (DLQ)."""
        time_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        rand_token = uuid.uuid4().hex[:6]
        resolved_batch = batch_id or f"DLQ_AI_{time_slug}_{rand_token}"
        entry = DeadLetterEntry(
            batch_id=resolved_batch,
            report_type=f"AI_{service_name.upper()}_TIMEOUT",
            row_index=1,
            raw_payload=_serialize_for_json(raw_payload),
            validation_errors=[
                {
                    "error_type": "AI_API_TIMEOUT",
                    "service": service_name,
                    "message": error_message,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
            status="TIMEOUT_QUARANTINED",
        )
        if persist_to_db:
            try:
                await self.persist_dead_letter_entries([entry])
            except Exception as exc:
                logger.error("Failed to persist DLQ entry to database: %s", exc)
        return entry

    async def process_and_quarantine(
        self,
        data_source: Path | str | list[dict[str, Any]] | pd.DataFrame,
        report_type: SAPReportType | str,
        batch_id: str | None = None,
        persist_to_db: bool = True,
    ) -> ValidationReport:
        """Validate SAP data and route malformed rows to PostgreSQL dead-letter storage."""
        if isinstance(data_source, (Path, str)):
            report = self.validate_csv(data_source, report_type, batch_id=batch_id)
        elif isinstance(data_source, pd.DataFrame):
            report = self.validate_dataframe(data_source, report_type, batch_id=batch_id)
        elif isinstance(data_source, list):
            report = self.validate_records(data_source, report_type, batch_id=batch_id)
        else:
            raise TypeError(f"Unsupported data source type: {type(data_source)}")

        if persist_to_db and report.dead_letter_records:
            persisted = await self.persist_dead_letter_entries(report.dead_letter_records)
            report.persisted_count = persisted

        return report

    def process_and_quarantine_sync(
        self,
        data_source: Path | str | list[dict[str, Any]] | pd.DataFrame,
        report_type: SAPReportType | str,
        batch_id: str | None = None,
        persist_to_db: bool = True,
    ) -> ValidationReport:
        """Synchronous wrapper for process_and_quarantine."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(
                    asyncio.run,
                    self.process_and_quarantine(
                        data_source, report_type, batch_id=batch_id, persist_to_db=persist_to_db
                    ),
                ).result()
        else:
            return asyncio.run(
                self.process_and_quarantine(
                    data_source, report_type, batch_id=batch_id, persist_to_db=persist_to_db
                )
            )
