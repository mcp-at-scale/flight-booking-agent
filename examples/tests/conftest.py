"""Shared fixtures for the example-server test suite.

The SDK pulls anyio >= 4.9, so async tests run on the anyio pytest plugin
(`@pytest.mark.anyio` plus this backend fixture) rather than pytest-asyncio.
"""

import os

# The §5.4 server wires an OTLP exporter at import time. Nothing is listening on
# localhost:4317 in CI, and the retry chatter drowns the actual test output.
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
