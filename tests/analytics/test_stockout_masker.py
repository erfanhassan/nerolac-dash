"""Unit & Integration Test Suite for Historical Stockout Preprocessing Engine.

Verifies:
1. Scanning historical SAP inventory logs (MB52 snapshots, MSEG movements)
   for zero-stock periods across all 8 Nerolac depots in Bangladesh.
2. Aggregation of contiguous stockout days into StockoutPeriod spans.
3. Accurate flagging of stockout dates (`is_stockout_flag = TRUE`) in historical_sales.
4. Absolute revenue integrity assertion: net_revenue and sales volume actuals
   remain 100% unaltered.
5. ML demand dataset preparation for LightGBM/Prophet without demand distortion.
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

import asyncpg
import numpy as np
import pandas as pd
import pytest

from src.backend.analytics.stockout_masker import (
    NEROLAC_DEPOTS,
    RevenueIntegrityViolationError,
    StockoutEvent,
    StockoutMasker,
)
from src.backend.config.vault import get_vault_client


@pytest.fixture
def masker() -> StockoutMasker:
    return StockoutMasker()


@pytest.fixture
async def db_conn() -> asyncpg.Connection:
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


class TestMB52StockoutScanning:
    """Test suite for scanning SAP MB52 warehouse stock snapshot files."""

    def test_scan_mb52_csv_across_all_8_depots(
        self, tmp_path: Path, masker: StockoutMasker
    ) -> None:
        """Verify zero-stock detection across all 8 Nerolac depots in Bangladesh."""
        mb52_file = tmp_path / "MB52_SNAPSHOT_ALL_DEPOTS.csv"
        rows: list[dict[str, str]] = []

        # Generate entries for all 8 depots: some with stock, some with 0 stock
        for idx, depot_id in enumerate(NEROLAC_DEPOTS.keys(), 1):
            # Stockout for DEC_EXT_EXCEL_WHITE on 2026-05-10
            rows.append(
                {
                    "depot_id": depot_id,
                    "sku_id": "DEC_EXT_EXCEL_WHITE",
                    "snapshot_date": "2026-05-10",
                    "unrestricted_stock": "0.0",
                }
            )
            # Available stock on 2026-05-11
            rows.append(
                {
                    "depot_id": depot_id,
                    "sku_id": "DEC_EXT_EXCEL_WHITE",
                    "snapshot_date": "2026-05-11",
                    "unrestricted_stock": str(1500.0 * idx),
                }
            )

        with open(mb52_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        events = masker.scan_mb52_inventory_snapshots(mb52_file)

        # Exactly 8 zero-stock events (1 per depot on 2026-05-10)
        assert len(events) == 8
        affected_depots = {e.depot_id for e in events}
        assert affected_depots == set(NEROLAC_DEPOTS.keys())
        for e in events:
            assert e.stockout_date == date(2026, 5, 10)
            assert e.stock_quantity == 0.0
            assert e.source_report == "MB52"

    def test_scan_mb52_dataframe_input(self, masker: StockoutMasker) -> None:
        """Verify scanning pandas DataFrame with alias column names."""
        df = pd.DataFrame(
            [
                {
                    "plant_id": "DEPOT_01",
                    "material_code": "IND_EPOXY_FLOOR_GR",
                    "date": "2026-06-01",
                    "quantity": 0.0,
                },
                {
                    "plant_id": "DEPOT_01",
                    "material_code": "IND_EPOXY_FLOOR_GR",
                    "date": "2026-06-02",
                    "quantity": 500.0,
                },
                {
                    "plant_id": "DEPOT_02",
                    "material_code": "IND_PU_TOPCOAT_WHITE",
                    "date": "2026-06-01",
                    "quantity": 0.0,
                },
            ]
        )
        events = masker.scan_mb52_inventory_snapshots(df)
        assert len(events) == 2
        keys = {(e.depot_id, e.sku_id, e.stockout_date) for e in events}
        assert ("DEPOT_01", "IND_EPOXY_FLOOR_GR", date(2026, 6, 1)) in keys
        assert ("DEPOT_02", "IND_PU_TOPCOAT_WHITE", date(2026, 6, 1)) in keys


class TestMSEGMovementScanning:
    """Test suite for tracking cumulative stock and stockouts via MSEG material documents."""

    def test_scan_mseg_running_balance_depletion(self, masker: StockoutMasker) -> None:
        """Verify stockout is triggered when delivery issues (601) deplete stock to 0."""
        movements = [
            # Initial receipt 1000L
            {
                "depot_id": "DEPOT_01",
                "sku_id": "DEC_INT_BEAUTY_GOLD",
                "date": "2026-07-01",
                "movement_type": "101",
                "quantity": 1000.0,
            },
            # Issue 600L -> remaining 400L (in stock)
            {
                "depot_id": "DEPOT_01",
                "sku_id": "DEC_INT_BEAUTY_GOLD",
                "date": "2026-07-02",
                "movement_type": "601",
                "quantity": 600.0,
            },
            # Issue 400L -> remaining 0L (STOCKOUT on 2026-07-03)
            {
                "depot_id": "DEPOT_01",
                "sku_id": "DEC_INT_BEAUTY_GOLD",
                "date": "2026-07-03",
                "movement_type": "601",
                "quantity": 400.0,
            },
            # Receipt 1500L on 2026-07-05 (replenished)
            {
                "depot_id": "DEPOT_01",
                "sku_id": "DEC_INT_BEAUTY_GOLD",
                "date": "2026-07-05",
                "movement_type": "101",
                "quantity": 1500.0,
            },
        ]
        events = masker.scan_mseg_material_movements(movements)
        assert len(events) == 1
        assert events[0].depot_id == "DEPOT_01"
        assert events[0].sku_id == "DEC_INT_BEAUTY_GOLD"
        assert events[0].stockout_date == date(2026, 7, 3)
        assert events[0].source_report == "MSEG"


class TestStockoutPeriodAggregation:
    """Test suite for grouping contiguous stockout dates into duration periods."""

    def test_contiguous_stockout_period_span(self, masker: StockoutMasker) -> None:
        """Verify consecutive dates span from start_date to end_date."""
        events = [
            StockoutEvent("DEPOT_01", "DEC_EXT_EXCEL_WHITE", date(2026, 8, 1)),
            StockoutEvent("DEPOT_01", "DEC_EXT_EXCEL_WHITE", date(2026, 8, 2)),
            StockoutEvent("DEPOT_01", "DEC_EXT_EXCEL_WHITE", date(2026, 8, 3)),
            # Gap of 3 days
            StockoutEvent("DEPOT_01", "DEC_EXT_EXCEL_WHITE", date(2026, 8, 7)),
        ]
        periods = masker.identify_stockout_periods(events)
        assert len(periods) == 2

        # Period 1: Aug 1 to Aug 3 (3 days)
        assert periods[0].start_date == date(2026, 8, 1)
        assert periods[0].end_date == date(2026, 8, 3)
        assert periods[0].duration_days == 3

        # Period 2: Aug 7 (1 day)
        assert periods[1].start_date == date(2026, 8, 7)
        assert periods[1].end_date == date(2026, 8, 7)
        assert periods[1].duration_days == 1


class TestSalesMaskingAndRevenueIntegrity:
    """Test suite verifying stockouts are flagged without altering revenue actuals."""

    @pytest.fixture
    def sample_sales_df(self) -> pd.DataFrame:
        """Generate 10-day sales time series for two SKUs across two depots."""
        records = []
        base_d = date(2026, 9, 1)
        for i in range(10):
            d = base_d + timedelta(days=i)
            # Normal sales on all days except stockouts
            records.append(
                {
                    "depot_id": "DEPOT_01",
                    "sku_id": "DEC_EXT_EXCEL_WHITE",
                    "sales_date": d,
                    "quantity_liters": 0.0 if i in (3, 4) else 150.0 + (i * 10),
                    "net_revenue": 0.0 if i in (3, 4) else (150.0 + (i * 10)) * 450.0,
                }
            )
            records.append(
                {
                    "depot_id": "DEPOT_02",
                    "sku_id": "IND_EPOXY_FLOOR_GR",
                    "sales_date": d,
                    "quantity_liters": 250.0 + (i * 15),
                    "net_revenue": (250.0 + (i * 15)) * 620.0,
                }
            )
        return pd.DataFrame(records)

    def test_mask_sales_dataframe_flags_stockouts_accurately(
        self, masker: StockoutMasker, sample_sales_df: pd.DataFrame
    ) -> None:
        """Assert stockout dates are accurately flagged as True."""
        # Stockout on days 3 and 4 (Sep 4 and Sep 5) for DEPOT_01
        events = [
            StockoutEvent("DEPOT_01", "DEC_EXT_EXCEL_WHITE", date(2026, 9, 4)),
            StockoutEvent("DEPOT_01", "DEC_EXT_EXCEL_WHITE", date(2026, 9, 5)),
        ]

        masked_df = masker.mask_sales_dataframe(sample_sales_df, events)

        # Check flag column exists
        assert "is_stockout_flag" in masked_df.columns

        # Verify flagged rows
        depot1_excel = masked_df[
            (masked_df["depot_id"] == "DEPOT_01")
            & (masked_df["sku_id"] == "DEC_EXT_EXCEL_WHITE")
        ]
        flagged_days = depot1_excel[depot1_excel["is_stockout_flag"] == True]  # noqa: E712
        assert len(flagged_days) == 2
        flagged_dates = set(flagged_days["sales_date"].values)
        assert date(2026, 9, 4) in flagged_dates
        assert date(2026, 9, 5) in flagged_dates

        # Non-stockout days remain False
        unflagged_days = depot1_excel[depot1_excel["is_stockout_flag"] == False]  # noqa: E712
        assert len(unflagged_days) == 8

        # Other depot remains False on all 10 days
        depot2_epoxy = masked_df[masked_df["depot_id"] == "DEPOT_02"]
        assert (depot2_epoxy["is_stockout_flag"] == False).all()  # noqa: E712

    def test_strict_revenue_integrity_assertion(
        self, masker: StockoutMasker, sample_sales_df: pd.DataFrame
    ) -> None:
        """CRITICAL: Assert that revenue and sales volume actuals remain 100% unaltered."""
        total_rev_before = float(sample_sales_df["net_revenue"].sum())
        total_qty_before = float(sample_sales_df["quantity_liters"].sum())

        events = [
            StockoutEvent("DEPOT_01", "DEC_EXT_EXCEL_WHITE", date(2026, 9, 4)),
            StockoutEvent("DEPOT_01", "DEC_EXT_EXCEL_WHITE", date(2026, 9, 5)),
        ]

        masked_df = masker.mask_sales_dataframe(sample_sales_df, events)

        total_rev_after = float(masked_df["net_revenue"].sum())
        total_qty_after = float(masked_df["quantity_liters"].sum())

        # Exact mathematical equality
        assert total_rev_before == total_rev_after
        assert total_qty_before == total_qty_after
        assert np.array_equal(
            sample_sales_df["net_revenue"].to_numpy(),
            masked_df["net_revenue"].to_numpy(),
        )
        assert np.array_equal(
            sample_sales_df["quantity_liters"].to_numpy(),
            masked_df["quantity_liters"].to_numpy(),
        )

    def test_revenue_tampering_raises_exception(
        self, masker: StockoutMasker, sample_sales_df: pd.DataFrame
    ) -> None:
        """Verify RevenueIntegrityViolationError is raised if any revenue figure changes."""
        tampered_df = sample_sales_df.copy()
        current_rev = float(str(tampered_df.at[0, "net_revenue"]))
        tampered_df.at[0, "net_revenue"] = current_rev + 1.00  # Modify 1 BDT

        with pytest.raises(RevenueIntegrityViolationError, match="Revenue altered"):
            masker.verify_revenue_integrity(sample_sales_df, tampered_df)

    def test_prepare_ml_demand_dataset_masks_zero_demand(
        self, masker: StockoutMasker, sample_sales_df: pd.DataFrame
    ) -> None:
        """Verify downstream ML dataset has effective demand masked for Prophet/LightGBM."""
        events = [
            StockoutEvent("DEPOT_01", "DEC_EXT_EXCEL_WHITE", date(2026, 9, 4)),
            StockoutEvent("DEPOT_01", "DEC_EXT_EXCEL_WHITE", date(2026, 9, 5)),
        ]
        ml_df = masker.prepare_ml_demand_dataset(sample_sales_df, events)

        # Revenue actuals remain intact
        assert ml_df["net_revenue"].sum() == sample_sales_df["net_revenue"].sum()
        assert ml_df["quantity_liters"].sum() == sample_sales_df["quantity_liters"].sum()

        # Effective demand is NaN on stockout days
        stockout_rows = ml_df[ml_df["is_stockout_flag"] == True]  # noqa: E712
        assert stockout_rows["effective_demand_liters"].isna().all()

        # Effective demand is equal to quantity_liters on normal days
        normal_rows = ml_df[ml_df["is_stockout_flag"] == False]  # noqa: E712
        assert np.array_equal(
            normal_rows["effective_demand_liters"].to_numpy(),
            normal_rows["quantity_liters"].to_numpy(),
        )


@pytest.mark.asyncio
class TestDatabaseHistoricalSalesUpdate:
    """Integration test suite verifying database updates to nerolac_ops.historical_sales."""

    async def test_database_sales_stockout_flag_update(
        self, db_conn: asyncpg.Connection, masker: StockoutMasker
    ) -> None:
        """Verify database UPDATE sets is_stockout_flag=TRUE without altering revenues."""
        test_depot = "DEPOT_01"
        test_sku = "SKU_SO_TEST"

        # Ensure prerequisite depot and SKU exist to satisfy foreign keys
        await db_conn.execute(
            """
            INSERT INTO nerolac_ops.depots (depot_id, depot_code, depot_name, region)
            VALUES ($1, $1, 'Dhaka Central', 'DHAKA')
            ON CONFLICT (depot_id) DO NOTHING;
            """,
            test_depot,
        )
        await db_conn.execute(
            """
            INSERT INTO nerolac_ops.skus (sku_id, sku_code, sku_name, category)
            VALUES ($1, $1, 'Test Paint SKU', 'DECORATIVE')
            ON CONFLICT (sku_id) DO NOTHING;
            """,
            test_sku,
        )

        # Insert 3 sales records (2 normal, 1 stockout day)
        d1 = date(2026, 10, 1)
        d2 = date(2026, 10, 2)  # will be flagged
        d3 = date(2026, 10, 3)

        await db_conn.execute(
            """
            INSERT INTO nerolac_ops.historical_sales
                (depot_id, sku_id, sales_date, quantity_liters, net_revenue, is_stockout_flag)
            VALUES
                ($1, $2, $3, 100.0, 45000.00, FALSE),
                ($1, $2, $4, 0.0, 0.00, FALSE),
                ($1, $2, $5, 120.0, 54000.00, FALSE)
            ON CONFLICT (depot_id, sku_id, sales_date) DO UPDATE
            SET quantity_liters = EXCLUDED.quantity_liters,
                net_revenue = EXCLUDED.net_revenue,
                is_stockout_flag = FALSE;
            """,
            test_depot,
            test_sku,
            d1,
            d2,
            d3,
        )

        # Record total revenue before update
        total_rev_before: float = await db_conn.fetchval(
            """
            SELECT sum(net_revenue) FROM nerolac_ops.historical_sales
            WHERE depot_id = $1 AND sku_id = $2;
            """,
            test_depot,
            test_sku,
        )

        # Execute stockout update
        stockout_event = StockoutEvent(test_depot, test_sku, d2)
        await masker.update_historical_sales_stockout_flags([stockout_event])

        # Verify d2 is flagged TRUE, d1 and d3 are FALSE
        flag_d2 = await db_conn.fetchval(
            """
            SELECT is_stockout_flag FROM nerolac_ops.historical_sales
            WHERE depot_id = $1 AND sku_id = $2 AND sales_date = $3;
            """,
            test_depot,
            test_sku,
            d2,
        )
        assert flag_d2 is True

        flag_d1 = await db_conn.fetchval(
            """
            SELECT is_stockout_flag FROM nerolac_ops.historical_sales
            WHERE depot_id = $1 AND sku_id = $2 AND sales_date = $3;
            """,
            test_depot,
            test_sku,
            d1,
        )
        assert flag_d1 is False

        # Verify revenue actuals are 100% unaltered in database
        total_rev_after: float = await db_conn.fetchval(
            """
            SELECT sum(net_revenue) FROM nerolac_ops.historical_sales
            WHERE depot_id = $1 AND sku_id = $2;
            """,
            test_depot,
            test_sku,
        )
        assert float(total_rev_before) == float(total_rev_after)
