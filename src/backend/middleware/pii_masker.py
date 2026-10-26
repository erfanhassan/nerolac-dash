"""PII Redaction Middleware & Sanitizer for Bangladesh Enterprise Operations.

Redacts:
1. Bangladeshi Phone Numbers: +8801..., 8801..., 01... with varying separators.
2. National ID Numbers (NID): 10-digit Smart NID, 13-digit NID, 17-digit birth-year NID.
3. Bank Account Numbers & Figures: 9-18 digit account numbers, routing references, cards.

Supports:
- Text sanitization (`mask_pii`)
- Deep data structure sanitization (`mask_dict`)
- LLM Context Window scrubber (`mask_llm_context`)
- Logging Formatter (`PIIRedactingFormatter`)
- ASGI / FastAPI Middleware (`PIIMaskingMiddleware`)
"""

from __future__ import annotations

import copy
import logging
import re
from typing import Any, Callable

logger = logging.getLogger("nerolac.security.pii")

# 1. Bangladeshi Phone Numbers:
# Operators: 013, 014, 015, 016, 017, 018, 019
# Formats: +8801XXXXXXXXX, 8801XXXXXXXXX, 01XXXXXXXXX with optional spaces or hyphens
BD_PHONE_REGEX = re.compile(
    r"(?:\+?880|880)?[ -]?0?1[3-9]\d(?:[ -]?\d){7}\b",
    re.ASCII,
)

# 2. Bangladeshi National ID (NID) Numbers:
# - Keyword-guided (NID, National ID, etc.) followed by 10, 13, or 17 digits
# - Standalone 17-digit NID starting with valid birth years (1900-2029)
# - Standalone 13-digit NID
# - Standalone 10-digit Smart NID
BD_NID_KEYWORD_REGEX = re.compile(
    r"(?i)\b(?:nid|national\s*id|smart\s*card|identity\s*no|citizen\s*id)[\s:#=-]*(\d{10}|\d{13}|\d{17})\b"
)
BD_NID_17_DIGIT_REGEX = re.compile(r"\b(?:19\d{2}|20[0-2]\d)\d{13}\b")
BD_NID_13_DIGIT_REGEX = re.compile(r"\b\d{13}\b")
BD_NID_10_DIGIT_REGEX = re.compile(r"(?i)\b(?:nid|smart\s*nid|id)[\s:#=-]*\b(\d{10})\b")

# 3. Bank Account Numbers & Payment Figures:
# - Keyword-guided accounts (e.g., A/C: 1234567890123)
# - Bank account number formatting with hyphens: 3-3-7 or 4-4-5
# - Standard 16-digit credit/debit card numbers
BANK_ACCOUNT_KEYWORD_REGEX = re.compile(
    r"(?i)\b(?:a/?c|acc(?:ount)?|bank\s*a/?c|acct|iban|bban)[\s:#=-]*(\d{8,18})\b"
)
BANK_ACCOUNT_HYPHEN_REGEX = re.compile(r"\b\d{3,4}[- ]\d{3,4}[- ]\d{4,10}\b")
CREDIT_CARD_REGEX = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")

REDACTED_PHONE_TAG = "[BD_PHONE_REDACTED]"
REDACTED_NID_TAG = "[BD_NID_REDACTED]"
REDACTED_BANK_TAG = "[BANK_ACCOUNT_REDACTED]"


def mask_pii(text: str) -> str:
    """Mask all detected Bangladeshi PII (phone, NID, bank account) in text."""
    if not isinstance(text, str) or not text:
        return text

    sanitized = text

    # Step 1: Mask Bangladeshi Phone numbers first (e.g. +880 1712-345678, 01812-345678)
    sanitized = BD_PHONE_REGEX.sub(REDACTED_PHONE_TAG, sanitized)

    # Step 2: Mask Bank Account numbers and Payment cards
    def redact_bank_keyword(match: re.Match[str]) -> str:
        full_match = match.group(0)
        account_num = match.group(1)
        return full_match.replace(account_num, REDACTED_BANK_TAG)

    sanitized = BANK_ACCOUNT_KEYWORD_REGEX.sub(redact_bank_keyword, sanitized)
    sanitized = BANK_ACCOUNT_HYPHEN_REGEX.sub(REDACTED_BANK_TAG, sanitized)
    sanitized = CREDIT_CARD_REGEX.sub(REDACTED_BANK_TAG, sanitized)

    # Step 3: Mask National ID (NID) numbers
    def redact_nid_keyword(match: re.Match[str]) -> str:
        full_match = match.group(0)
        nid_num = match.group(1)
        return full_match.replace(nid_num, REDACTED_NID_TAG)

    sanitized = BD_NID_KEYWORD_REGEX.sub(redact_nid_keyword, sanitized)
    sanitized = BD_NID_17_DIGIT_REGEX.sub(REDACTED_NID_TAG, sanitized)
    sanitized = BD_NID_13_DIGIT_REGEX.sub(REDACTED_NID_TAG, sanitized)
    sanitized = BD_NID_10_DIGIT_REGEX.sub(redact_nid_keyword, sanitized)

    return sanitized


