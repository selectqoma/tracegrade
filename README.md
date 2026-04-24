# TraceGrade

Open-source, framework-agnostic tool that turns production AI agent failures into regression tests automatically.

**The problem:** AI agents break differently than normal software. A single LLM call might look fine while the sequence of tool calls produces a wrong answer three steps later. Existing tools either trace individual LLM calls (missing multi-turn failures) or run offline benchmarks (disconnected from production). Neither closes the loop.

**TraceGrade closes it:** trace → annotate → synthesize eval → regress in CI.

```
Production agent fails → you annotate what went wrong → TraceGrade generates a regression test → CI catches it next time
```

## Quick Start

### 1. Instrument your agent (3 lines)

```python
from tracegrade_sdk import instrument

instrument(service_name="my-agent", endpoint="http://localhost:8000/v1/traces")

# ...your existing agent code runs unchanged...
```

Works with any framework — Anthropic SDK, OpenAI, LangGraph, ADK, Goose, smolagents, or raw API calls. The SDK auto-patches known libraries via OpenTelemetry.

### 2. Start TraceGrade

```bash
git clone https://github.com/selectqoma/tracegrade.git
cd tracegrade
docker compose up
```

This starts:
- **API** on `localhost:8000` — receives traces, serves REST API
- **Web UI** on `localhost:3000` — browse sessions, annotate failures
- **Worker** — synthesizes evals and runs graders
- **Postgres** — sessions, annotations, evals, rubrics
- **ClickHouse** — span storage (optimized for trace queries)
- **Redis** — job queue

### 3. Browse failures in the UI

Open `http://localhost:3000/sessions`. You'll see your agent sessions with trace trees, span details, token counts, costs, and errors.

### 4. Annotate what went wrong

Click into a failed session. Expand the span tree. Find the span where things went wrong and annotate it:
- **Verdict**: good / neutral / bad
- **Failure mode**: `wrong_tool_choice`, `hallucinated_citation`, `infinite_loop`, `stale_context`, etc.
- **Note**: freeform description of what went wrong

### 5. Synthesize a regression test

TraceGrade takes your annotation + the origin trace and calls Claude to generate a structured eval:

```json
{
  "name": "agent should not hallucinate citations",
  "grader_type": "groundedness",
  "grader_config": {"context_field": "context", "output_field": "output"},
  "input_fixture": {"query": "summarize the Q3 report"},
  "expected_behavior": "output references only facts from the provided context"
}
```

You review and edit before saving. Evals are never auto-saved — human review is required.

### 6. Run in CI

```yaml
# .github/workflows/eval.yml
- uses: tracegrade/action@v1
  with:
    instance: ${{ secrets.TRACEGRADE_URL }}
    api_key: ${{ secrets.TRACEGRADE_KEY }}
    suite: default
    fail_on: regression
```

Or from the CLI:

```bash
pip install tracegrade
tracegrade eval run --suite default
```

## Architecture

```
┌─────────────────────────────────────────────┐
│           Your Agent Application            │
│  (LangGraph / ADK / Anthropic SDK / etc.)   │
│                                             │
│  from tracegrade_sdk import instrument      │
│  instrument(...)                            │
└──────────────────┬──────────────────────────┘
                   │ OTLP/HTTP
                   ▼
┌─────────────────────────────────────────────┐
│            Ingest (FastAPI)                 │
│  • OTLP receiver at /v1/traces             │
│  • Normalizes spans (GenAI semconv)         │
│  • Stitches sessions by session_id         │
│  • Batches writes to ClickHouse            │
│  • Upserts session metadata in Postgres    │
└──────┬──────────────────┬───────────────────┘
       │                  │
       ▼                  ▼
┌──────────────┐  ┌───────────────────┐
│  ClickHouse  │  │     Postgres      │
│  spans/traces│  │  sessions, annots │
│  (hot, TB)   │  │  evals, rubrics   │
│              │  │  runs, embeddings │
└──────┬───────┘  └──────┬────────────┘
       └────────┬────────┘
                ▼
┌─────────────────────────────────────────────┐
│              API (FastAPI)                  │
│  REST endpoints for all CRUD operations    │
└──────┬──────────────────┬───────────────────┘
       │                  │
       ▼                  ▼
┌──────────────┐  ┌───────────────────┐
│  Next.js UI  │  │   Eval Workers    │
│  Sessions    │  │  • Synthesis      │
│  Traces      │  │  • Grading        │
│  Annotations │  │  • Scheduled runs │
│  Evals/Runs  │  │                   │
└──────────────┘  └───────────────────┘
```

## How Eval Synthesis Works

This is the core differentiator. When you click "Synthesize eval" on an annotation:

1. **Context assembly** — TraceGrade fetches the origin trace tree and any existing rubrics for the project
2. **LLM call** — Sends the trace + annotations to Claude with a structured output schema
3. **Draft review** — You see the proposed eval side-by-side with the origin trace. Edit freely.
4. **Save** — Rubric + eval are persisted and added to the default suite
5. **CI picks it up** — Next run catches the regression

The synthesis prompt asks Claude to choose the right grader type for the failure mode, generate a minimal input fixture, and explain its rationale.

## Built-in Graders

| Grader | What it checks |
|--------|---------------|
| `llm_judge` | LLM evaluates output against rubric criteria |
| `exact_match` | Specific JSON fields match expected values |
| `tool_sequence` | Agent called tools in the expected order |
| `regex` | Output matches a regex pattern |
| `groundedness` | Output is supported by provided context (no hallucinations) |

## CLI Commands

```bash
tracegrade init                        # scaffold tracegrade.yaml
tracegrade login <url>                 # authenticate to an instance
tracegrade trace export <session_id>   # export session as JSON fixture
tracegrade eval list                   # list evals
tracegrade eval run [--suite S]        # run evals locally
tracegrade ci report --run-id <id>     # generate markdown CI report
```

## Configuration

`tracegrade.yaml` in your project root:

```yaml
project: my-agent
instance: https://tracegrade.internal
agent:
  entrypoint: myagent.main:run_agent
  version: ${GIT_SHA}
suites:
  - default
graders:
  llm_judge:
    model: claude-haiku-4-5-20251001
```

## Project Structure

```
tracegrade/
├── apps/
│   ├── api/              # FastAPI: ingest + REST API
│   ├── worker/           # arq workers: synthesis + grading
│   └── web/              # Next.js 15 UI
├── packages/
│   ├── cli/              # `pip install tracegrade`
│   ├── sdk-python/       # instrumentation SDK
│   └── graders/          # built-in grader implementations
├── migrations/
│   ├── postgres/          # pgvector schema
│   └── clickhouse/        # span table
├── examples/
│   └── raw-anthropic-sdk/ # example instrumented agent
├── docker-compose.yaml    # single-command deploy
└── .github/workflows/     # CI + eval action
```

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.13, FastAPI, Pydantic v2 |
| Queue | arq (Redis) |
| DB (metadata) | Postgres 17 + pgvector |
| DB (spans) | ClickHouse 25.x |
| Frontend | Next.js 15, Tailwind v4 |
| LLM | Anthropic Claude (synthesis + LLM judge grader) |
| Telemetry | OpenTelemetry GenAI semantic conventions |
| Deploy | Docker Compose |

## Who This Is For

- AI engineers running agents in production on any framework
- Small teams (2-20) who need more than print-debugging but can't justify per-seat SaaS pricing
- Enterprises with data residency needs who need self-hosted observability + evals

## Who This Is Not For

- Single-turn chatbot operators — the value scales with agent trajectory complexity
- Teams looking for prompt management, model routing, or synthetic data generation

## License

Apache 2.0
