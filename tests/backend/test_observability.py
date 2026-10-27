"""Test Suite: OpenTelemetry Metrics, Sentry PII Scrubber, and ML Model Drift Monitor.

Verifications:
1. OpenTelemetry metrics endpoint `/metrics` outputs valid Prometheus-formatted data.
2. Metrics capture HTTP duration, DB pool stats, Redis cache hit ratio, and Celery depth.
3. Sentry PII scrubber redacts Bangladeshi NID, phone numbers, bank accounts, and secrets.
4. ML Model Drift Monitor calculates MAPE/RMSE, tracks deviations, and triggers drift alerts.
"""

from __future__ import annotations

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from src.backend.main import app
from src.backend.ml.drift_monitor import (
    DriftSeverity,
    MLModelDriftMonitor,
)
from src.backend.observability.sentry_config import (
    get_grafana_dashboard_json,
    scrub_pii_from_string,
    sentry_before_send,
)
from src.backend.observability.telemetry import (
    get_telemetry_manager,
    record_http_request,
)


@pytest.mark.asyncio
async def test_metrics_endpoint_outputs_prometheus_format() -> None:
    """Verify OpenTelemetry metrics endpoint /metrics outputs Prometheus-formatted data."""
    # Seed telemetry with known metric events
    telemetry = get_telemetry_manager()
    record_http_request(
        method="GET",
        endpoint="/api/v1/finance/actuals",
        status_code=200,
        duration_seconds=0.042,
    )
    record_http_request(
        method="POST",
        endpoint="/api/v1/whatsapp/webhook",
        status_code=200,
        duration_seconds=0.015,
    )

    telemetry.update_db_pool_stats(
        pool_type="master", active=4, idle=16, overflow=0, max_capacity=20
    )
    telemetry.update_db_pool_stats(
        pool_type="read_replica", active=6, idle=24, overflow=0, max_capacity=30
    )

    telemetry.record_cache_hit("db0_query_cache")
    telemetry.record_cache_hit("db0_query_cache")
    telemetry.record_cache_miss("db0_query_cache")

    telemetry.update_celery_queue_depth("celery_default", 5)
    telemetry.update_ml_metrics(depot_id="CTG", sku_id="N-101", mape=11.4, rmse=0.85)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    text = response.text

    # Assert required Prometheus metrics exist in payload
    assert "nerolac_http_request_duration_seconds" in text
    assert "nerolac_http_requests_total" in text
    assert "nerolac_db_pool_connections" in text
    assert "nerolac_db_pool_utilization_ratio" in text
    assert "nerolac_redis_cache_hits_total" in text
    assert "nerolac_redis_cache_misses_total" in text
    assert "nerolac_redis_cache_hit_ratio" in text
    assert "nerolac_celery_queue_depth" in text
    assert "nerolac_ml_forecast_mape" in text
    assert "nerolac_ml_forecast_rmse" in text

    # Assert values
    assert 'endpoint="/api/v1/finance/actuals"' in text
    assert 'pool_type="master"' in text
    assert 'pool_type="read_replica"' in text


def test_sentry_pii_scrubber() -> None:
    """Verify Bangladeshi NID, phone numbers, bank accounts, and secrets are redacted."""
    raw_text = (
        "Customer NID is 19922612345678901 with mobile 01712345678 and international "
        "+8801812345678. Bank account 123456789012345."
    )
    scrubbed = scrub_pii_from_string(raw_text)
    assert "19922612345678901" not in scrubbed
    assert "[REDACTED_NID]" in scrubbed
    assert "01712345678" not in scrubbed
    assert "+8801812345678" not in scrubbed
    assert "[REDACTED_PHONE]" in scrubbed
    assert "123456789012345" not in scrubbed
    assert "[REDACTED_BANK_ACC]" in scrubbed

    # Test event processor dictionary scrubbing
    event = {
        "request": {
            "headers": {
                "Authorization": "Bearer super-secret-jwt-token",
                "User-Agent": "Mozilla/5.0",
            },
            "data": "Customer phone: 01987654321",
        },
        "breadcrumbs": {
            "values": [{"message": "Queried dealer NID 9876543210123"}],
        },
    }
    processed = sentry_before_send(event, None)
    assert processed is not None
    assert processed["request"]["headers"]["Authorization"] == "[REDACTED_SECRET]"
    assert "[REDACTED_PHONE]" in processed["request"]["data"]
    assert "[REDACTED_NID]" in processed["breadcrumbs"]["values"][0]["message"]


def test_grafana_dashboard_json_validity() -> None:
    """Verify Grafana Dashboard JSON contains all required observability panels."""
    dashboard = get_grafana_dashboard_json()
    assert dashboard["title"] == "Nerolac Operations Dashboard - Production Observability"
    assert dashboard["uid"] == "nerolac-ops-observability"

    panel_titles = [p.get("title") for p in dashboard.get("panels", [])]
    assert any("HTTP Request Latency" in t for t in panel_titles)
    assert any("Database Connection Pool" in t or "PostgreSQL" in t for t in panel_titles)
    assert any("Redis Cache Hit Ratio" in t for t in panel_titles)
    assert any("Celery" in t for t in panel_titles)
    assert any("Ensemble Demand Forecast MAPE" in t for t in panel_titles)


def test_ml_model_drift_monitor() -> None:
    """Verify MAPE/RMSE calculation, alert triggers, and drift severity escalation."""
    monitor = MLModelDriftMonitor(baseline_mape=12.0, warning_mape=15.0, critical_mape=25.0)

    # 1. Healthy performance below baseline (MAPE ~ 5%)
    actuals = np.array([100.0, 150.0, 200.0, 80.0, 120.0])
    predictions = np.array([105.0, 142.0, 195.0, 82.0, 125.0])

    mape = monitor.calculate_mape(actuals, predictions)
    rmse = monitor.calculate_rmse(actuals, predictions)
    assert 3.0 < mape < 8.0
    assert 4.0 < rmse < 8.0

    # Record healthy predictions
    for act, pred in zip(actuals, predictions):
        monitor.record_forecast_actual(
            depot_id="DHK", sku_id="SKU-EXT-1", actual=act, predicted=pred
        )

    result_normal = monitor.evaluate_drift(
        depot_id="DHK", sku_id="SKU-EXT-1", baseline_rmse=10.0
    )
    assert result_normal.severity == DriftSeverity.NORMAL
    assert not result_normal.is_drift_detected

    # 2. Severe drift (MAPE > 30%)
    drift_monitor = MLModelDriftMonitor(baseline_mape=12.0, warning_mape=15.0, critical_mape=25.0)
    drifted_actuals = [100.0, 150.0, 200.0, 80.0, 120.0]
    drifted_predictions = [140.0, 210.0, 280.0, 120.0, 180.0]  # ~40-50% error

    for act, pred in zip(drifted_actuals, drifted_predictions):
        drift_monitor.record_forecast_actual(
            depot_id="BOG", sku_id="SKU-INT-2", actual=act, predicted=pred
        )

    result_critical = drift_monitor.evaluate_drift(
        depot_id="BOG", sku_id="SKU-INT-2", baseline_rmse=5.0
    )
    assert result_critical.severity == DriftSeverity.CRITICAL
    assert result_critical.is_drift_detected
    assert result_critical.current_mape > 25.0
    assert any("CRITICAL DRIFT" in alert for alert in result_critical.alerts)
    assert len(result_critical.recommendations) >= 2
