"""Smoke tests for every chapter example server.

One parametrized test per server. Each imports the module, binds an in-memory
Client to its module-level `mcp`, and exercises the primitives the server
advertises. This is the gate that catches an SDK API change breaking a chapter:
without it, a bad `mcp` upgrade shows up as a reader's bug report.

Kept deliberately shallow. Behaviour is Chapter 5's job; this only asserts each
server starts, negotiates a protocol version, and answers its list calls.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from mcp.client import Client
from mcp.server import MCPServer

SRC = Path(__file__).resolve().parent.parent / "src"

# Ch5 §5.3 evals run against a v1-pinned environment (mcp-agent has not migrated
# to v2), so there is no server module there to smoke.
SERVERS = sorted(SRC.glob("chapter*/section*/mcp_server.py"))

# §2.1.2 is the "initialize the server" section. It deliberately ships no tools;
# the first ones arrive in §2.1.3. Anywhere else, an empty tool list is a bug.
TOOLLESS_BY_DESIGN = {"chapter2/section2_1_2"}


def _load(path: Path) -> MCPServer:
    """Import a server module by path and hand back its module-level `mcp`."""
    name = f"_smoke_{path.parent.parent.name}_{path.parent.name}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, f"could not build an import spec for {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

    mcp = getattr(module, "mcp", None)
    assert isinstance(mcp, MCPServer), (
        f"{path} has no module-level `mcp = MCPServer(...)`; the smoke harness "
        f"and the book's run instructions both rely on that name"
    )
    return mcp


def _ident(path: Path) -> str:
    return f"{path.parent.parent.name}/{path.parent.name}"


assert SERVERS, f"no example servers discovered under {SRC}"


@pytest.mark.anyio
@pytest.mark.parametrize("path", SERVERS, ids=[_ident(p) for p in SERVERS])
async def test_server_answers_discovery(path: Path) -> None:
    """The server starts, negotiates 2026-07-28, and answers its list calls."""
    mcp = _load(path)

    async with Client(mcp) as client:
        # Auto mode probes server/discover and falls back to initialize. Landing
        # on 2026-07-28 is the assertion that matters: it means the server is
        # serving the stateless revision, not just starting up.
        assert client.protocol_version == "2026-07-28", (
            f"{_ident(path)} negotiated {client.protocol_version}, expected the "
            f"2026-07-28 stateless revision"
        )

        caps = client.server_capabilities
        assert caps is not None, f"{_ident(path)} advertised no capabilities"

        # Only call what the server actually advertises. Not every chapter
        # section has resources or prompts, and asking anyway proves nothing.
        tools = await client.list_tools()
        if _ident(path) not in TOOLLESS_BY_DESIGN:
            assert tools.tools, f"{_ident(path)} advertises no tools"

        if caps.resources is not None:
            await client.list_resources()

        if caps.prompts is not None:
            await client.list_prompts()