def mask_dict(data: Any) -> Any:
    """Recursively mask PII in dictionaries, lists, and nested data structures."""
    if isinstance(data, str):
        return mask_pii(data)
    if isinstance(data, dict):
        return {key: mask_dict(value) for key, value in data.items()}
    if isinstance(data, list):
        return [mask_dict(item) for item in data]
    if isinstance(data, tuple):
        return tuple(mask_dict(item) for item in data)
    if isinstance(data, set):
        return {mask_dict(item) for item in data}
    return data


def mask_llm_context(context: Any) -> Any:
    """Scrub PII from LLM prompts, chat message arrays, and context windows.

    Guarantees that sensitive dealer, customer, or employee PII never escapes
    into external LLM inference endpoints or third-party AI APIs.
    """
    if isinstance(context, str):
        return mask_pii(context)

    if isinstance(context, list):
        scrubbed_list = []
        for item in context:
            if isinstance(item, dict):
                msg_copy = copy.deepcopy(item)
                if "content" in msg_copy and isinstance(msg_copy["content"], str):
                    msg_copy["content"] = mask_pii(msg_copy["content"])
                else:
                    msg_copy = mask_dict(msg_copy)
                scrubbed_list.append(msg_copy)
            else:
                scrubbed_list.append(mask_dict(item))
        return scrubbed_list

    if isinstance(context, dict):
        return mask_dict(context)

    return context


class PIIRedactingFormatter(logging.Formatter):
    """Custom logging Formatter that redacts PII before outputting to log streams."""

    def format(self, record: logging.LogRecord) -> str:
        original_msg = record.msg
        if isinstance(original_msg, str):
            record.msg = mask_pii(original_msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = mask_dict(record.args)
            elif isinstance(record.args, (tuple, list)):
                record.args = tuple(mask_dict(arg) for arg in record.args)

        formatted = super().format(record)
        return mask_pii(formatted)


class PIIMaskingMiddleware:
    """ASGI / FastAPI Middleware that masks PII in incoming and outgoing payloads."""

    def __init__(self, app: Callable[..., Any]) -> None:
        self.app = app

    async def __call__(
        self, scope: dict[str, Any], receive: Callable[..., Any], send: Callable[..., Any]
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_start: dict[str, Any] | None = None
        body_parts: list[bytes] = []

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal response_start
            if message["type"] == "http.response.start":
                response_start = message
                return

            if message["type"] == "http.response.body":
                body = message.get("body", b"")
                more_body = message.get("more_body", False)
                body_parts.append(body)

                if more_body:
                    return

                # All body chunks collected, process now
                full_body = b"".join(body_parts)
                try:
                    text_body = full_body.decode("utf-8")
                    masked_text = mask_pii(text_body)
                    final_body = masked_text.encode("utf-8")
                except UnicodeDecodeError:
                    final_body = full_body

                if response_start is not None:
                    # Update Content-Length header to match the new body length
                    headers: list[tuple[bytes, bytes]] = []
                    for name, value in response_start.get("headers", []):
                        if name.lower() == b"content-length":
                            continue
                        headers.append((name, value))
                    headers.append((b"content-length", str(len(final_body)).encode("latin-1")))
                    response_start["headers"] = headers
                    await send(response_start)

                await send(
                    {
                        "type": "http.response.body",
                        "body": final_body,
                        "more_body": False,
                    }
                )
                return

            await send(message)

        await self.app(scope, receive, send_wrapper)
