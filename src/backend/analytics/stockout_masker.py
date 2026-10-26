"""Historical Stockout Preprocessing Engine to Prevent Demand Distortion.

Scans historical SAP inventory logs (MB52 stock snapshots, MSEG material documents)
for zero-stock periods across all 8 Nerolac depots in Bangladesh and updates
`historical_sales` setting `is_stockout_flag = TRUE` so downstream ML forecasting models
(LightGBM/Prophet) do not confuse inventory starvation with zero customer demand.
Crucially guarantees that historical revenue actuals and sales volumes remain 100% unaltered.
"""

from __future__ import annotations

import csv
import logging
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import asyncpg
import numpy as np
import pandas as pd

from src.backend.config.vault import get_vault_client

logger = logging.getLogger("nerolac.analytics.stockout_masker")

# Canonical 8 Nerolac Depots across Bangladesh
NEROLAC_DEPOTS: dict[str, str] = {
    "DEPOT_01": "Dhaka Central Depot",
    "DEPOT_02": "Chittagong Depot",
    "DEPOT_03": "Sylhet Depot",
    "DEPOT_04": "Rajshahi Depot",
    "DEPOT_05": "Khulna Depot",
    "DEPOT_06": "Barishal Depot",
    "DEPOT_07": "Rangpur Depot",
    "DEPOT_08": "Mymensingh Depot",
}


class RevenueIntegrityViolationError(RuntimeError):
    """Raised if financial actuals or revenue figures are tampered with during stockout masking."""


@dataclass(frozen=True)
class StockoutEvent:
    """Represents a zero-stock event for a SKU at a depot on a specific date."""

    depot_id: str
    sku_id: str
    stockout_date: date
    stock_quantity: float = 0.0
    source_report: str = "MB52"  # "MB52" or "MSEG"
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_key(self) -> tuple[str, str, date]:
        """Unique compound key identifying the stockout event."""
        return (self.depot_id, self.sku_id, self.stockout_date)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "depot_id": self.depot_id,
            "sku_id": self.sku_id,
            "stockout_date": self.stockout_date.isoformat(),
            "stock_quantity": self.stock_quantity,
            "source_report": self.source_report,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class StockoutPeriod:
    """Represents a contiguous duration of consecutive stockout days."""

    depot_id: str
    sku_id: str
    start_date: date
    end_date: date
    duration_days: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize stockout period to dictionary."""
        return {
            "depot_id": self.depot_id,
            "sku_id": self.sku_id,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "duration_days": self.duration_days,
        }


@dataclass
class StockoutMaskingReport:
    """Summary of stockout scanning, masking, and revenue integrity verification."""

    total_inventory_records_scanned: int
    stockout_events_detected: int
    unique_depots_affected: int
    unique_skus_affected: int
    database_rows_flagged: int
    revenue_actuals_altered: bool
    stockout_periods_count: int
    stockout_events: list[StockoutEvent] = field(default_factory=list)
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to dictionary."""
        data = asdict(self)
        data["stockout_events"] = [e.to_dict() for e in self.stockout_events]
        data["completed_at"] = self.completed_at.isoformat()
        return data


