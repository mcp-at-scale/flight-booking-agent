# Chapter 5 §5.3 Eval Suite

This directory contains the mcp-eval suite Chapter 5 §5.3 walks through.
Eight evals against the `chapter3/section3_5` flight-booking server,
covering paraphrase resilience, multi-turn state, and intent
disambiguation regressions.

## SDK v2 note

The rest of the examples are pinned to MCP Python SDK v2 (`mcp==2.0.0b1`).
The eval framework (`mcpevals`, via `mcp-agent`) has not migrated to v2 yet:
it still imports the v1-only `mcp.server.fastmcp` module. Until the framework
ships v2 support, run this eval suite in a separate environment pinned to the
v1 SDK (`mcp>=1.20,<2`). The `chapter3/section3_5` server under test is
unchanged by the migration, so the evals themselves do not need edits.

## What's here

| File | Purpose |
|---|---|
| `mcpeval.yaml` | Provider, model, server-spawn command, OAuth header injection |
| `evals/conftest.py` | Mints a demo HS256 token into `EVAL_DEMO_TOKEN`; marks long evals with `slow` |
| `evals/test_booking_intents.py` | The eight evals from §5.3 |

## Run locally

You need an Anthropic API key (or change the provider in `mcpeval.yaml`):

```bash
cd flight-booking-agent/examples
uv sync
export ANTHROPIC_API_KEY="sk-ant-..."
uv run pytest src/chapter5/section5_3/evals/
```

Each test costs one or more LLM API calls. The full suite costs under
$1 with Claude Sonnet 4.5 pricing as of mid-2026.

## Skip the expensive multi-turn evals during a quick local check

```bash
uv run pytest src/chapter5/section5_3/evals/ -m "not slow"
```

The `slow` marker is applied automatically to evals with `two_turn` or
`multi_turn` in their name.

## CI

The recommended cadence (see §5.3 Table 5.5):

| Trigger | What to run |
|---|---|
| PR to `main` | Full suite |
| Daily scheduled | Full suite |
| Before promoting a new model version | Full suite twice (old + new) |
| Pre-deploy to production | Full suite |
| Every commit on feature branch | Skip |

The §5.3 prose includes a complete GitHub Actions workflow that runs
on PR and daily. Adapt to GitLab CI / CircleCI / etc. by lifting the
`uv run pytest` step.

## Extending the suite

When you add a new tool to the server, add at least one eval that:

1. Phrases the user's intent in two different ways (paraphrase regression).
2. Asserts the new tool was called.
3. Asserts a sibling tool was *not* called (intent disambiguation).

Three evals per tool is the rough budget that keeps the suite under
a dollar per CI run for a 10-tool server.
