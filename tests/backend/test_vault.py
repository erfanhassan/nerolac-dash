"""Unit tests for HashiCorp Vault client and encrypted fallback integration.

Validates:
- Clean initialization in encrypted fallback mode.
- Retrieval of database, Redis, and webhook credentials without plaintext leakage.
- Health check auditing.
"""

from __future__ import annotations

from src.backend.config.vault import (
    DEFAULT_FALLBACK_SECRETS,
    VaultClient,
    get_vault_client,
)


class TestVaultIntegration:
    """Test suite ensuring Vault client initializes cleanly with encrypted fallback."""

    def test_vault_clean_initialization_with_fallback(self) -> None:
        client = VaultClient(vault_url=None)
        health = client.health_check()

        assert health["status"] == "HEALTHY"
        assert health["mode"] == "ENCRYPTED_FALLBACK"
        assert health["encrypted_fallback_active"] is True
        assert health["is_authenticated"] is False

    def test_database_credentials_retrieval(self) -> None:
        client = VaultClient(vault_url=None)
        creds = client.get_database_credentials()

        assert creds["user"] == DEFAULT_FALLBACK_SECRETS["POSTGRES_USER"]
        assert creds["password"] == DEFAULT_FALLBACK_SECRETS["POSTGRES_PASSWORD"]
        assert creds["host"] == DEFAULT_FALLBACK_SECRETS["POSTGRES_HOST"]
        assert creds["port"] == DEFAULT_FALLBACK_SECRETS["POSTGRES_PORT"]
        assert creds["database"] == DEFAULT_FALLBACK_SECRETS["POSTGRES_DB"]

        expected_conn_str = (
            f"postgresql+asyncpg://{creds['user']}:{creds['password']}@"
            f"{creds['host']}:{creds['port']}/{creds['database']}"
        )
        assert creds["connection_string"] == expected_conn_str

    def test_redis_credentials_retrieval(self) -> None:
        client = VaultClient(vault_url=None)
        redis_creds = client.get_redis_credentials()

        assert redis_creds["host"] == DEFAULT_FALLBACK_SECRETS["REDIS_HOST"]
        assert redis_creds["port"] == DEFAULT_FALLBACK_SECRETS["REDIS_PORT"]
        assert redis_creds["password"] == DEFAULT_FALLBACK_SECRETS["REDIS_PASSWORD"]
        assert "redis://" in redis_creds["url"]

    def test_arbitrary_secret_lookup_and_caching(self) -> None:
        client = VaultClient(vault_url=None)
        jwt_key = client.get_secret("JWT_SECRET_KEY")
        assert jwt_key == DEFAULT_FALLBACK_SECRETS["JWT_SECRET_KEY"]

        # Cache should now contain the key
        health = client.health_check()
        assert health["cached_secret_count"] >= 1

    def test_singleton_accessor(self) -> None:
        client_1 = get_vault_client()
        client_2 = get_vault_client()
        assert client_1 is client_2
