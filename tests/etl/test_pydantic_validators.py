"""Unit and Integration Tests for Pydantic v2 and Pandera Data Validation Pipelines.

Verifies:
1. FinancialActualsSchema validates GL codes 10000–10017, fiscal year/month, segment, BDT.
2. HistoricalSalesSchema validates sales date, depot ID, SKU code, liters, net revenue BDT.
3. ProcurementSchema validates PO date, vendor ID/name, material code, unit price BDT, quantity.
4. Pandera DataFrame validation engines for batch tabular ingestion.
5. Dead-Letter Quarantine engine routes malformed rows to `ingestion_dead_letter` table.
6. Valid rows pass 100% while malformed rows are isolated with detailed error diagnostics.
"""

from __future__ import annotations

import json
import uuid
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError
from sqlalchemy import text

from src.backend.database.session_router import get_read_session
from src.backend.etl.dead_letter_handler import DeadLetterHandler
from src.backend.etl.file_verifier import SAPReportType
from src.backend.etl.schemas.financial_actuals import (
    FinancialActualsSchema,
    financial_actuals_pandera_schema,
)
from src.backend.etl.schemas.historical_sales import (
    HistoricalSalesSchema,
    historical_sales_pandera_schema,
)
from src.backend.etl.schemas.procurement import (
    ProcurementSchema,
    procurement_pandera_schema,
)


class TestFinancialActualsValidation:
    """Test suite for SAP FAGLL03 Financial Actuals Pydantic & Pandera validation."""

    def test_valid_financial_actuals_record(self) -> None:
        data = {
            "gl_code": 10005,
            "fiscal_year": 2026,
            "fiscal_month": 3,
            "segment_code": "DECORATIVE",
            "amount": 250000.75,
            "depot_id": "DEPOT_01",
            "transaction_date": "2026-03-15",
        }
        validated = FinancialActualsSchema.model_validate(data)
        assert validated.gl_code == 10005
        assert validated.fiscal_year == 2026
        assert validated.fiscal_month == 3
        assert validated.segment_code == "DECORATIVE"
        assert validated.amount == 250000.75
        assert validated.transaction_date == date(2026, 3, 15)

    def test_gl_code_boundary_limits(self) -> None:
        # 10000 (min boundary) - must pass
        min_record = FinancialActualsSchema.model_validate(
            {
                "gl_code": "10000",
                "fiscal_year": 2026,
                "fiscal_month": 1,
                "segment_code": "INDUSTRIAL",
                "amount": 1000.0,
            }
        )
        assert min_record.gl_code == 10000

        # 10017 (max boundary) - must pass
        max_record = FinancialActualsSchema.model_validate(
            {
                "gl_code": 10017,
                "fiscal_year": 2026,
                "fiscal_month": 12,
                "segment_code": "AUTO",
                "amount": 5000.0,
            }
        )
        assert max_record.gl_code == 10017

        # 9999 (below min boundary) - must fail
        with pytest.raises(ValidationError) as exc_info:
            FinancialActualsSchema.model_validate(
                {
                    "gl_code": 9999,
                    "fiscal_year": 2026,
                    "fiscal_month": 1,
                    "segment_code": "COATINGS",
                    "amount": 100.0,
                }
            )
        assert "outside authorized SAP Chart of Accounts range" in str(exc_info.value)

        # 10018 (above max boundary) - must fail
        with pytest.raises(ValidationError) as exc_info:
            FinancialActualsSchema.model_validate(
                {
                    "gl_code": 10018,
                    "fiscal_year": 2026,
                    "fiscal_month": 1,
                    "segment_code": "COATINGS",
                    "amount": 100.0,
                }
            )
        assert "outside authorized SAP Chart of Accounts range" in str(exc_info.value)

    def test_fiscal_month_validation(self) -> None:
        # Month 13 is invalid
        with pytest.raises(ValidationError) as exc_info:
            FinancialActualsSchema.model_validate(
                {
                    "gl_code": 10001,
                    "fiscal_year": 2026,
                    "fiscal_month": 13,
                    "segment_code": "DECORATIVE",
                    "amount": 100.0,
                }
            )
        assert "Must be between 1 and 12" in str(exc_info.value)

        # Month 0 is invalid
        with pytest.raises(ValidationError):
            FinancialActualsSchema.model_validate(
                {
                    "gl_code": 10001,
                    "fiscal_year": 2026,
                    "fiscal_month": 0,
                    "segment_code": "DECORATIVE",
                    "amount": 100.0,
                }
            )

    def test_segment_code_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            FinancialActualsSchema.model_validate(
                {
                    "gl_code": 10002,
                    "fiscal_year": 2026,
                    "fiscal_month": 5,
                    "segment_code": "   ",
                    "amount": 500.0,
                }
            )
        assert "Segment code cannot be empty" in str(exc_info.value)

    def test_pandera_financial_actuals_dataframe(self) -> None:
        valid_df = pd.DataFrame(
            [
                {
                    "gl_code": 10000,
                    "fiscal_year": 2026,
                    "fiscal_month": 1,
                    "segment_code": "DEC",
                    "amount": 1000.0,
                },
                {
                    "gl_code": 10017,
                    "fiscal_year": 2026,
                    "fiscal_month": 12,
                    "segment_code": "IND",
                    "amount": 2500.0,
                },
            ]
        )
        validated_df = financial_actuals_pandera_schema.validate(valid_df)
        assert len(validated_df) == 2


