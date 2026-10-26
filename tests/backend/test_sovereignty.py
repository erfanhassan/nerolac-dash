"""Unit tests for Bangladesh Data Sovereignty validation."""

from __future__ import annotations

import pytest

from src.backend.config.settings import (
    DataSovereigntyViolationError,
    Settings,
    is_sovereign_host,
)


class TestDataSovereignty:
    """Test suite ensuring data residency complies with Bangladesh Data Sovereignty."""

    @pytest.mark.parametrize(
        "sovereign_endpoint",
        [
            "localhost",
            "127.0.0.1",
            "10.0.1.15",
            "172.16.5.10",
            "192.168.1.100",
            "db.dhaka.nerolacbd.com",
            "postgres.ctg.nerolacbd.com",
            "redis.plant.nerolacbd.com",
            "postgres.database.gov.bd",
        ],
    )
    def test_approved_sovereign_endpoints(self, sovereign_endpoint: str) -> None:
        assert is_sovereign_host(sovereign_endpoint) is True

    @pytest.mark.parametrize(
        "foreign_endpoint",
        [
            "us-east-1.rds.amazonaws.com",
            "eu-west-1.database.azure.com",
            "ap-southeast-1.gcp.google.com",
            "db.singapore.digitalocean.com",
            "random-foreign-host.com",
        ],
    )
    def test_rejected_foreign_endpoints(self, foreign_endpoint: str) -> None:
        assert is_sovereign_host(foreign_endpoint) is False

    def test_settings_raises_on_foreign_database_host(self) -> None:
        from pydantic import ValidationError

        with pytest.raises((DataSovereigntyViolationError, ValidationError)) as exc_info:
            Settings(
                POSTGRES_HOST="prod-db.us-east-1.rds.amazonaws.com",
                ENFORCE_DATA_SOVEREIGNTY=True,
            )
        assert "Bangladesh Data Sovereignty Violation" in str(exc_info.value)

    def test_settings_raises_on_foreign_redis_host(self) -> None:
        from pydantic import ValidationError

        with pytest.raises((DataSovereigntyViolationError, ValidationError)) as exc_info:
            Settings(
                REDIS_HOST="cache.eu-central-1.amazonaws.com",
                ENFORCE_DATA_SOVEREIGNTY=True,
            )
        assert "Bangladesh Data Sovereignty Violation" in str(exc_info.value)

    def test_settings_raises_on_invalid_region(self) -> None:
        from pydantic import ValidationError

        with pytest.raises((DataSovereigntyViolationError, ValidationError)) as exc_info:
            Settings(
                DATA_RESIDENCY_REGION="US",
                ENFORCE_DATA_SOVEREIGNTY=True,
            )
        assert "Invalid data residency region" in str(exc_info.value)

    def test_settings_passes_with_local_sovereign_hosts(self) -> None:
        settings = Settings(
            POSTGRES_HOST="localhost",
            REDIS_HOST="127.0.0.1",
            DATA_RESIDENCY_REGION="BD",
            ENFORCE_DATA_SOVEREIGNTY=True,
        )
        assert settings.db_host == "localhost"
        assert settings.redis_host == "127.0.0.1"
        assert settings.data_residency_region == "BD"
