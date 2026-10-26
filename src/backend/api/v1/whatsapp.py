"""FastAPI Endpoints for Module 4: WhatsApp Field Intelligence & 7:00 PM SAP Recon.

Endpoints:
1. GET /api/v1/whatsapp/webhook: Meta WhatsApp Webhook Verification Handshake.
2. POST /api/v1/whatsapp/webhook: Ingests WhatsApp events, returns HTTP 200 OK immediately,
   and dispatches async parsing to Celery Redis Queue.
3. GET /api/v1/whatsapp/messages: Returns real-time parsed message stream for dashboard.
4. GET /api/v1/whatsapp/reconciliation: Returns 7:00 PM reconciliation summary and exceptions.
5. POST /api/v1/whatsapp/reconciliation/run: Triggers manual reconciliation recalculation.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import PlainTextResponse

from src.backend.api.v1.schemas.whatsapp_schemas import (
    DailyReconciliationResponse,
    MetaWebhookPayload,
    WebhookIngestResponse,
    WhatsAppMessageFeedResponse,
)
from src.backend.workers.whatsapp_parser import (
    get_message_store,
    get_whatsapp_parser,
    parse_whatsapp_message_task,
)

logger = logging.getLogger("nerolac.api.whatsapp")

whatsapp_router = APIRouter(prefix="/whatsapp", tags=["Module 4: WhatsApp & Recon"])

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "NEROLAC_SECRET_TOKEN_2024")


# ============================================================================
# 1. Meta Webhook Handshake & Ingestion
# ============================================================================


@whatsapp_router.get(
    "/webhook",
    summary="Meta WhatsApp Webhook Handshake Verification",
    response_class=PlainTextResponse,
)
async def verify_meta_webhook(
    request: Request,
) -> Response:
    """Verify Meta Webhook subscription handshake using hub.challenge token."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Meta Webhook verification handshake successful.")
        return PlainTextResponse(content=challenge or "", status_code=status.HTTP_200_OK)

    logger.warning("Meta Webhook verification failed. Invalid token: %s", token)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Verification token mismatch or invalid mode",
    )


@whatsapp_router.post(
    "/webhook",
    response_model=WebhookIngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Meta WhatsApp Webhook Listener (Immediate HTTP 200 OK + Celery Dispatch)",
)
async def ingest_whatsapp_message(
    payload: MetaWebhookPayload | dict[str, Any],
) -> WebhookIngestResponse:
    """Ingest WhatsApp messages, acknowledge Meta with HTTP 200 OK, and enqueue to Celery."""
    raw_data: dict[str, Any] = (
        payload.model_dump(by_alias=True)
        if isinstance(payload, MetaWebhookPayload)
        else dict(payload)
    )

    ingested_ids: list[str] = []
    task_ids: list[str] = []
    entries = raw_data.get("entry", [])

    for entry in entries:
        for change in entry.get("changes", []):
            val = change.get("value", {})
            messages = val.get("messages", [])
            contacts = val.get("contacts", [])
            sender_name = "Sales Officer"
            if contacts and "profile" in contacts[0]:
                sender_name = contacts[0]["profile"].get("name", "Sales Officer")

            for msg in messages:
                waba_id = msg.get("id", f"gen_{os.urandom(6).hex()}")
                sender_phone = msg.get("from", "8801700000000")
                raw_text = msg.get("text", {}).get("body", "")

                ingested_ids.append(waba_id)

                # Dispatch async parsing task to Celery on Redis DB 1
                try:
                    async_result = parse_whatsapp_message_task.delay(
                        raw_id=abs(hash(waba_id)) % 1000000,
                        waba_message_id=waba_id,
                        sender_phone=sender_phone,
                        sender_name=sender_name,
                        raw_text=raw_text,
                    )
                    task_ids.append(str(async_result.id))
                except Exception as exc:
                    logger.warning(
                        "Celery broker unavailable; falling back to synchronous execution: %s",
                        exc,
                    )
                    # Graceful local fallback if standalone Celery worker daemon is idle
                    parser = get_whatsapp_parser()
                    rec = parser.parse_message(
                        raw_id=abs(hash(waba_id)) % 1000000,
                        waba_message_id=waba_id,
                        sender_phone=sender_phone,
                        sender_name=sender_name,
                        raw_text=raw_text,
                    )
                    get_message_store().insert(0, rec)
                    task_ids.append(f"sync_{waba_id}")

    logger.info("Ingested %d WhatsApp messages via Webhook.", len(ingested_ids))
    return WebhookIngestResponse(
        status="ok",
        message="EVENT_RECEIVED",
        waba_message_ids=ingested_ids,
        queued_task_ids=task_ids,
    )


