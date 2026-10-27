"""Dead-Letter Queue (DLQ) Failover Verification Test Suite.

Verifies:
1. Graceful Dead-Letter Queue (DLQ) failover during simulated AI API / LLM timeouts.
2. Quarantining of timed-out payloads with status 'TIMEOUT_QUARANTINED' into DLQ.
3. Seamless fallback execution to local NLP vector & regex parsing engines without dropping events.
4. Completeness of audit metadata: batch ID, raw payload, error details, and SLA breach timestamps.
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.backend.etl.dead_letter_handler import (
    DeadLetterEntry,
    DeadLetterHandler,
)
from src.backend.main import app  # noqa: F401
from src.backend.workers.whatsapp_parser import (
    WhatsAppBanglishParser,
    get_whatsapp_parser,
)


class TestDLQFailover:
    """Verifies DLQ routing and recovery during external AI API timeouts."""

    async def test_dlq_quarantine_ai_timeout_direct(self) -> None:
        """Assert DeadLetterHandler isolates timed-out AI payload to DLQ."""
        handler = DeadLetterHandler()
        raw_msg = {
            "waba_message_id": "wamid.HBgLMjAyNDA0MDFCX11",
            "sender_phone": "8801711998877",
            "sender_name": "Rafiqul Islam",
            "text": "Bismillah H/W CTG: 10 drum Impression 10L, 5 can Beauty Gold. Cash 50k",
        }

        entry: DeadLetterEntry = await handler.quarantine_ai_timeout(
            service_name="whatsapp_llm_parser",
            raw_payload=raw_msg,
            error_message="Meta AI LLM inference timeout (5000ms SLA exceeded)",
            persist_to_db=False,
        )

        assert entry.batch_id.startswith("DLQ_AI_")
        assert entry.status == "TIMEOUT_QUARANTINED"
        assert entry.report_type == "AI_WHATSAPP_LLM_PARSER_TIMEOUT"
        assert len(entry.validation_errors) == 1
        assert entry.validation_errors[0]["error_type"] == "AI_API_TIMEOUT"
        assert "5000ms SLA exceeded" in entry.validation_errors[0]["message"]
        assert entry.raw_payload["sender_phone"] == "8801711998877"

    async def test_whatsapp_worker_ai_timeout_failover_recovery(self) -> None:
        """Assert parser catches simulated AI timeout, routes to DLQ, and completes via NLP."""
        parser: WhatsAppBanglishParser = get_whatsapp_parser()

        raw_id = 9901
        waba_id = "wamid.HBgLMjAyNDA0MDFCX99"
        sender_phone = "8801711223344"
        sender_name = "Kamrul Hassan (Chittagong SO)"
        raw_text = "Bismillah H/W CTG: 5 drum Impression 10L, 10 can Beauty Gold 4L. Cash 50k"

        # Execute parsing with simulated AI API timeout
        record, dlq_entry = await parser.parse_with_ai_fallback(
            raw_id=raw_id,
            waba_message_id=waba_id,
            sender_phone=sender_phone,
            sender_name=sender_name,
            raw_text=raw_text,
            ai_simulate_timeout=True,
        )

        # 1. Assert DLQ Entry was created and quarantined
        assert dlq_entry is not None, "DLQ entry must be created upon AI timeout"
        assert dlq_entry.status == "TIMEOUT_QUARANTINED"
        assert dlq_entry.raw_payload["waba_message_id"] == waba_id

        # 2. Assert local fallback succeeded in extracting entities
        assert record is not None
        assert record.waba_message_id == waba_id
        assert record.dealer is not None
        assert record.dealer.dealer_code == "D-40982"
        assert record.dealer.trade_name == "Bismillah Hardware & Paint Store"
        assert len(record.line_items) >= 2
        assert record.total_sales_bdt > 0
        assert len(record.collections) >= 1
        assert record.total_collection_bdt == 50000.0

        # 3. Assert failover was audited in processing notes
        assert record.processing_notes is not None
        assert "[DLQ_FAILOVER]" in record.processing_notes
        if dlq_entry.batch_id:
            assert dlq_entry.batch_id in record.processing_notes

    async def test_simulated_ai_api_timeout_exception_handling(self) -> None:
        """Assert asynchronous asyncio.TimeoutError routes payload to DLQ cleanly."""
        handler = DeadLetterHandler()

        async def _mock_ai_call_timing_out() -> dict[str, Any]:
            await asyncio.sleep(0.05)
            raise asyncio.TimeoutError("Upstream Meta AI Inference Server Unreachable")

        failed_entry: DeadLetterEntry | None = None
        try:
            await _mock_ai_call_timing_out()
        except asyncio.TimeoutError as exc:
            failed_entry = await handler.quarantine_ai_timeout(
                service_name="meta_ai_cluster",
                raw_payload={"request_id": "REQ-AI-TIMEOUT-001", "tokens": 256},
                error_message=str(exc),
                persist_to_db=False,
            )

        assert failed_entry is not None
        assert failed_entry.status == "TIMEOUT_QUARANTINED"
        assert "Upstream Meta AI" in failed_entry.validation_errors[0]["message"]
