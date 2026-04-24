export default function Home() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-2">TraceGrade</h1>
        <p className="text-[var(--muted)]">
          Turn production AI agent failures into regression tests automatically.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <a
          href="/sessions"
          className="block border border-[var(--border)] rounded-lg p-6 hover:border-[var(--accent)] transition-colors"
        >
          <h2 className="text-lg font-semibold mb-1">Sessions</h2>
          <p className="text-sm text-[var(--muted)]">
            Browse agent sessions, traces, and spans
          </p>
        </a>
        <a
          href="/evals"
          className="block border border-[var(--border)] rounded-lg p-6 hover:border-[var(--accent)] transition-colors"
        >
          <h2 className="text-lg font-semibold mb-1">Evals</h2>
          <p className="text-sm text-[var(--muted)]">
            View and manage regression test suites
          </p>
        </a>
        <a
          href="/runs"
          className="block border border-[var(--border)] rounded-lg p-6 hover:border-[var(--accent)] transition-colors"
        >
          <h2 className="text-lg font-semibold mb-1">Runs</h2>
          <p className="text-sm text-[var(--muted)]">
            Review eval run results and regressions
          </p>
        </a>
      </div>

      <div className="border border-[var(--border)] rounded-lg p-6 bg-[var(--card)]">
        <h2 className="text-lg font-semibold mb-3">Quick Start</h2>
        <pre className="text-sm text-[var(--muted)] overflow-x-auto">
{`# Instrument your agent (3 lines)
from tracegrade_sdk import instrument
instrument(service_name="my-agent", endpoint="http://localhost:8000/v1/traces")

# Run your agent as usual — traces flow automatically

# Then install the CLI
pip install tracegrade

# Export a failed session and create a regression test
tracegrade trace export <session_id> -o fixture.json
tracegrade eval run`}
        </pre>
      </div>
    </div>
  );
}