# ============================================================================
# 2. Real-Time Message Stream API
# ============================================================================


@whatsapp_router.get(
    "/messages",
    response_model=WhatsAppMessageFeedResponse,
    summary="Real-Time WhatsApp Message Stream Feed",
)
async def get_whatsapp_messages(
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    depot_id: str | None = Query(None, description="Filter by assigned regional depot"),
    search: str | None = Query(None, description="Search query in text, dealer, or rep"),
) -> WhatsAppMessageFeedResponse:
    """Return sequential WhatsApp message feed with parsed entities and collection amounts."""
    messages = get_message_store()
    filtered = list(messages)

    if status_filter and status_filter != "ALL":
        filtered = [m for m in filtered if m.status == status_filter]

    if depot_id and depot_id != "ALL":
        filtered = [m for m in filtered if m.dealer and m.dealer.depot_id == depot_id]

    if search:
        q = search.lower()
        filtered = [
            m
            for m in filtered
            if q in m.raw_text.lower()
            or q in m.sender_name.lower()
            or (
                m.dealer and (q in m.dealer.trade_name.lower() or q in m.dealer.dealer_code.lower())
            )
        ]

    total_msgs = len(messages)
    parsed_count = sum(1 for m in messages if m.status == "PARSED")
    exception_count = sum(1 for m in messages if m.status in ("EXCEPTION", "NEEDS_REVIEW"))
    total_sales = sum(m.total_sales_bdt for m in messages)
    total_colls = sum(m.total_collection_bdt for m in messages)

    return WhatsAppMessageFeedResponse(
        total_messages_today=total_msgs,
        parsed_count=parsed_count,
        exception_count=exception_count,
        total_reported_sales_bdt=round(total_sales, 2),
        total_collections_bdt=round(total_colls, 2),
        messages=filtered,
    )


# ============================================================================
# 3. 7:00 PM SAP Daily Reconciliation API
# ============================================================================


@whatsapp_router.get(
    "/reconciliation",
    response_model=DailyReconciliationResponse,
    summary="7:00 PM SAP Daily Reconciliation & Top-10 Exceptions",
)
async def get_daily_reconciliation(
    recon_date: str | None = Query(None, description="Reconciliation Date (YYYY-MM-DD)"),
) -> DailyReconciliationResponse:
    """Return 7:00 PM daily reconciliation audit comparing WhatsApp vs. SAP invoicing."""
    from src.backend.analytics.daily_reconciliation import get_daily_reconciler

    engine = get_daily_reconciler()
    return await engine.execute_reconciliation(recon_date=recon_date)


@whatsapp_router.post(
    "/reconciliation/run",
    response_model=DailyReconciliationResponse,
    summary="Manually Trigger 7:00 PM Daily Reconciliation Engine",
)
async def trigger_daily_reconciliation(
    recon_date: str | None = Query(None, description="Reconciliation Date (YYYY-MM-DD)"),
) -> DailyReconciliationResponse:
    """Force execution of 7:00 PM daily reconciliation engine, clearing cache."""
    from datetime import datetime, timezone

    from src.backend.analytics.daily_reconciliation import get_daily_reconciler

    engine = get_daily_reconciler()
    # Invalidate existing cache
    date_str = recon_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await engine.cache_manager.delete(f"dash:whatsapp:recon:{date_str}")
    return await engine.execute_reconciliation(recon_date=date_str)
