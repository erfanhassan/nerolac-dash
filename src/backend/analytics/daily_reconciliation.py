"""Evening 7:00 PM SAP Daily Reconciliation Engine.

Compares daily self-reported field sales from WhatsApp against official SAP S/4HANA
billing invoices (VA05 / FAGLL03) across all 8 regional depots in Bangladesh.
Identifies discrepancies, calculates variances, and highlights top-10 audit exceptions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.backend.api.v1.schemas.whatsapp_schemas import (
    DailyReconciliationResponse,
    DepotReconSummary,
    ReconciliationExceptionItem,
)
from src.backend.cache.cache_invalidation import CacheAsideManager
from src.backend.config.redis_config import DB_QUERY_CACHE, get_redis_client
from src.backend.workers.whatsapp_parser import get_message_store

logger = logging.getLogger("nerolac.analytics.daily_reconciliation")

# Standard SAP Invoicing Simulation Data (as of 7:00 PM BST)
SAP_INVOICED_LEDGER: list[dict[str, Any]] = [
    {
        "dealer_code": "D-40982",
        "dealer_name": "Bismillah Hardware & Paint Store",
        "depot_id": "DEPOT_02",
        "depot_name": "Chittagong Port Depot",
        "sales_rep_name": "Kamrul Hassan",
        "sales_rep_phone": "8801711223344",
        "sap_invoiced_bdt": 39750.0,  # WA reported: 5x4250 + 10x1850 = 39,750 (Exact match)
        "sap_invoice_number": "INV-CTG-2024-9041",
    },
    {
        "dealer_code": "D-10245",
        "dealer_name": "Rahman Enterprise & Color Center",
        "depot_id": "DEPOT_01",
        "depot_name": "Dhaka Central Hub",
        "sales_rep_name": "Tanvir Ahmed",
        "sales_rep_phone": "8801711334455",
        "sap_invoiced_bdt": 62500.0,
        "sap_invoice_number": "INV-DHK-2024-1102",
        "exception_reason": "Order blocked in SAP SD: Customer credit limit exceeded.",
        "action_guidance": "Finance Director approval required to release pending sales delivery.",
    },
    {
        "dealer_code": "D-30419",
        "dealer_name": "M/S Bhai Bhai Traders Bogura",
        "depot_id": "DEPOT_03",
        "depot_name": "Bogura Distribution Center",
        "sales_rep_name": "Mizanur Rahman",
        "sales_rep_phone": "8801711445566",
        "sap_invoiced_bdt": 57600.0,  # WA reported: 8x4800 + 12x1600 = 57,600 (Exact match)
        "sap_invoice_number": "INV-BGR-2024-3420",
    },
    {
        "dealer_code": "D-50811",
        "dealer_name": "Haji Paint House Sylhet",
        "depot_id": "DEPOT_04",
        "depot_name": "Sylhet Depot",
        "sales_rep_name": "Farid Uddin",
        "sales_rep_phone": "8801711556677",
        "sap_invoiced_bdt": 172000.0,  # WA reported: 15x4800 + 8x12500 = 172,000 (Exact match)
        "sap_invoice_number": "INV-SYL-2024-5519",
    },
    {
        "dealer_code": "D-60122",
        "dealer_name": "Khan & Sons Decor Khulna",
        "depot_id": "DEPOT_05",
        "depot_name": "Khulna Coastal Hub",
        "sales_rep_name": "Sharif Hossain",
        "sales_rep_phone": "8801711667788",
        "sap_invoiced_bdt": 32900.0,  # WA reported: 6x4250 + 4x1850 = 32,900 (Exact match)
        "sap_invoice_number": "INV-KLN-2024-7714",
    },
    {
        "dealer_code": "D-70334",
        "dealer_name": "Padma Hardware Rajshahi",
        "depot_id": "DEPOT_06",
        "depot_name": "Rajshahi Depot",
        "sales_rep_name": "Enamul Haque",
        "sales_rep_phone": "8801711778899",
        "sap_invoiced_bdt": 79800.0,  # WA reported: 12x4250 + 6x4800 = 79,800 (Exact match)
        "sap_invoice_number": "INV-RAJ-2024-8110",
    },
    {
        "dealer_code": "D-80512",
        "dealer_name": "Barishal Color World",
        "depot_id": "DEPOT_07",
        "depot_name": "Barishal Depot",
        "sales_rep_name": "Jashim Uddin",
        "sales_rep_phone": "8801711889900",
        "sap_invoiced_bdt": 44500.0,  # WA reported: 10x1850 + 5x1600 = 26,500 -> Variance -18,000
        "sap_invoice_number": "INV-BAR-2024-2190",
        "exception_reason": "Direct walk-in dealer counter purchase generated in SAP.",
        "action_guidance": "Rep must verify counter delivery challan and reconcile collection log.",
    },
    {
        "dealer_code": "D-90641",
        "dealer_name": "Al-Madina Paint Gallery Comilla",
        "depot_id": "DEPOT_08",
        "depot_name": "Comilla Regional Hub",
        "sales_rep_name": "Zubair Ahmed",
        "sales_rep_phone": "8801711990011",
        "sap_invoiced_bdt": 210000.0,  # WA reported: 20x4250 + 10x12500 = 210,000 (Exact match)
        "sap_invoice_number": "INV-COM-2024-4412",
    },
    {
        "dealer_code": "D-11099",
        "dealer_name": "Uttara Color Mansion",
        "depot_id": "DEPOT_01",
        "depot_name": "Dhaka Central Hub",
        "sales_rep_name": "Kamrul Islam",
        "sales_rep_phone": "8801711001122",
        "sap_invoiced_bdt": 85000.0,
        "sap_invoice_number": "INV-DHK-2024-1188",
        "exception_reason": "Missing WhatsApp report: SAP invoiced without field update.",
        "action_guidance": "Automated warning sent to Area Sales Manager for beat discipline.",
    },
    {
        "dealer_code": "D-22180",
        "dealer_name": "Agrabad Hardware Mart",
        "depot_id": "DEPOT_02",
        "depot_name": "Chittagong Port Depot",
        "sales_rep_name": "Nasir Hossain",
        "sales_rep_phone": "8801711002233",
        "sap_invoiced_bdt": 51000.0,
        "sap_invoice_number": "INV-CTG-2024-9104",
        "exception_reason": "PGI Delay: Delivery challan pending warehouse dispatch.",
        "action_guidance": "Depot warehouse supervisor must dispatch goods from stock immediately.",
    },
]


class DailyReconciliationEngine:
    """Evaluates WhatsApp self-reported sales vs. SAP invoicing at 7:00 PM daily."""

    def __init__(self) -> None:
        self.redis_client = get_redis_client(DB_QUERY_CACHE)
        self.cache_manager = CacheAsideManager(self.redis_client)

    async def execute_reconciliation(
        self, recon_date: str | None = None
    ) -> DailyReconciliationResponse:
        """Run daily evening reconciliation across all depots and calculate top-10 exceptions."""
        if not recon_date:
            recon_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        cache_key = f"dash:whatsapp:recon:{recon_date}"
        cached = await self.cache_manager.get(cache_key)
        if cached:
            return DailyReconciliationResponse.model_validate(cached)

        messages = get_message_store()

        # 1. Aggregate WhatsApp sales by dealer_code
        wa_by_dealer: dict[str, dict[str, Any]] = {}
        for msg in messages:
            if msg.dealer and msg.total_sales_bdt > 0:
                code = msg.dealer.dealer_code
                if code not in wa_by_dealer:
                    wa_by_dealer[code] = {
                        "dealer_code": code,
                        "dealer_name": msg.dealer.trade_name,
                        "depot_id": msg.dealer.depot_id,
                        "depot_name": msg.dealer.depot_name,
                        "sales_rep_name": msg.sender_name,
                        "sales_rep_phone": msg.sender_phone,
                        "whatsapp_sales_bdt": 0.0,
                    }
                wa_by_dealer[code]["whatsapp_sales_bdt"] += msg.total_sales_bdt

        # 2. Reconcile with SAP Invoicing Ledger
        reconciled_items: list[dict[str, Any]] = []
        all_dealer_codes = set(wa_by_dealer.keys()) | {
            item["dealer_code"] for item in SAP_INVOICED_LEDGER
        }

        sap_map = {item["dealer_code"]: item for item in SAP_INVOICED_LEDGER}

        for code in sorted(list(all_dealer_codes)):
            wa_item = wa_by_dealer.get(code)
            sap_item = sap_map.get(code)

            wa_sales = float(wa_item["whatsapp_sales_bdt"]) if wa_item else 0.0
            sap_sales = float(sap_item["sap_invoiced_bdt"]) if sap_item else 0.0
            variance = round(wa_sales - sap_sales, 2)
            abs_var = abs(variance)

            # Determine variance pct
            base_sales = sap_sales if sap_sales > 0 else wa_sales
            var_pct = round((variance / base_sales) * 100, 1) if base_sales > 0 else 0.0

            dealer_name = str(
                (sap_item["dealer_name"] if sap_item else None)
                or (wa_item["dealer_name"] if wa_item else None)
                or "Unknown Dealer"
            )
            depot_id = str(
                (sap_item["depot_id"] if sap_item else None)
                or (wa_item["depot_id"] if wa_item else None)
                or "DEPOT_01"
            )
            depot_name = str(
                (sap_item["depot_name"] if sap_item else None)
                or (wa_item["depot_name"] if wa_item else None)
                or "Central Hub"
            )
            rep_name = str(
                (wa_item["sales_rep_name"] if wa_item else None)
                or (sap_item["sales_rep_name"] if sap_item else None)
                or "Assigned Officer"
            )
            rep_phone = str(
                (wa_item["sales_rep_phone"] if wa_item else None)
                or (sap_item["sales_rep_phone"] if sap_item else None)
                or "8801700000000"
            )

            # Classify exception type
            if abs_var <= 50.0:
                ex_type = "BALANCED"
                reason = "Exact match between field WhatsApp report and SAP S/4HANA invoice."
                guidance = "No action required. Reconciled successfully."
            elif wa_sales > 0 and sap_sales == 0:
                ex_type = "OVER_REPORTED"
                reason = (
                    (sap_item.get("exception_reason") if sap_item else None)
                    or "WhatsApp field sale reported, but zero corresponding SAP invoice found."
                )
                guidance = (
                    (sap_item.get("action_guidance") if sap_item else None)
                    or "Check SAP order entry queue for unbilled delivery notes."
                )
            elif wa_sales == 0 and sap_sales > 0:
                ex_type = "MISSING_WHATSAPP_REPORT"
                reason = (
                    (sap_item.get("exception_reason") if sap_item else None)
                    or "SAP invoice generated without sales rep WhatsApp field report."
                )
                guidance = (
                    (sap_item.get("action_guidance") if sap_item else None)
                    or "Sales rep must submit missing end-of-day field dispatch note."
                )
            elif wa_sales > sap_sales:
                ex_type = "OVER_REPORTED"
                reason = (
                    (sap_item.get("exception_reason") if sap_item else None)
                    or f"Reported sales exceed SAP invoice by BDT {abs_var:,.0f}."
                )
                guidance = (
                    (sap_item.get("action_guidance") if sap_item else None)
                    or "Investigate partial delivery or order backlog in SAP SD."
                )
            else:
                ex_type = "UNDER_REPORTED"
                reason = (
                    (sap_item.get("exception_reason") if sap_item else None)
                    or f"SAP invoice exceeds field reported volume by BDT {abs_var:,.0f}."
                )
                guidance = (
                    (sap_item.get("action_guidance") if sap_item else None)
                    or "Verify counter billing receipts with dealer ledger."
                )

            reconciled_items.append(
                {
                    "dealer_code": code,
                    "dealer_name": dealer_name,
                    "depot_id": depot_id,
                    "depot_name": depot_name,
                    "sales_rep_name": rep_name,
                    "sales_rep_phone": rep_phone,
                    "whatsapp_sales_bdt": wa_sales,
                    "sap_invoiced_sales_bdt": sap_sales,
                    "variance_bdt": variance,
                    "abs_variance_bdt": abs_var,
                    "variance_pct": var_pct,
                    "exception_type": ex_type,
                    "exception_reason": reason,
                    "action_guidance": guidance,
                }
            )

        # 3. Sort exceptions by absolute variance descending
        exceptions = [item for item in reconciled_items if item["exception_type"] != "BALANCED"]
        exceptions.sort(key=lambda x: x["abs_variance_bdt"], reverse=True)

        # Assign top-10 rank
        top_10: list[ReconciliationExceptionItem] = []
        for idx, item in enumerate(exceptions[:10], start=1):
            top_10.append(
                ReconciliationExceptionItem(
                    rank=idx,
                    dealer_code=item["dealer_code"],
                    dealer_name=item["dealer_name"],
                    depot_id=item["depot_id"],
                    depot_name=item["depot_name"],
                    sales_rep_name=item["sales_rep_name"],
                    sales_rep_phone=item["sales_rep_phone"],
                    whatsapp_sales_bdt=item["whatsapp_sales_bdt"],
                    sap_invoiced_sales_bdt=item["sap_invoiced_sales_bdt"],
                    variance_bdt=item["variance_bdt"],
                    variance_pct=item["variance_pct"],
                    exception_type=item["exception_type"],
                    exception_reason=item["exception_reason"],
                    action_guidance=item["action_guidance"],
                )
            )

        # 4. Depot Summaries
        depot_map: dict[str, dict[str, Any]] = {}
        for item in reconciled_items:
            d_id = item["depot_id"]
            if d_id not in depot_map:
                depot_map[d_id] = {
                    "depot_id": d_id,
                    "depot_name": item["depot_name"],
                    "total_whatsapp_bdt": 0.0,
                    "total_sap_bdt": 0.0,
                    "variance_bdt": 0.0,
                    "exception_count": 0,
                }
            depot_map[d_id]["total_whatsapp_bdt"] += item["whatsapp_sales_bdt"]
            depot_map[d_id]["total_sap_bdt"] += item["sap_invoiced_sales_bdt"]
            depot_map[d_id]["variance_bdt"] += item["variance_bdt"]
            if item["exception_type"] != "BALANCED":
                depot_map[d_id]["exception_count"] += 1

        depot_summaries: list[DepotReconSummary] = []
        for d in sorted(depot_map.values(), key=lambda x: x["depot_id"]):
            match_pct = (
                round(
                    100.0
                    - min(
                        100.0,
                        (abs(d["variance_bdt"]) / (d["total_sap_bdt"] or 1.0)) * 100.0,
                    ),
                    1,
                )
                if d["total_sap_bdt"] > 0
                else 100.0
            )
            depot_summaries.append(
                DepotReconSummary(
                    depot_id=d["depot_id"],
                    depot_name=d["depot_name"],
                    total_whatsapp_bdt=round(d["total_whatsapp_bdt"], 2),
                    total_sap_bdt=round(d["total_sap_bdt"], 2),
                    variance_bdt=round(d["variance_bdt"], 2),
                    match_rate_pct=max(0.0, match_pct),
                    exception_count=d["exception_count"],
                )
            )

        # 5. Grand Totals
        total_wa = round(sum(i["whatsapp_sales_bdt"] for i in reconciled_items), 2)
        total_sap = round(sum(i["sap_invoiced_sales_bdt"] for i in reconciled_items), 2)
        net_var = round(total_wa - total_sap, 2)
        match_rate = round(
            max(
                0.0,
                100.0
                - min(
                    100.0,
                    (abs(net_var) / (total_sap or 1.0)) * 100.0,
                ),
            ),
            1,
        )

        overall_status = "BALANCED" if len(exceptions) == 0 else "VARIANCE_FLAGGED"

        response = DailyReconciliationResponse(
            reconciliation_date=recon_date,
            reconciliation_time_bst="19:00:00 BST",
            overall_status=overall_status,
            overall_match_rate_pct=match_rate,
            total_whatsapp_sales_bdt=total_wa,
            total_sap_invoiced_bdt=total_sap,
            net_variance_bdt=net_var,
            total_exceptions_count=len(exceptions),
            top_10_exceptions=top_10,
            depot_summaries=depot_summaries,
        )

        # Cache in Redis DB 0 for 5 minutes
        await self.cache_manager.set(cache_key, response.model_dump(), ttl_seconds=300)
        return response


_reconciler_instance: DailyReconciliationEngine | None = None


def get_daily_reconciler() -> DailyReconciliationEngine:
    """Return the global DailyReconciliationEngine singleton."""
    global _reconciler_instance
    if _reconciler_instance is None:
        _reconciler_instance = DailyReconciliationEngine()
    return _reconciler_instance