class TestHistoricalSalesValidation:
    """Test suite for SAP VA05 Historical Sales Pydantic & Pandera validation."""

    def test_valid_historical_sales_record(self) -> None:
        data = {
            "sales_date": "2026-03-20",
            "depot_id": "DEPOT_DHAKA_01",
            "sku_code": "SKU_GLOSS_ENAMEL_1L",
            "liters": 150.5,
            "net_revenue": 45000.0,
        }
        validated = HistoricalSalesSchema.model_validate(data)
        assert validated.sales_date == date(2026, 3, 20)
        assert validated.depot_id == "DEPOT_DHAKA_01"
        assert validated.sku_code == "SKU_GLOSS_ENAMEL_1L"
        assert validated.liters == 150.5
        assert validated.net_revenue == 45000.0

    def test_negative_liters_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            HistoricalSalesSchema.model_validate(
                {
                    "sales_date": "2026-03-20",
                    "depot_id": "DEPOT_01",
                    "sku_code": "SKU_01",
                    "liters": -10.0,
                    "net_revenue": 500.0,
                }
            )
        assert "Liters cannot be negative" in str(exc_info.value)

    def test_negative_net_revenue_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            HistoricalSalesSchema.model_validate(
                {
                    "sales_date": "2026-03-20",
                    "depot_id": "DEPOT_01",
                    "sku_code": "SKU_01",
                    "liters": 10.0,
                    "net_revenue": -150.0,
                }
            )
        assert "Net revenue in BDT cannot be negative" in str(exc_info.value)

    def test_empty_depot_or_sku_rejected(self) -> None:
        with pytest.raises(ValidationError):
            HistoricalSalesSchema.model_validate(
                {
                    "sales_date": "2026-03-20",
                    "depot_id": "",
                    "sku_code": "SKU_01",
                    "liters": 10.0,
                    "net_revenue": 100.0,
                }
            )

        with pytest.raises(ValidationError):
            HistoricalSalesSchema.model_validate(
                {
                    "sales_date": "2026-03-20",
                    "depot_id": "DEPOT_01",
                    "sku_code": "   ",
                    "liters": 10.0,
                    "net_revenue": 100.0,
                }
            )

    def test_pandera_historical_sales_dataframe(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "depot_id": "DEPOT_01",
                    "sku_code": "SKU_A",
                    "liters": 100.0,
                    "net_revenue": 20000.0,
                },
                {"depot_id": "DEPOT_02", "sku_code": "SKU_B", "liters": 0.0, "net_revenue": 0.0},
            ]
        )
        validated_df = historical_sales_pandera_schema.validate(df)
        assert len(validated_df) == 2


