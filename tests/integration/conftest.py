"""
Integration tests shared configuration.

Sets a dedicated PostgreSQL schema for tests to avoid interfering with the
application schema. The schema is dropped before and after the test session.
"""

import os
from typing import AsyncGenerator

import pytest

from src.data.connection_managers import ConnectionManager

TEST_SCHEMA = "helios_trading_test"


@pytest.fixture(scope="session", autouse=True)
async def use_test_schema() -> AsyncGenerator[None, None]:
    """Configure tests to use a dedicated DB schema and ensure teardown.

    - Forces DATABASE_SCHEMA to the test schema for the whole session
    - Drops the schema (if exists) before and after the session
    - Skips teardown silently if DB is not configured
    """

    # Force schema for the entire test session
    os.environ["DATABASE_SCHEMA"] = TEST_SCHEMA

    # Best-effort drop before session starts
    try:
        cm = ConnectionManager()
        await cm.connect_all()
        if cm.postgres and cm.postgres.pool is not None:
            await cm.postgres.execute(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE")
        await cm.disconnect_all()
    except Exception:
        # Environment may not be fully configured; ignore pre-drop failures
        pass

    yield

    # Drop after session ends to clean up
    try:
        cm = ConnectionManager()
        await cm.connect_all()
        if cm.postgres and cm.postgres.pool is not None:
            await cm.postgres.execute(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE")
        await cm.disconnect_all()
    except Exception:
        # Do not fail the session on cleanup issues
        pass
