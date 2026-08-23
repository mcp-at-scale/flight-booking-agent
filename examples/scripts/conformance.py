#!/usr/bin/env python3
"""Run the official MCP conformance suite against a chapter example server.

    uv run python scripts/conformance.py chapter3/section3_2

Starts the server, runs `@modelcontextprotocol/conformance` at
`--requirements 2026-07-28`, then scores the result against the baseline in
`conformance-baseline.json`.

We do not aim for a clean sheet. The suite drives a reference fixture server with
its own tools and resources (`test://static-binary` and friends), so a chapter
example fails every scenario that reaches for a fixture it does not have. Those
failures say nothing about conformance. Two families of check do:

  wire-schema-valid   Present in every scenario. Validates each message the
                      server sent against the spec JSON schema for the
                      negotiated revision. Fixture-independent, so any failure
                      here is a real regression. Must stay at zero.

  server-stateless    The SEP-2575 scenario: per-request `_meta`, `serverInfo`
                      placement, capability rejection, subscription
                      notifications. Scored against a named baseline so a fix
                      or a regression both show up as a diff.

Requires node (for npx). Exits non-zero if either family regresses.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "conformance-baseline.json"
CONFORMANCE_PKG = "@modelcontextprotocol/conformance@alpha"
REQUIREMENTS = "2026-07-28"


# Every example server hardcodes `mcp.run(..., port=9000)`, matching the book's
# run instructions. We do not override it here: A0 does not touch example code.
SERVER_PORT = 9000


def _port_is_free(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def _wait_for(port: int, timeout: float = 45.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket() as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.25)
    return False


def _scenario_of(results_dir: str) -> str:
    base = os.path.basename(results_dir)
    return re.sub(r"^server-|-\d{4}-\d\d-\d\dT.*$", "", base)


def collect(out_dir: Path) -> dict[str, list[dict]]:
    """Map scenario name to its list of checks."""
    found: dict[str, list[dict]] = {}
    for path in glob.glob(str(out_dir / "**" / "checks.json"), recursive=True):
        found[_scenario_of(os.path.dirname(path))] = json.load(open(path))
    return found


def run_suite(section: str, port: int, out_dir: Path) -> dict[str, list[dict]]:
    module = f"{section.replace('/', '.')}.mcp_server"
    env = {**os.environ, "OTEL_SDK_DISABLED": "true"}

    server = subprocess.Popen(
        [sys.executable, "-m", module],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        if not _wait_for(port):
            raise SystemExit(f"server {module} did not come up on port {port}")

        subprocess.run(
            [
                "npx", "-y", CONFORMANCE_PKG, "server",
                "--url", f"http://127.0.0.1:{port}/mcp",
                "--requirements", REQUIREMENTS,
                "-o", str(out_dir),
            ],
            cwd=ROOT,
            check=False,
        )
        return collect(out_dir)
    finally:
        os.killpg(os.getpgid(server.pid), signal.SIGTERM)
        server.wait(timeout=15)


def score(section: str, checks: dict[str, list[dict]], baseline: dict) -> int:
    expected = set(baseline.get(section, {}).get("server_stateless_failures", []))
    problems = 0

    schema_fails = [
        (scen, c.get("errorMessage", ""))
        for scen, cs in checks.items()
        for c in cs
        if c["id"] == "wire-schema-valid" and c["status"] != "SUCCESS"
    ]
    total_schema = sum(1 for cs in checks.values() for c in cs if c["id"] == "wire-schema-valid")
    print(f"\nwire-schema-valid: {total_schema - len(schema_fails)}/{total_schema} clean")
    for scen, msg in schema_fails:
        print(f"  REGRESSION {scen}: {msg[:160]}")
        problems += 1

    actual = {
        c["id"]
        for c in checks.get("server-stateless", [])
        if c["status"] != "SUCCESS"
    }
    print(f"\nserver-stateless: {len(actual)} failing, {len(expected)} in baseline")
    for cid in sorted(actual - expected):
        print(f"  NEW FAILURE      {cid}")
        problems += 1
    for cid in sorted(expected - actual):
        print(f"  NOW FIXED        {cid}  (remove it from {BASELINE.name})")
        problems += 1

    return problems


def main() -> int:
    if not shutil.which("npx"):
        print("npx not found; install node to run the conformance gate", file=sys.stderr)
        return 2

    parser = argparse.ArgumentParser()
    parser.add_argument("section", help="e.g. chapter3/section3_2")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    out_dir = Path(args.out or ROOT / ".conformance" / args.section.replace("/", "-"))
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    if not _port_is_free(SERVER_PORT):
        print(
            f"port {SERVER_PORT} is already in use; stop whatever is bound to it "
            f"(the example servers hardcode that port)",
            file=sys.stderr,
        )
        return 2

    checks = run_suite(args.section, SERVER_PORT, out_dir)
    if not checks:
        print("no conformance results produced", file=sys.stderr)
        return 2

    baseline = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}

    if args.update_baseline:
        baseline.setdefault(args.section, {})["server_stateless_failures"] = sorted(
            c["id"] for c in checks.get("server-stateless", []) if c["status"] != "SUCCESS"
        )
        BASELINE.write_text(json.dumps(baseline, indent=2) + "\n")
        print(f"\nbaseline updated for {args.section}")
        return 0

    problems = score(args.section, checks, baseline)
    print("\nPASS" if problems == 0 else f"\nFAIL ({problems} to resolve)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
