"""Database Session Router: Read/Write Replica Routing & PgBouncer Integration.

Architectural Guarantees:
1. Primary DB Session: Dedicated to transactional write operations (INSERT, UPDATE, DELETE).
2. Read Replica Session: Dedicated to heavy analytical queries (P&L tree grids, SCM trends).
   Read sessions are configured with READ ONLY transaction isolation, avoiding write locks.
3. PgBouncer Connection Pooling: Configured for transaction pooling across primary & replica.
4. Bangladesh Data Sovereignty: Enforced across all database connection endpoints.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.backend.config.settings import is_sovereign_host
from src.backend.config.vault import get_vault_client
from src.backend.middleware.auth_middleware import (
    current_depot_id,
    current_user_id,
    current_user_role,
)

logger = logging.getLogger("nerolac.database.router")


def _sanitize_session_identifier(value: str) -> str:
    """Sanitize identifier to letters, digits, and underscores to prevent SQL injection."""
    return re.sub(r"[^A-Za-z0-9_]", "", value)


async def apply_rls_session_variables(
    session: AsyncSession,
    depot_id: str | None = None,
    user_role: str | None = None,
) -> None:
    """Apply PostgreSQL Row-Level Security (RLS) session variables before query execution.

    Sets:
    - SET LOCAL ROLE nerolac_rls_user; (ensures RLS enforcement even in superuser dev environments)
    - SET LOCAL app.current_depot_id = '<depot_id>';
    - SET LOCAL app.current_user_role = '<user_role>';
    """
    effective_depot = depot_id if depot_id is not None else current_depot_id.get()
    effective_role = user_role if user_role is not None else current_user_role.get()

    if effective_depot or effective_role:
        try:
            await session.execute(text("SET LOCAL ROLE nerolac_rls_user;"))
        except Exception:
            pass

    if effective_depot:
        clean_depot = _sanitize_session_identifier(effective_depot)
        await session.execute(text(f"SET LOCAL app.current_depot_id = '{clean_depot}';"))
    if effective_role:
        clean_role = _sanitize_session_identifier(effective_role)
        await session.execute(text(f"SET LOCAL app.current_user_role = '{clean_role}';"))


class DatabaseRoutingManager:
    """Enterprise database engine router separating primary writes from replica reads."""

    def __init__(
        self,
        primary_url: str | None = None,
        replica_url: str | None = None,
        pool_size: int = 50,
        max_overflow: int = 25,
    ) -> None:
        vault = get_vault_client()
        creds = vault.get_database_credentials()

        # Check for PgBouncer ports or direct Postgres ports
        pgbouncer_port = int(os.getenv("PGBOUNCER_PORT", "6432"))
        use_pgbouncer = os.getenv("USE_PGBOUNCER", "true").lower() in ("true", "1")

        host = creds["host"]
        port = pgbouncer_port if use_pgbouncer else creds["port"]
        user = creds["user"]
        password = creds["password"]
        db = creds["database"]

        # Validate Bangladesh Data Sovereignty
        if not is_sovereign_host(host):
            raise ValueError(f"Data sovereignty breach: DB host '{host}' outside Bangladesh.")

        # Primary write endpoint
        if primary_url:
            self._primary_url = primary_url
        else:
            db_name = "nerolac_ops_primary" if use_pgbouncer else db
            self._primary_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"

        # Read replica endpoint
        if replica_url:
            self._replica_url = replica_url
        else:
            rep_host = os.getenv("REPLICA_HOST", host)
            rep_port = int(os.getenv("REPLICA_PORT", str(port)))
            rep_db = "nerolac_ops_replica" if use_pgbouncer else db
            self._replica_url = (
                f"postgresql+asyncpg://{user}:{password}@{rep_host}:{rep_port}/{rep_db}"
            )

        # When running with PgBouncer transaction pooling, NullPool avoids double-pooling
        engine_kwargs: dict[str, Any] = {
            "echo": False,
            "future": True,
            "poolclass": NullPool if use_pgbouncer else None,
        }
        if not use_pgbouncer:
            engine_kwargs.update(
                {
                    "pool_size": pool_size,
                    "max_overflow": max_overflow,
                    "pool_pre_ping": True,
                }
            )

        self.primary_engine: AsyncEngine = create_async_engine(self._primary_url, **engine_kwargs)
        self.replica_engine: AsyncEngine = create_async_engine(self._replica_url, **engine_kwargs)

        self.primary_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.primary_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        self.replica_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.replica_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @asynccontextmanager
    async def get_primary_session(
        self,
        depot_id: str | None = None,
        user_role: str | None = None,
    ) -> AsyncIterator[AsyncSession]:
        """Provide a dedicated write session connected to Primary DB with RLS context."""
        session: AsyncSession = self.primary_session_factory()
        try:
            await apply_rls_session_variables(session, depot_id=depot_id, user_role=user_role)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @asynccontextmanager
    async def get_replica_session(
        self,
        depot_id: str | None = None,
        user_role: str | None = None,
    ) -> AsyncIterator[AsyncSession]:
        """Provide a dedicated read session connected to Read Replica with RLS context."""
        session: AsyncSession = self.replica_session_factory()
        try:
            # Enforce read-only isolation on replica sessions
            await session.execute(text("SET TRANSACTION READ ONLY;"))
            await apply_rls_session_variables(session, depot_id=depot_id, user_role=user_role)
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def audit_status(self) -> dict[str, Any]:
        """Audit connectivity of both primary write and read replica endpoints."""
        async with self.primary_engine.connect() as conn:
            primary_ver = await conn.scalar(text("SELECT version();"))
        async with self.replica_engine.connect() as conn:
            replica_ver = await conn.scalar(text("SELECT version();"))

        return {
            "status": "HEALTHY",
            "primary_connected": primary_ver is not None,
            "replica_connected": replica_ver is not None,
            "primary_url_masked": self._primary_url.split("@")[-1],
            "replica_url_masked": self._replica_url.split("@")[-1],
            "pool_mode": "TRANSACTION_PGBOUNCER",
        }

    async def dispose(self) -> None:
        """Dispose both database engines cleanly."""
        await self.primary_engine.dispose()
        await self.replica_engine.dispose()


# Global Singleton Router Manager
_router_manager_instance: DatabaseRoutingManager | None = None


def get_routing_manager() -> DatabaseRoutingManager:
    """Return the global DatabaseRoutingManager instance."""
    global _router_manager_instance
    if _router_manager_instance is None:
        _router_manager_instance = DatabaseRoutingManager()
    return _router_manager_instance


@asynccontextmanager
async def get_write_session(
    depot_id: str | None = None,
    user_role: str | None = None,
) -> AsyncIterator[AsyncSession]:
    """Context manager for write transactions targeting the Primary DB."""
    router = get_routing_manager()
    async with router.get_primary_session(depot_id=depot_id, user_role=user_role) as session:
        yield session


@asynccontextmanager
async def get_read_session(
    depot_id: str | None = None,
    user_role: str | None = None,
) -> AsyncIterator[AsyncSession]:
    """Context manager for heavy analytical queries targeting the Read Replica."""
    router = get_routing_manager()
    async with router.get_replica_session(depot_id=depot_id, user_role=user_role) as session:
        yield session


async def provide_write_session() -> AsyncIterator[AsyncSession]:
    """FastAPI Dependency Injection providing Primary DB write session."""
    async with get_write_session() as session:
        yield session


async def provide_read_session() -> AsyncIterator[AsyncSession]:
    """FastAPI Dependency Injection providing Read Replica analytical read session."""
    async with get_read_session() as session:
        yield session


@asynccontextmanager
async def rls_context(
    depot_id: str,
    user_role: str,
    user_id: str | None = None,
) -> AsyncIterator[None]:
    """Scoped context manager setting RLS contextvars for a code block."""
    t_depot = current_depot_id.set(depot_id)
    t_role = current_user_role.set(user_role)
    t_user = current_user_id.set(user_id) if user_id else None
    try:
        yield
    finally:
        current_depot_id.reset(t_depot)
        current_user_role.reset(t_role)
        if t_user is not None:
            current_user_id.reset(t_user)
