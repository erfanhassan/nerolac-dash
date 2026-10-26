"""Unit and integration test verifying PostgreSQL 16 schema integrity."""

from __future__ import annotations

import pytest

from scripts.db.verify_schema_integrity import verify_schema


@pytest.mark.asyncio
async def test_postgresql_schema_integrity() -> None:
    """Assert that all 19 tables, 4 enums, and 6 composite indexes match DDL."""
    is_valid = await verify_schema()
    assert is_valid is True
