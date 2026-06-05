"""pytest configuration for the Chapter 5 §5.3 mcp-eval suite.

mcp-eval's pytest plugin provides the `mcp_agent` fixture automatically
based on the mcpeval.yaml in the parent directory. This conftest exists
to mint the demo OAuth token the YAML's headers reference, and to add
a smoke-test marker so contributors can opt out of expensive evals
during a quick local check.
"""

from __future__ import annotations

import os
import time

import jwt
import pytest


# Reuse the demo HS256 secrets from chapter3/section3_5 so the spawned
# server accepts the token at handshake time. In a real deployment this
# would mint against the production identity provider.
DEMO_SECRET = "demo-secret-do-not-use-in-production"
DEMO_AUDIENCE = "flight-booking-mcp-server"
DEMO_ISSUER = "https://demo-issuer.example.com/"


def _mint_demo_token() -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "iss": DEMO_ISSUER,
            "aud": DEMO_AUDIENCE,
            "sub": "eval-suite@example.com",
            "scope": "openid read:bookings write:bookings",
            "iat": now,
            "exp": now + 3600,
        },
        DEMO_SECRET,
        algorithm="HS256",
    )


@pytest.fixture(scope="session", autouse=True)
def set_demo_token():
    """Populate EVAL_DEMO_TOKEN before mcp-eval reads mcpeval.yaml."""
    os.environ["EVAL_DEMO_TOKEN"] = _mint_demo_token()
    yield


def pytest_collection_modifyitems(config, items):
    """Mark expensive evals so contributors can skip them with `-m 'not slow'`."""
    slow_marker = pytest.mark.slow
    for item in items:
        # Multi-turn conversational evals tend to be the costly ones.
        if "two_turn" in item.name or "multi_turn" in item.name:
            item.add_marker(slow_marker)