class TestProcurementValidation:
    """Test suite for SAP ME2L Procurement Register Pydantic & Pandera validation."""

    def test_valid_procurement_record(self) -> None:
        data = {
            "po_date": "2026-03-10",
            "vendor_name": "BANGLADESH_CHEMICALS_LTD",
            "material_code": "MAT_TITANIUM_DIOXIDE",
            "unit_price": 420.50,
            "quantity": 1000.0,
            "depot_id": "DEPOT_01",
        }
        validated = ProcurementSchema.model_validate(data)
        assert validated.po_date == date(2026, 3, 10)
        assert validated.vendor_name == "BANGLADESH_CHEMICALS_LTD"
        assert validated.material_code == "MAT_TITANIUM_DIOXIDE"
        assert validated.unit_price == 420.50
        assert validated.quantity == 1000.0

    def test_non_positive_unit_price_rejected(self) -> None:
        # Zero unit price
        with pytest.raises(ValidationError) as exc_info:
            ProcurementSchema.model_validate(
                {
                    "po_date": "2026-03-10",
                    "vendor_name": "SUPPLIER_01",
                    "material_code": "MAT_01",
                    "unit_price": 0.0,
                    "quantity": 100.0,
                }
            )
        assert "must be strictly positive" in str(exc_info.value)

        # Negative unit price
        with pytest.raises(ValidationError):
            ProcurementSchema.model_validate(
                {
                    "po_date": "2026-03-10",
                    "vendor_name": "SUPPLIER_01",
                    "material_code": "MAT_01",
                    "unit_price": -50.0,
                    "quantity": 100.0,
                }
            )

    def test_non_positive_quantity_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ProcurementSchema.model_validate(
                {
                    "po_date": "2026-03-10",
                    "vendor_name": "SUPPLIER_01",
                    "material_code": "MAT_01",
                    "unit_price": 10.0,
                    "quantity": 0.0,
                }
            )
        assert "must be strictly positive" in str(exc_info.value)

    def test_pandera_procurement_dataframe(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "vendor_name": "VEND_1",
                    "material_code": "MAT_1",
                    "unit_price": 50.0,
                    "quantity": 10.0,
                },
                {
                    "vendor_name": "VEND_2",
                    "material_code": "MAT_2",
                    "unit_price": 100.0,
                    "quantity": 5.0,
                },
            ]
        )
        validated_df = procurement_pandera_schema.validate(df)
        assert len(validated_df) == 2


