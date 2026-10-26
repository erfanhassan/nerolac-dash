"""Unit and Integration Test Suite for WhatsApp Parser & 7:00 PM SAP Reconciliation.

Validates:
1. Banglish abbreviation expansion & vector representation.
2. Vector + RapidFuzz hybrid dealer resolution ("Bismillah H/W CTG" -> "D-40982").
3. SKU line item & volume/revenue extraction.
4. Cash, cheque, and MFS payment collection parsing.
5. Meta WhatsApp Webhook handshake and immediate HTTP 200 OK ingestion.
6. 7:00 PM Daily Reconciliation engine and top-10 exception ranking.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.backend.analytics.daily_reconciliation import DailyReconciliationEngine
from src.backend.main import app
from src.backend.workers.whatsapp_parser import (
    WhatsAppBanglishParser,
    generate_character_ngram_vector,
)


@pytest.fixture
def parser() -> WhatsAppBanglishParser:
    """Instantiate fresh WhatsAppBanglishParser."""
    return WhatsAppBanglishParser()


class TestWhatsAppBanglishParser:
    """Test suite for Banglish NLP, vector fuzzy matching, and entity extraction."""

    def test_character_ngram_vector_generation(self) -> None:
        """Assert vector embedding produces normalized 64-dim L2 vector."""
        vec = generate_character_ngram_vector("Bismillah Hardware Chittagong", dim=64)
        assert len(vec) == 64
        # Norm should be approximately 1.0
        norm = sum(x * x for x in vec) ** 0.5
        assert 0.99 <= norm <= 1.01

    def test_banglish_abbreviation_expansion(self, parser: WhatsAppBanglishParser) -> None:
        """Verify regional abbreviations expand correctly to standard vocabulary."""
        text = "bismillah h/w ctg cash joma 50k"
        normalized = parser.normalize_banglish(text)
        assert "hardware" in normalized
        assert "chittagong" in normalized
        assert "collected" in normalized

    def test_vector_fuzzy_dealer_resolution_bismillah(
        self, parser: WhatsAppBanglishParser
    ) -> None:
        """Assert 'Bismillah H/W CTG' resolves to SAP Dealer D-40982 with high confidence."""
        query = "Bismillah H/W CTG"
        dealer = parser.resolve_dealer(query)

        assert dealer is not None
        assert dealer.dealer_code == "D-40982"
        assert dealer.trade_name == "Bismillah Hardware & Paint Store"
        assert dealer.depot_id == "DEPOT_02"
        assert dealer.depot_name == "Chittagong Port Depot"
        assert dealer.confidence_score >= 0.85
        assert dealer.resolution_method == "VECTOR_RAPIDFUZZ_HYBRID"

    def test_vector_fuzzy_dealer_resolution_other_depots(
        self, parser: WhatsAppBanglishParser
    ) -> None:
        """Assert fuzzy and vector matching across other regional hubs."""
        # 1. Dhaka North
        d_dhaka = parser.resolve_dealer("Rahman Ent DHK")
        assert d_dhaka is not None
        assert d_dhaka.dealer_code == "D-10245"
        assert d_dhaka.depot_id == "DEPOT_01"

        # 2. Bogura Town
        d_bogura = parser.resolve_dealer("Bhai Bhai Traders Bogura")
        assert d_bogura is not None
        assert d_bogura.dealer_code == "D-30419"
        assert d_bogura.depot_id == "DEPOT_03"

        # 3. Sylhet Sadar
        d_sylhet = parser.resolve_dealer("Haji Paint House Sylhet")
        assert d_sylhet is not None
        assert d_sylhet.dealer_code == "D-50811"
        assert d_sylhet.depot_id == "DEPOT_04"

        # 4. Rajshahi
        d_raj = parser.resolve_dealer("Padma H/W Raj")
        assert d_raj is not None
        assert d_raj.dealer_code == "D-70334"
        assert d_raj.depot_id == "DEPOT_06"

    def test_exact_sap_code_matching(self, parser: WhatsAppBanglishParser) -> None:
        """Assert direct SAP Dealer Code lookup returns 1.0 confidence."""
        dealer = parser.resolve_dealer("Dealer update for D-60122 Khulna")
        assert dealer is not None
        assert dealer.dealer_code == "D-60122"
        assert dealer.trade_name == "Khan & Sons Decor Khulna"
        assert dealer.confidence_score == 1.0
        assert dealer.resolution_method == "EXACT_CODE"

    def test_sku_and_quantity_extraction(self, parser: WhatsAppBanglishParser) -> None:
        """Assert extraction of multiple paint SKUs, units, liters, and revenues."""
        raw_text = (
            "Bismillah H/W CTG: 5 drum Impression 10L, 10 can Beauty Gold 4L. Cash collect 50k"
        )
        line_items = parser.extract_skus(raw_text)

        assert len(line_items) == 2

        # Item 1: Impressions 10L
        imp = next(item for item in line_items if item.sku_id == "SKU_DEC_001")
        assert imp.quantity == 5.0
        assert imp.liters == 50.0
        assert imp.unit_price_bdt == 4250.0
        assert imp.total_value_bdt == 21250.0

        # Item 2: Beauty Gold 4L
        bg = next(item for item in line_items if item.sku_id == "SKU_DEC_002")
        assert bg.quantity == 10.0
        assert bg.liters == 40.0
        assert bg.unit_price_bdt == 1850.0
        assert bg.total_value_bdt == 18500.0

    def test_collection_parsing_varieties(self, parser: WhatsAppBanglishParser) -> None:
        """Assert extraction of Cash, Cheque, and bKash collections."""
        # Cash
        c1 = parser.extract_collections("Cash collect 50k")[0]
        assert c1.payment_method == "CASH"
        assert c1.amount_bdt == 50000.0

        # Cheque
        c2 = parser.extract_collections("Payment via Cheque 1.2 Lac")[0]
        assert c2.payment_method == "CHEQUE"
        assert c2.amount_bdt == 120000.0

        # bKash
        c3 = parser.extract_collections("bKash 35,000 paid")[0]
        assert c3.payment_method == "BKASH"
        assert c3.amount_bdt == 35000.0

    def test_full_message_parsing_pipeline(self, parser: WhatsAppBanglishParser) -> None:
        """Assert end-to-end parsing of field sales update."""
        raw = "Bismillah H/W CTG: 5 drum Impression 10L, 10 can Beauty Gold 4L. Cash collect 50k"
        record = parser.parse_message(
            raw_id=9901,
            waba_message_id="wamid.TEST9901",
            sender_phone="8801711223344",
            sender_name="Kamrul Hassan",
            raw_text=raw,
        )

        assert record.status == "PARSED"
        assert record.dealer is not None
        assert record.dealer.dealer_code == "D-40982"
        assert len(record.line_items) == 2
        assert record.total_sales_bdt == 39750.0  # 21,250 + 18,500
        assert len(record.collections) == 1
        assert record.total_collection_bdt == 50000.0


class TestWhatsAppWebhookAPI:
    """Integration test suite for Meta Webhook listener and 7:00 PM reconciliation."""

    @pytest.mark.asyncio
    async def test_meta_webhook_handshake_success(self) -> None:
        """Verify Meta Webhook GET handshake verification succeeds with HTTP 200."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/whatsapp/webhook",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "NEROLAC_SECRET_TOKEN_2024",
                    "hub.challenge": "CHALLENGE_ACCEPTED_12345",
                },
            )
            assert resp.status_code == 200
            assert resp.text == "CHALLENGE_ACCEPTED_12345"

    @pytest.mark.asyncio
    async def test_meta_webhook_handshake_invalid_token(self) -> None:
        """Verify invalid token is rejected with HTTP 403 Forbidden."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/whatsapp/webhook",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "WRONG_TOKEN",
                    "hub.challenge": "CHALLENGE_123",
                },
            )
            assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_meta_webhook_post_immediate_200_ok(self) -> None:
        """Verify incoming Meta WhatsApp POST payload returns immediate HTTP 200 OK."""
        transport = ASGITransport(app=app)
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WABA_001",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "contacts": [
                                    {
                                        "profile": {"name": "Kamrul Hassan"},
                                        "wa_id": "8801711223344",
                                    }
                                ],
                                "messages": [
                                    {
                                        "from": "8801711223344",
                                        "id": "wamid.TEST_HOOK_99",
                                        "timestamp": "1711886400",
                                        "text": {
                                            "body": (
                                                "Bismillah H/W CTG: 5 drum Impression 10L. Cash 20k"
                                            )
                                        },
                                        "type": "text",
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/whatsapp/webhook", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["message"] == "EVENT_RECEIVED"
            assert "wamid.TEST_HOOK_99" in data["waba_message_ids"]

    @pytest.mark.asyncio
    async def test_whatsapp_messages_stream_endpoint(self) -> None:
        """Verify GET /api/v1/whatsapp/messages returns live feed cards and KPIs."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/whatsapp/messages")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_messages_today"] >= 8
            assert data["total_reported_sales_bdt"] > 0
            assert len(data["messages"]) >= 8

            # Check Bismillah record
            bismillah_msg = next(
                m
                for m in data["messages"]
                if m.get("dealer") and m["dealer"]["dealer_code"] == "D-40982"
            )
            assert bismillah_msg["dealer"]["trade_name"] == "Bismillah Hardware & Paint Store"
            assert bismillah_msg["total_sales_bdt"] == 39750.0

    @pytest.mark.asyncio
    async def test_7pm_daily_reconciliation_engine(self) -> None:
        """Verify 7:00 PM reconciliation calculation, top-10 exceptions, and depot breakdown."""
        engine = DailyReconciliationEngine()
        recon = await engine.execute_reconciliation("2024-04-01")

        assert recon.reconciliation_date == "2024-04-01"
        assert recon.reconciliation_time_bst == "19:00:00 BST"
        assert recon.total_whatsapp_sales_bdt > 0
        assert recon.total_sap_invoiced_bdt > 0
        assert recon.overall_match_rate_pct > 0
        assert len(recon.top_10_exceptions) > 0
        assert len(recon.top_10_exceptions) <= 10

        # Top exception must be ranked #1 with highest absolute variance
        top1 = recon.top_10_exceptions[0]
        assert top1.rank == 1
        assert abs(top1.variance_bdt) > 0
        assert top1.exception_type in ("OVER_REPORTED", "UNDER_REPORTED", "MISSING_WHATSAPP_REPORT")

        # Assert all 8 depots are covered
        assert len(recon.depot_summaries) == 8
