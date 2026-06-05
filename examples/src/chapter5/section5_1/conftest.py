"""Pytest fixtures for Chapter 5 §5.1 unit + integration tests.

Targets chapter3/section3_5 as the system under test. The fixtures wire
up an in-memory ClientSession bound to that server (no subprocess, no
network), patch the auth lookup to return a fake authenticated user,
and reset module-level state between tests so holds and bookings don't
leak across cases.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from mcp.client.session import ClientSession
from mcp.server.auth.provider import AccessToken
from mcp.shared.memory import create_client_server_memory_streams

from chapter3.section3_5 import mcp_server as server_module


@pytest.fixture(scope="session")
def event_loop():
    """One event loop per pytest session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def fake_access_token() -> AccessToken:
    """A valid-shaped AccessToken used to fake authentication in tests."""
    return AccessToken(
        token="fake-test-token",
        client_id="alice@example.com",
        scopes=["openid", "read:bookings", "write:bookings"],
        expires_at=None,
    )


@pytest.fixture
def authenticated(fake_access_token):
    """Patch get_access_token in the server module to return the fake token.

    Use this fixture in any test that exercises a tool that reads from
    get_access_token() (most state-changing tools do).
    """
    with patch.object(server_module, "get_access_token", return_value=fake_access_token):
        yield fake_access_token


@pytest.fixture
def unauthenticated():
    """Patch get_access_token to return None so we can test the auth-error path."""
    with patch.object(server_module, "get_access_token", return_value=None):
        yield


@pytest.fixture(autouse=True)
def reset_server_state():
    """Clear in-memory HOLDS and BOOKINGS between tests.

    autouse=True so every test starts with empty state without having to
    declare the dependency. Module-level state would otherwise leak from
    one test to the next.
    """
    yield
    server_module.HOLDS.clear()
    server_module.BOOKINGS.clear()


@pytest.fixture
async def mcp_session(authenticated):
    """Yield a ClientSession bound to the section3_5 server, in-process.

    The auth fixture is applied first so tools that read from the auth
    context find the fake user when the in-memory client invokes them.
    """
    async with create_client_server_memory_streams() as (client_streams, server_streams):
        server_read, server_write = server_streams
        server_task = asyncio.create_task(
            server_module.mcp._mcp_server.run(
                server_read,
                server_write,
                server_module.mcp._mcp_server.create_initialization_options(),
            )
        )
        try:
            client_read, client_write = client_streams
            async with ClientSession(client_read, client_write) as session:
                await session.initialize()
                yield session
        finally:
            server_task.cancel()
            try:
                await server_task
            except (asyncio.CancelledError, Exception):
                pass