class TestDeadLetterQuarantineEngine:
    """Integration test suite ensuring dead-letter handler routes malformed rows to PostgreSQL."""

    def test_100_percent_valid_sap_csv_passes_without_quarantine(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "FAGLL03_VALID.csv"
        headers = "gl_code,fiscal_year,fiscal_month,segment_code,amount,depot_id,transaction_date"
        csv_content = f"""{headers}
10000,2026,1,DECORATIVE,150000.00,DEPOT_01,2026-01-15
10005,2026,1,INDUSTRIAL,220000.50,DEPOT_01,2026-01-20
10012,2026,2,AUTO,85000.00,DEPOT_02,2026-02-10
10017,2026,2,POWDER,94000.00,DEPOT_02,2026-02-18
"""
        csv_file.write_text(csv_content, encoding="utf-8")

        handler = DeadLetterHandler()
        report = handler.validate_csv(csv_file, report_type=SAPReportType.FAGLL03)

        assert report.total_rows == 4
        assert report.valid_rows_count == 4
        assert report.quarantined_rows_count == 0
        assert len(report.dead_letter_records) == 0
        assert len(report.valid_records) == 4

    @pytest.mark.asyncio
    async def test_mixed_csv_isolates_malformed_rows_to_dead_letter_table(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify pipeline does not halt on malformed rows and logs them to dead-letter table."""
        csv_file = tmp_path / "FAGLL03_MIXED_BATCH.csv"
        # 5 rows: Row 1 valid, Row 2 invalid GL (99999), Row 3 valid,
        # Row 4 invalid fiscal month (14), Row 5 invalid GL (9990)
        headers = "gl_code,fiscal_year,fiscal_month,segment_code,amount,depot_id,transaction_date"
        csv_content = f"""{headers}
10001,2026,3,DECORATIVE,50000.00,DEPOT_01,2026-03-01
99999,2026,3,DECORATIVE,75000.00,DEPOT_01,2026-03-02
10015,2026,3,INDUSTRIAL,120000.00,DEPOT_02,2026-03-05
10002,2026,14,AUTO,40000.00,DEPOT_01,2026-03-10
9990,2026,3,COATINGS,60000.00,DEPOT_01,2026-03-12
"""
        csv_file.write_text(csv_content, encoding="utf-8")

        handler = DeadLetterHandler()
        test_batch_id = f"TEST_BATCH_FAGLL03_{uuid.uuid4().hex[:8]}_MIXED"

        # Execute processing and database quarantine
        report = await handler.process_and_quarantine(
            csv_file,
            report_type=SAPReportType.FAGLL03,
            batch_id=test_batch_id,
            persist_to_db=True,
        )

        # 1. Pipeline did NOT halt or crash
        assert report.total_rows == 5
        assert report.valid_rows_count == 2
        assert report.quarantined_rows_count == 3
        assert report.persisted_count == 3

        # 2. Check quarantined indices
        quarantined_indices = [dl.row_index for dl in report.dead_letter_records]
        assert quarantined_indices == [2, 4, 5]

        # 3. Direct PostgreSQL Verification: assert rows written to ingestion_dead_letter
        async with get_read_session() as session:
            result = await session.execute(
                text(
                    """
                    SELECT dead_letter_id, batch_id, report_type, row_index,
                           raw_payload, validation_errors, status
                    FROM nerolac_ops.ingestion_dead_letter
                    WHERE batch_id = :batch_id
                    ORDER BY row_index ASC;
                    """
                ),
                {"batch_id": test_batch_id},
            )
            db_rows = result.fetchall()

        assert len(db_rows) == 3

        # Row index 2 (GL code 99999)
        r2 = db_rows[0]
        assert r2.row_index == 2
        assert r2.report_type == "FAGLL03"
        payload_2 = (
            r2.raw_payload if isinstance(r2.raw_payload, dict) else json.loads(r2.raw_payload)
        )
        assert payload_2["gl_code"] == "99999"
        errors_2 = (
            r2.validation_errors
            if isinstance(r2.validation_errors, list)
            else json.loads(r2.validation_errors)
        )
        assert any("outside authorized SAP Chart of Accounts range" in e["msg"] for e in errors_2)

        # Row index 4 (Month 14)
        r4 = db_rows[1]
        assert r4.row_index == 4
        payload_4 = (
            r4.raw_payload if isinstance(r4.raw_payload, dict) else json.loads(r4.raw_payload)
        )
        assert payload_4["fiscal_month"] == "14"
        errors_4 = (
            r4.validation_errors
            if isinstance(r4.validation_errors, list)
            else json.loads(r4.validation_errors)
        )
        assert any("Must be between 1 and 12" in e["msg"] for e in errors_4)

        # Row index 5 (GL code 9990)
        r5 = db_rows[2]
        assert r5.row_index == 5
        payload_5 = (
            r5.raw_payload if isinstance(r5.raw_payload, dict) else json.loads(r5.raw_payload)
        )
        assert payload_5["gl_code"] == "9990"

    @pytest.mark.asyncio
    async def test_historical_sales_quarantines_malformed_records(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "VA05_MALFORMED.csv"
        csv_content = """sales_date,depot_id,sku_code,liters,net_revenue
2026-03-01,DEPOT_01,SKU_RED,100.0,25000.00
2026-03-02,,SKU_BLUE,50.0,12000.00
2026-03-03,DEPOT_01,SKU_GREEN,-5.0,8000.00
"""
        csv_file.write_text(csv_content, encoding="utf-8")

        handler = DeadLetterHandler()
        batch_id = f"TEST_VA05_SALES_{uuid.uuid4().hex[:8]}"
        report = await handler.process_and_quarantine(
            csv_file,
            report_type=SAPReportType.VA05,
            batch_id=batch_id,
            persist_to_db=True,
        )

        assert report.total_rows == 3
        assert report.valid_rows_count == 1
        assert report.quarantined_rows_count == 2
        assert report.persisted_count == 2

    @pytest.mark.asyncio
    async def test_procurement_quarantines_malformed_records(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "ME2L_MALFORMED.csv"
        csv_content = """po_date,vendor_name,material_code,unit_price,quantity
2026-03-01,VENDOR_A,MAT_RESIN,120.00,500.0
2026-03-02,VENDOR_B,MAT_SOLVENT,0.00,200.0
2026-03-03,VENDOR_C,MAT_PIGMENT,85.00,-10.0
"""
        csv_file.write_text(csv_content, encoding="utf-8")

        handler = DeadLetterHandler()
        batch_id = f"TEST_ME2L_PROCUREMENT_{uuid.uuid4().hex[:8]}"
        report = await handler.process_and_quarantine(
            csv_file,
            report_type=SAPReportType.ME2L,
            batch_id=batch_id,
            persist_to_db=True,
        )

        assert report.total_rows == 3
        assert report.valid_rows_count == 1
        assert report.quarantined_rows_count == 2
        assert report.persisted_count == 2
