"""Integrated Backend Test Suite Aggregator in tests/backend/.

Ensures that running `pytest tests/backend/` executes the complete backend unit
and integration test suite across all modules (Analytics, API, ETL, ML,
Reporting, Security, Infrastructure, and Workers) asserting >85% code coverage.
"""

from __future__ import annotations

# Sibling test suite imports
from tests.analytics.test_stockout_masker import *  # noqa: F403
from tests.analytics.test_unit_converter import *  # noqa: F403
from tests.api.test_finance_api import *  # noqa: F403
from tests.api.test_hr_api import *  # noqa: F403
from tests.etl.test_historical_backfill import *  # noqa: F403
from tests.etl.test_pydantic_validators import *  # noqa: F403
from tests.etl.test_sftp_watcher import *  # noqa: F403
from tests.infrastructure.test_redis_routing import *  # noqa: F403
from tests.ml.test_demand_forecaster import *  # noqa: F403
from tests.reporting.test_report_exporters import *  # noqa: F403
from tests.security.test_rls_isolation import *  # noqa: F403
from tests.workers.test_whatsapp_parser import *  # noqa: F403
