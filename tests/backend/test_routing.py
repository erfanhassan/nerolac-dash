"""Unit and integration tests for Database Session Router."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from src.backend.database.session_router import (
    get_read_session,
    get_routing_manager,
    get_write_session,
)


@pytest.mark.asyncio
async def test_routing_manager_audit() -> None:
    router = get_routing_manager()
    status = await router.audit_status()
    assert status["status"] == "HEALTHY"
    assert status["primary_connected"] is True
    assert status["replica_connected"] is True


@pytest.mark.asyncio
async def test_read_replica_session_read_only() -> None:
    async with get_read_session() as session:
        count = await session.scalar(text("SELECT count(*) FROM nerolac_ops.skus;"))
        assert count is not None
        assert count >= 0


@pytest.mark.asyncio
async def test_write_session_transaction() -> None:
    test_id = "TEST_ROUTER_DEPOT"
    async with get_write_session() as session:
        await session.execute(
            text(
                """
                INSERT INTO nerolac_ops.depots (depot_id, depot_code, depot_name, region)
                VALUES (:id, :code, :name, :region)
                ON CONFLICT (depot_id) DO NOTHING;
                """
            ),
            {"id": test_id, "code": "CODE_TEST_ROUTER", "name": "Router Test", "region": "Sylhet"},
        )

    # Verify and clean up
    async with get_write_session() as session:
        found = await session.scalar(
            text("SELECT depot_name FROM nerolac_ops.depots WHERE depot_id = :id;"),
            {"id": test_id},
        )
        assert found == "Router Test"
        await session.execute(
            text("DELETE FROM nerolac_ops.depots WHERE depot_id = :id;"),
            {"id": test_id},
        )
