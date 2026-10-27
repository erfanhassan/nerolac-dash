"""Nerolac Dash Enterprise Settings & Bangladesh Data Sovereignty Validation.

Enforces:
1. Strict Bangladesh Data Sovereignty rules: Database & Redis residency in BD.
2. Integration with HashiCorp Vault / Azure Key Vault (zero raw secrets in .env).
3. Pydantic v2 validation and typed settings.
"""

from __future__ import annotations

import ipaddress
import logging

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.backend.config.vault import get_vault_client

logger = logging.getLogger("nerolac.config")


class DataSovereigntyViolationError(ValueError):
    """Raised when database or cache host violates Bangladesh Data Sovereignty mandate."""


# Approved sovereign domains, cloud regions, and network CIDRs for Bangladesh residency
SOVEREIGN_DOMAINS = (
    ".bd",
    ".nerolacbd.com",
    ".gov.bd",
    "localhost",
)

SOVEREIGN_REGIONS = {
    "BD",
    "BD-DHAKA-1",
    "BD-CENTRAL-1",
    "BD-KALIAKOIR-1",
}

# RFC 1918 private subnets and loopback allowed for local/on-premise enterprise deployments
SOVEREIGN_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    # National Data Center (NDC) Bangladesh dedicated IP ranges
    ipaddress.ip_network("103.48.16.0/22"),
]


def is_sovereign_host(host: str) -> bool:
    """Verify whether a host or IP resides within Bangladesh sovereign boundaries."""
    cleaned_host = host.strip().lower()

    # 1. Match allowed domain suffixes and localhost
    if any(cleaned_host.endswith(dom) or cleaned_host == dom for dom in SOVEREIGN_DOMAINS):
        return True

    # 2. Check IP address against approved CIDR networks
    try:
        ip = ipaddress.ip_address(cleaned_host)
        return any(ip in net for net in SOVEREIGN_PRIVATE_NETWORKS)
    except ValueError:
        # Not a raw IP, so it is a hostname that did not match approved sovereign domain suffix
        pass

    # 3. Explicit foreign cloud regions are rejected
    foreign_cloud_indicators = [
        "amazonaws.com",
        "azure.com",
        "google.com",
        "digitalocean.com",
        "oraclecloud.com",
        "us-east",
        "us-west",
        "eu-west",
        "ap-southeast",
    ]
    if any(indicator in cleaned_host for indicator in foreign_cloud_indicators):
        return False

    return False


class Settings(BaseSettings):
    """Enterprise application configuration with built-in data sovereignty validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Application Metadata
    app_name: str = "Nerolac Operations Dashboard"
    environment: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")

    # Bangladesh Data Sovereignty Mandate
    data_residency_region: str = Field(default="BD", alias="DATA_RESIDENCY_REGION")
    enforce_data_sovereignty: bool = Field(default=True, alias="ENFORCE_DATA_SOVEREIGNTY")

    # Host & Port
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")  # nosec
    api_port: int = Field(default=8000, alias="API_PORT")

    # Database and Cache Hosts (Credentials loaded via Vault)
    db_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    db_port: int = Field(default=5432, alias="POSTGRES_PORT")
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")

    @model_validator(mode="after")
    def validate_data_sovereignty(self) -> Settings:
        """Validate database and cache storage complies with Bangladesh Data Sovereignty."""
        if not self.enforce_data_sovereignty:
            logger.warning("Data sovereignty enforcement is explicitly disabled.")
            return self

        # 1. Validate region code
        if self.data_residency_region.upper() not in SOVEREIGN_REGIONS:
            raise DataSovereigntyViolationError(
                f"Invalid data residency region '{self.data_residency_region}'. "
                f"Sovereignty requires one of: {sorted(SOVEREIGN_REGIONS)}"
            )

        # 2. Validate database host residency
        if not is_sovereign_host(self.db_host):
            raise DataSovereigntyViolationError(
                f"Bangladesh Data Sovereignty Violation: Database host '{self.db_host}' is outside "
                "sovereign boundaries. Database residency must be in Bangladesh or local infra."
            )

        # 3. Validate Redis cache host residency
        if not is_sovereign_host(self.redis_host):
            raise DataSovereigntyViolationError(
                f"Bangladesh Data Sovereignty Violation: Redis host '{self.redis_host}' is outside "
                "sovereign boundaries. Cache residency must be in Bangladesh or local infra."
            )

        return self

    def get_database_url(self) -> str:
        """Retrieve dynamic database connection URL from Vault."""
        vault = get_vault_client()
        creds = vault.get_database_credentials()
        return creds["connection_string"]

    def get_redis_url(self) -> str:
        """Retrieve dynamic Redis connection URL from Vault."""
        vault = get_vault_client()
        creds = vault.get_redis_credentials()
        return creds["url"]


# Global cached settings instance
_settings_instance: Settings | None = None


def get_settings() -> Settings:
    """Return the global Settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
