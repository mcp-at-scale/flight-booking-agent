# flight-booking-agent

The demo flight booking agent we will be building to demonstrate MCP capabilities as it evolves through the book.

## Layout

Each chapter section owns one self-contained server, cumulative on the section before it:

```
examples/src/chapter<N>/section<N_X_Y>/mcp_server.py
```

Shared flight data (airports, flight templates, search) lives in the `pyflight-internal` package. Chapter 5 also carries the test and observability examples for its own sections.

## Running a server

```bash
cd examples
uv run python -m chapter3.section3_1.mcp_server
```

Servers listen on `streamable-http` at port 9000. Point MCP Inspector at `http://localhost:9000/mcp/`.

## Tests

```bash
cd examples
uv run pytest tests/ src/chapter5/section5_1
```

Two suites, both guarding the book's claims rather than the agent's behaviour:

- `tests/test_server_smoke.py` imports every `mcp_server.py`, binds an in-memory `Client` to it, and asserts it negotiates **2026-07-28** and answers the list calls it advertises. This is what catches an SDK upgrade breaking a chapter.
- `tests/test_mrtr_regression.py` exercises §3.4's elicitation on both protocol eras. The server must return the question and let the client retry (multi round-trip requests); a regression to a server-initiated back channel fails the 2026 case.

Chapter 5 §5.3 evals are excluded: `mcp-agent` has not migrated to SDK v2 and needs a separate v1-pinned environment.

## Conformance

```bash
cd examples
uv run python scripts/conformance.py chapter3/section3_2
```

Runs the official MCP conformance suite at `--requirements 2026-07-28` and scores the result against `conformance-baseline.json`.

Two things to know before reading the output. The CLI is pinned to the `@alpha` tag, because npm `latest` predates this revision and rejects the version outright. And most raw failures are noise: the suite drives its own reference fixture server, so a chapter example fails every scenario reaching for a tool or resource it does not have. Only two families are scored, and `conformance-baseline.json` documents why each baselined failure is there.

Regenerate a baseline with `--update-baseline` after a deliberate change.

## SDK version

Pinned to `mcp[cli]==2.0.0` and `mcp-types==2.0.0` in `examples/pyproject.toml`. `mcp-types` tracks the SDK version exactly; do not pin it to a different number.