class StockoutMasker:
    """Engine scanning SAP MB52/MSEG logs for stockouts without revenue distortion."""

    def __init__(self, dsn: str | None = None) -> None:
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

    @staticmethod
    def _parse_date(val: Any) -> date:
        """Parse various date representations into a standard date object."""
        if isinstance(val, date):
            return val
        if isinstance(val, datetime):
            return val.date()
        date_str = str(val).strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y%m%d"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Unable to parse date from string: '{val}'")

    def scan_mb52_inventory_snapshots(
        self,
        data_source: Path | str | pd.DataFrame | Sequence[dict[str, Any]],
        stockout_threshold: float = 0.0,
    ) -> list[StockoutEvent]:
        """Scan SAP MB52 daily warehouse inventory logs for zero-stock snapshots.

        Expected fields (with common SAP aliases):
        - depot_id / plant_id / werks / depot
        - sku_id / material_code / matnr / sku_code
        - snapshot_date / inventory_date / date / datum
        - unrestricted_stock / stock_quantity / labst / quantity
        """
        events: list[StockoutEvent] = []

        if isinstance(data_source, (Path, str)):
            csv_path = Path(data_source)
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    depot = str(
                        row.get("depot_id")
                        or row.get("plant_id")
                        or row.get("werks")
                        or row.get("depot")
                        or ""
                    ).strip()
                    sku = str(
                        row.get("sku_id")
                        or row.get("material_code")
                        or row.get("matnr")
                        or row.get("sku_code")
                        or ""
                    ).strip()
                    raw_date = (
                        row.get("snapshot_date")
                        or row.get("inventory_date")
                        or row.get("date")
                        or row.get("datum")
                    )
                    raw_stock = (
                        row.get("unrestricted_stock")
                        or row.get("stock_quantity")
                        or row.get("labst")
                        or row.get("quantity")
                        or "0.0"
                    )

                    if not depot or not sku or not raw_date:
                        continue

                    stock_val = float(str(raw_stock).replace(",", ""))
                    event_date = self._parse_date(raw_date)

                    if stock_val <= stockout_threshold:
                        events.append(
                            StockoutEvent(
                                depot_id=depot,
                                sku_id=sku,
                                stockout_date=event_date,
                                stock_quantity=stock_val,
                                source_report="MB52",
                            )
                        )

        elif isinstance(data_source, pd.DataFrame):
            df = data_source.copy()
            # Normalize column names
            cols_map = {c: str(c).strip().lower() for c in df.columns}
            df.rename(columns=cols_map, inplace=True)

            depot_col = next(
                (c for c in ["depot_id", "plant_id", "werks", "depot"] if c in df.columns), None
            )
            sku_col = next(
                (c for c in ["sku_id", "material_code", "matnr", "sku_code"] if c in df.columns),
                None,
            )
            date_col = next(
                (
                    c
                    for c in ["snapshot_date", "inventory_date", "date", "datum"]
                    if c in df.columns
                ),
                None,
            )
            stock_col = next(
                (
                    c
                    for c in [
                        "unrestricted_stock",
                        "stock_quantity",
                        "labst",
                        "quantity",
                        "stock_liters",
                    ]
                    if c in df.columns
                ),
                None,
            )

            if not (depot_col and sku_col and date_col and stock_col):
                raise ValueError(
                    f"DataFrame missing required MB52 columns. Found: {list(df.columns)}"
                )

            zero_stock_df = df[df[stock_col] <= stockout_threshold]
            for _, df_row in zero_stock_df.iterrows():
                events.append(
                    StockoutEvent(
                        depot_id=str(df_row[depot_col]).strip(),
                        sku_id=str(df_row[sku_col]).strip(),
                        stockout_date=self._parse_date(df_row[date_col]),
                        stock_quantity=float(df_row[stock_col]),
                        source_report="MB52",
                    )
                )

        else:
            for item in data_source:
                depot = str(
                    item.get("depot_id")
                    or item.get("plant_id")
                    or item.get("werks")
                    or item.get("depot")
                    or ""
                ).strip()
                sku = str(
                    item.get("sku_id")
                    or item.get("material_code")
                    or item.get("matnr")
                    or item.get("sku_code")
                    or ""
                ).strip()
                raw_date = (
                    item.get("snapshot_date")
                    or item.get("inventory_date")
                    or item.get("date")
                    or item.get("datum")
                )
                raw_stock = (
                    item.get("unrestricted_stock")
                    or item.get("stock_quantity")
                    or item.get("labst")
                    or item.get("quantity")
                    or 0.0
                )

                if not depot or not sku or not raw_date:
                    continue

                stock_val = float(raw_stock)
                event_date = self._parse_date(raw_date)

                if stock_val <= stockout_threshold:
                    events.append(
                        StockoutEvent(
                            depot_id=depot,
                            sku_id=sku,
                            stockout_date=event_date,
                            stock_quantity=stock_val,
                            source_report="MB52",
                        )
                    )

        # Remove duplicate events for the same (depot, sku, date)
        unique_events: dict[tuple[str, str, date], StockoutEvent] = {}
        for ev in events:
            unique_events[ev.to_key()] = ev

        logger.info(
            "Scanned MB52 inventory records. Identified %d zero-stock events.",
            len(unique_events),
        )
        return list(unique_events.values())

    def scan_mseg_material_movements(
        self,
        data_source: Path | str | pd.DataFrame | Sequence[dict[str, Any]],
        initial_stock: dict[tuple[str, str], float] | None = None,
        stockout_threshold: float = 0.0,
    ) -> list[StockoutEvent]:
        """Scan SAP MSEG material documents and cumulative balances for zero-stock events."""
        events: list[StockoutEvent] = []
        running_balances: dict[tuple[str, str], float] = dict(initial_stock or {})

        records: list[dict[str, Any]] = []
        if isinstance(data_source, (Path, str)):
            with open(data_source, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                records = list(reader)
        elif isinstance(data_source, pd.DataFrame):
            records = [
                {str(k): v for k, v in d.items()}
                for d in data_source.to_dict(orient="records")
            ]
        else:
            records = list(data_source)

        # Sort records chronologically
        parsed_records: list[tuple[date, str, str, float]] = []
        for r in records:
            d = self._parse_date(r.get("posting_date") or r.get("date"))
            depot = str(r.get("depot_id") or r.get("plant_id") or "").strip()
            sku = str(r.get("sku_id") or r.get("material_code") or "").strip()
            qty = float(r.get("quantity", 0.0))
            # 601 (Goods issue for delivery) is negative movement; 101 (Goods receipt) is positive
            m_type = str(r.get("movement_type", "101")).strip()
            if m_type in ("601", "201", "261", "301_OUT") and qty > 0:
                qty = -qty
            parsed_records.append((d, depot, sku, qty))

        parsed_records.sort(key=lambda x: x[0])

        for event_date, depot, sku, delta_qty in parsed_records:
            key = (depot, sku)
            current_bal = running_balances.get(key, 0.0) + delta_qty
            running_balances[key] = current_bal

            if current_bal <= stockout_threshold:
                events.append(
                    StockoutEvent(
                        depot_id=depot,
                        sku_id=sku,
                        stockout_date=event_date,
                        stock_quantity=max(current_bal, 0.0),
                        source_report="MSEG",
                    )
                )

        unique_events: dict[tuple[str, str, date], StockoutEvent] = {}
        for ev in events:
            unique_events[ev.to_key()] = ev

        return list(unique_events.values())

    @staticmethod
    def identify_stockout_periods(events: list[StockoutEvent]) -> list[StockoutPeriod]:
        """Group discrete stockout dates into contiguous start_date to end_date periods."""
        if not events:
            return []

        # Group by (depot_id, sku_id)
        grouped: dict[tuple[str, str], list[date]] = {}
        for ev in events:
            key = (ev.depot_id, ev.sku_id)
            grouped.setdefault(key, []).append(ev.stockout_date)

        periods: list[StockoutPeriod] = []

        for (depot, sku), dates in grouped.items():
            sorted_dates = sorted(set(dates))
            start_d = sorted_dates[0]
            prev_d = sorted_dates[0]

            for curr_d in sorted_dates[1:]:
                if curr_d == prev_d + timedelta(days=1):
                    prev_d = curr_d
                else:
                    duration = (prev_d - start_d).days + 1
                    periods.append(
                        StockoutPeriod(
                            depot_id=depot,
                            sku_id=sku,
                            start_date=start_d,
                            end_date=prev_d,
                            duration_days=duration,
                        )
                    )
                    start_d = curr_d
                    prev_d = curr_d

            # Append final span
            final_duration = (prev_d - start_d).days + 1
            periods.append(
                StockoutPeriod(
                    depot_id=depot,
                    sku_id=sku,
                    start_date=start_d,
                    end_date=prev_d,
                    duration_days=final_duration,
                )
            )

        return periods

    async def update_historical_sales_stockout_flags(
        self,
        stockout_events: Sequence[StockoutEvent],
        batch_size: int = 5000,
    ) -> int:
        """Update `historical_sales` table setting `is_stockout_flag = TRUE` for stockout dates.

        Guarantees:
        - `quantity_liters` and `net_revenue` are NOT modified.
        - Exactly matches (depot_id, sku_id, sales_date).
        """
        if not stockout_events:
            return 0

        # Extract unique keys
        unique_keys = list({(e.depot_id, e.sku_id, e.stockout_date) for e in stockout_events})
        total_keys = len(unique_keys)

        conn = await self._get_connection()
        total_rows_updated = 0

        update_sql = """
            UPDATE nerolac_ops.historical_sales
            SET is_stockout_flag = TRUE
            WHERE depot_id = $1 AND sku_id = $2 AND sales_date = $3;
        """

        try:
            for i in range(0, total_keys, batch_size):
                chunk = unique_keys[i : i + batch_size]
                async with conn.transaction():
                    status = await conn.executemany(update_sql, chunk)
                    # executemany in asyncpg returns None; we count affected rows if needed
                    logger.debug("Executed stockout update chunk: %s", status)

            # Query count of currently flagged rows
            count_flagged: int = await conn.fetchval(
                "SELECT count(*) FROM nerolac_ops.historical_sales WHERE is_stockout_flag = TRUE;"
            )
            total_rows_updated = count_flagged
            logger.info(
                "Successfully updated historical_sales table. "
                "Current rows with is_stockout_flag=TRUE: %d",
                total_rows_updated,
            )
            return total_rows_updated

        finally:
            await conn.close()

    @staticmethod
    def verify_revenue_integrity(
        before_df: pd.DataFrame,
        after_df: pd.DataFrame,
    ) -> bool:
        """Verify with 100% mathematical certainty that revenue actuals were not modified.

        Throws RevenueIntegrityViolationError if any discrepancy is detected.
        """
        if len(before_df) != len(after_df):
            raise RevenueIntegrityViolationError(
                f"Row count mismatch: before={len(before_df)}, after={len(after_df)}"
            )

        # Revenue checks
        rev_before = float(before_df["net_revenue"].sum())
        rev_after = float(after_df["net_revenue"].sum())
        if abs(rev_before - rev_after) > 1e-4:
            raise RevenueIntegrityViolationError(
                f"Revenue altered during stockout masking! "
                f"Before: {rev_before:,.2f} BDT, After: {rev_after:,.2f} BDT"
            )

        # Quantity checks
        qty_before = float(before_df["quantity_liters"].sum())
        qty_after = float(after_df["quantity_liters"].sum())
        if abs(qty_before - qty_after) > 1e-4:
            raise RevenueIntegrityViolationError(
                f"Sales quantities altered during stockout masking! "
                f"Before: {qty_before:,.2f} L, After: {qty_after:,.2f} L"
            )

        # Row-by-row equality verification
        if not np.array_equal(
            before_df["net_revenue"].to_numpy(), after_df["net_revenue"].to_numpy()
        ):
            raise RevenueIntegrityViolationError(
                "Discrepancy detected in individual row revenue figures."
            )

        if not np.array_equal(
            before_df["quantity_liters"].to_numpy(), after_df["quantity_liters"].to_numpy()
        ):
            raise RevenueIntegrityViolationError(
                "Discrepancy detected in individual row quantity figures."
            )

        return True

    def mask_sales_dataframe(
        self,
        sales_df: pd.DataFrame,
        stockout_events: Sequence[StockoutEvent],
    ) -> pd.DataFrame:
        """Flag `is_stockout_flag = TRUE` in sales DataFrame with revenue integrity guarantee."""
        # Baseline snapshot for integrity verification
        baseline_df = sales_df.copy()

        result_df = sales_df.copy()
        if "is_stockout_flag" not in result_df.columns:
            result_df["is_stockout_flag"] = False

        # Convert date column to standard date objects if string/datetime
        result_df["_temp_date"] = result_df["sales_date"].apply(self._parse_date)

        # Build lookup set of stockout keys
        stockout_set = {(e.depot_id, e.sku_id, e.stockout_date) for e in stockout_events}

        def _is_stockout(row: pd.Series) -> bool:
            key = (str(row["depot_id"]).strip(), str(row["sku_id"]).strip(), row["_temp_date"])
            return key in stockout_set

        # Apply flag
        mask = result_df.apply(_is_stockout, axis=1)
        result_df.loc[mask, "is_stockout_flag"] = True
        result_df.drop(columns=["_temp_date"], inplace=True)

        # Enforce revenue integrity verification
        self.verify_revenue_integrity(baseline_df, result_df)
        return result_df

    def prepare_ml_demand_dataset(
        self,
        sales_df: pd.DataFrame,
        stockout_events: Sequence[StockoutEvent] | None = None,
    ) -> pd.DataFrame:
        """Prepare feature-engineered dataset for downstream ML forecasting (LightGBM/Prophet).

        Adds:
        - `is_stockout_flag`: Boolean indicator of zero-stock event.
        - `effective_demand_liters`: Uncensored demand signal (NaN on stockouts for imputation
          so ML models do not learn false zero demand).
        - Revenue actuals and true sales volume figures are strictly preserved intact.
        """
        if stockout_events:
            processed_df = self.mask_sales_dataframe(sales_df, stockout_events)
        else:
            processed_df = sales_df.copy()
            if "is_stockout_flag" not in processed_df.columns:
                processed_df["is_stockout_flag"] = False

        # Effective demand for ML: mask stockout zeros to avoid demand underestimation
        processed_df["effective_demand_liters"] = processed_df["quantity_liters"]
        # On stockout days where sales were zero or truncated, mark as censored
        stockout_mask = processed_df["is_stockout_flag"] == True  # noqa: E712
        processed_df.loc[stockout_mask, "effective_demand_liters"] = None

        return processed_df
