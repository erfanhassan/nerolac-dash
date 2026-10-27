"""Nerolac Operations Dashboard - Sentry Error Tracking & Grafana Observability.

Architecture:
1. Production Sentry SDK configuration with automatic PII scrubbing (Bangladesh NID,
   mobile phone numbers, bank accounts) complying with data sovereignty laws.
2. Integrations: FastAPI, SQLAlchemy, Redis, and Celery.
3. Grafana Dashboard JSON loader and exporter for Prometheus observability.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

logger = logging.getLogger("nerolac.observability.sentry")

DASHBOARD_JSON_PATH = Path(__file__).resolve().parent / "grafana_dashboard.json"

# Bangladeshi PII regex patterns to scrub prior to Sentry transmission
NID_PATTERN = re.compile(r"\b(?:\d{10}|\d{13}|\d{17})\b")
PHONE_PATTERN = re.compile(r"(?:\+8801[3-9]\d{8}|01[3-9]\d{8})\b")
BANK_ACCOUNT_PATTERN = re.compile(r"\b\d{13,16}\b")


def scrub_pii_from_string(text: str) -> str:
    """Redact Bangladeshi NID, phone numbers, and bank accounts from strings."""
    if not isinstance(text, str):
        return text
    text = NID_PATTERN.sub("[REDACTED_NID]", text)
    text = PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
    text = BANK_ACCOUNT_PATTERN.sub("[REDACTED_BANK_ACC]", text)
    return text


def _scrub_dict_recursively(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively scrub sensitive keys and PII values from dictionaries."""
    sanitized: dict[str, Any] = {}
    sensitive_keys = {"authorization", "token", "password", "secret", "private_key", "cookie"}

    for key, value in data.items():
        if any(sens in key.lower() for sens in sensitive_keys):
            sanitized[key] = "[REDACTED_SECRET]"
        elif isinstance(value, str):
            sanitized[key] = scrub_pii_from_string(value)
        elif isinstance(value, dict):
            sanitized[key] = _scrub_dict_recursively(value)
        elif isinstance(value, list):
            sanitized[key] = [
                scrub_pii_from_string(item)
                if isinstance(item, str)
                else (_scrub_dict_recursively(item) if isinstance(item, dict) else item)
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


def sentry_before_send(
    event: Any, hint: Any = None
) -> Any:
    """Sentry event processor that strips PII before outbound network transmission."""
    try:
        # Scrub request headers and body
        if "request" in event and isinstance(event["request"], dict):
            event["request"] = _scrub_dict_recursively(event["request"])

        # Scrub breadcrumbs
        if "breadcrumbs" in event and isinstance(event["breadcrumbs"], dict):
            values = event["breadcrumbs"].get("values", [])
            for crumb in values:
                if isinstance(crumb, dict) and "message" in crumb and crumb["message"]:
                    crumb["message"] = scrub_pii_from_string(str(crumb["message"]))

        # Scrub extra context
        if "extra" in event and isinstance(event["extra"], dict):
            event["extra"] = _scrub_dict_recursively(event["extra"])

    except Exception as e:
        logger.warning("Error scrubbing PII in Sentry before_send: %s", e)

    return event


def init_sentry(
    dsn: str | None = None,
    environment: str = "production",
    release: str = "nerolac-dash@1.0.0",
    traces_sample_rate: float = 0.2,
) -> bool:
    """Initialize Sentry SDK with production hardening and PII scrubber.

    Returns True if initialized, False if DSN was omitted or mock/disabled.
    """
    effective_dsn = dsn or os.environ.get("SENTRY_DSN")
    if not effective_dsn or effective_dsn.startswith("disabled"):
        logger.info("Sentry DSN not provided or disabled. Skipping remote error transmission.")
        return False

    try:
        sentry_sdk.init(
            dsn=effective_dsn,
            environment=environment,
            release=release,
            traces_sample_rate=traces_sample_rate,
            before_send=sentry_before_send,
            send_default_pii=False,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                RedisIntegration(),
                CeleryIntegration(),
            ],
        )
        logger.info("Sentry SDK successfully initialized for environment: %s", environment)
        return True
    except Exception as e:
        logger.error("Failed to initialize Sentry SDK: %s", e)
        return False


def capture_exception_with_context(
    exc: Exception,
    user_id: str | None = None,
    depot_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Capture exception to Sentry with sanitized regional depot and user context."""
    with sentry_sdk.push_scope() as scope:
        if user_id:
            scope.set_user({"id": user_id})
        if depot_id:
            scope.set_tag("depot_id", depot_id)
        if extra:
            scope.set_extra("context", _scrub_dict_recursively(extra))
        sentry_sdk.capture_exception(exc)


def get_grafana_dashboard_json() -> dict[str, Any]:
    """Load and return the production Grafana Dashboard JSON definition."""
    if DASHBOARD_JSON_PATH.is_file():
        with open(DASHBOARD_JSON_PATH, encoding="utf-8") as f:
            data = json.load(f)
            return dict(data) if isinstance(data, dict) else {}
    return {"title": "Nerolac Operations Dashboard", "panels": []}


def export_grafana_dashboard(target_path: str | Path | None = None) -> str:
    """Export Grafana Dashboard JSON formatted string to disk or stdout."""
    dashboard = get_grafana_dashboard_json()
    formatted = json.dumps(dashboard, indent=2)
    if target_path:
        path = Path(target_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(formatted, encoding="utf-8")
        logger.info("Exported Grafana Dashboard JSON to %s", path)
    return formatted
