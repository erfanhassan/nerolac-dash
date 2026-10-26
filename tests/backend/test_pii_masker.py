"""Unit tests for PII Redaction Middleware and Scrubber.

Validates 100% masking of synthetic:
- Bangladeshi phone numbers (+880..., 880..., 01...)
- National ID numbers (10-digit Smart NID, 13-digit NID, 17-digit NID)
- Bank accounts and credit cards
- LLM context windows and logging formatter
"""

from __future__ import annotations

import io
import logging

import pytest

from src.backend.middleware.pii_masker import (
    REDACTED_BANK_TAG,
    REDACTED_NID_TAG,
    REDACTED_PHONE_TAG,
    PIIRedactingFormatter,
    mask_dict,
    mask_llm_context,
    mask_pii,
)


class TestPIIMasker:
    """Comprehensive test suite ensuring 100% redaction of Bangladeshi PII."""

    @pytest.mark.parametrize(
        "synthetic_phone",
        [
            "+8801712345678",
            "+880 1712-345678",
            "+880-1812-345678",
            "+880 1912 345678",
            "8801712345678",
            "8801812345678",
            "01712345678",
            "01812-345678",
            "01912 345678",
            "01612345678",
            "01512345678",
            "01312345678",
            "01412345678",
        ],
    )
    def test_bangladeshi_phone_number_masking(self, synthetic_phone: str) -> None:
        raw_text = f"Dealer contact number is {synthetic_phone} for dispatch confirmation."
        masked_text = mask_pii(raw_text)

        assert synthetic_phone not in masked_text
        assert REDACTED_PHONE_TAG in masked_text

    @pytest.mark.parametrize(
        "synthetic_nid,description",
        [
            ("19851234567890123", "17-digit birth-year NID"),
            ("19929876543210987", "17-digit birth-year NID"),
            ("20011234567890123", "17-digit modern birth-year NID"),
            ("1234567890123", "13-digit legacy NID"),
            ("9876543210123", "13-digit legacy NID"),
            ("NID: 1234567890", "10-digit Smart NID with keyword"),
            ("National ID: 9876543210", "10-digit Smart NID with keyword"),
            ("Smart Card: 5544332211", "10-digit Smart NID with keyword"),
        ],
    )
    def test_national_id_masking(self, synthetic_nid: str, description: str) -> None:
        raw_text = f"Dealer KYC verification document: {synthetic_nid} submitted."
        masked_text = mask_pii(raw_text)

        # Extract only digits from test NID to ensure no digit sequence leaked
        digits = "".join(filter(str.isdigit, synthetic_nid))
        assert digits not in masked_text
        assert REDACTED_NID_TAG in masked_text

    @pytest.mark.parametrize(
        "synthetic_bank_info",
        [
            "A/C: 1234567890123",
            "Account: 9876543210123",
            "Bank A/C: 1122334455667",
            "123-456-7890123",
            "1234-5678-90123",
            "4111-2222-3333-4444",
            "5500 0000 0000 1234",
        ],
    )
    def test_bank_account_and_card_masking(self, synthetic_bank_info: str) -> None:
        raw_text = f"Payment disbursement initiated to {synthetic_bank_info} for dealer incentive."
        masked_text = mask_pii(raw_text)

        digits = "".join(filter(str.isdigit, synthetic_bank_info))
        assert digits not in masked_text
        assert REDACTED_BANK_TAG in masked_text

    def test_composite_pii_string_complete_redaction(self) -> None:
        composite_input = (
            "Dealer Rafiqul Islam (Phone: +880 1712-345678, NID: 19881234567890123) "
            "placed order ORD-7821. Remit incentive to Bank A/C: 9876543210123."
        )
        masked = mask_pii(composite_input)

        # Assert 100% absence of raw PII
        assert "+880 1712-345678" not in masked
        assert "19881234567890123" not in masked
        assert "9876543210123" not in masked

        # Assert corresponding redaction tokens present
        assert REDACTED_PHONE_TAG in masked
        assert REDACTED_NID_TAG in masked
        assert REDACTED_BANK_TAG in masked

    def test_nested_data_structure_masking(self) -> None:
        payload = {
            "dealer_name": "Meghna Paints",
            "contacts": [
                {"role": "Primary", "phone": "+8801812345678"},
                {"role": "Accounts", "phone": "01712-998877"},
            ],
            "financials": {
                "nid": "19901234567890123",
                "disbursement_account": "Account: 8877665544332",
            },
        }

        masked_payload = mask_dict(payload)

        # Phone numbers masked
        assert masked_payload["contacts"][0]["phone"] == REDACTED_PHONE_TAG
        assert masked_payload["contacts"][1]["phone"] == REDACTED_PHONE_TAG

        # Financials masked
        assert "19901234567890123" not in masked_payload["financials"]["nid"]
        assert REDACTED_NID_TAG in masked_payload["financials"]["nid"]
        assert "8877665544332" not in masked_payload["financials"]["disbursement_account"]
        assert REDACTED_BANK_TAG in masked_payload["financials"]["disbursement_account"]

    def test_llm_context_window_scrubbing(self) -> None:
        messages = [
            {
                "role": "system",
                "content": "You are Nerolac Operations Assistant in Dhaka, Bangladesh.",
            },
            {
                "role": "user",
                "content": (
                    "Verify customer +8801711223344 with NID 19871234567890123 "
                    "and A/C 123456789012."
                ),
            },
        ]

        scrubbed = mask_llm_context(messages)

        user_content = scrubbed[1]["content"]
        assert "+8801711223344" not in user_content
        assert "19871234567890123" not in user_content
        assert "123456789012" not in user_content
        assert REDACTED_PHONE_TAG in user_content
        assert REDACTED_NID_TAG in user_content
        assert REDACTED_BANK_TAG in user_content

    def test_logging_formatter_pii_redaction(self) -> None:
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        formatter = PIIRedactingFormatter("%(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        test_logger = logging.getLogger("test.pii.logger")
        test_logger.setLevel(logging.INFO)
        test_logger.addHandler(handler)

        test_logger.info("Dealer phone is %s with NID %s", "+8801712345678", "19951234567890123")

        output = log_stream.getvalue()
        assert "+8801712345678" not in output
        assert "19951234567890123" not in output
        assert REDACTED_PHONE_TAG in output
        assert REDACTED_NID_TAG in output
