import { api, type EvalItem } from "@/lib/api";

export default async function EvalDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let evalItem: EvalItem;
  try {
    evalItem = await api<EvalItem>(`/api/evals/${id}`);
  } catch {
    return (
      <div className="text-center py-12 text-[var(--muted)]">
        Eval not found
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <a
          href="/evals"
          className="text-sm text-[var(--muted)] hover:text-[var(--fg)]"
        >
          &larr; Evals
        </a>
        <h1 className="text-xl font-bold mt-1">{evalItem.name}</h1>
        <p className="text-sm text-[var(--muted)]">
          Version {evalItem.version} &middot;{" "}
          {evalItem.enabled ? "Enabled" : "Disabled"}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="border border-[var(--border)] rounded-lg p-4">
          <h2 className="text-sm font-medium mb-3">Input Fixture</h2>
          <pre className="text-xs bg-black/30 p-3 rounded overflow-x-auto max-h-96 overflow-y-auto">
            {JSON.stringify(evalItem.input_fixture, null, 2)}
          </pre>
        </div>

        <div className="border border-[var(--border)] rounded-lg p-4">
          <h2 className="text-sm font-medium mb-3">Expected Output</h2>
          <pre className="text-xs bg-black/30 p-3 rounded overflow-x-auto max-h-96 overflow-y-auto">
            {evalItem.expected
              ? JSON.stringify(evalItem.expected, null, 2)
              : "No expected output specified (using rubric-based grading)"}
          </pre>
        </div>
      </div>

      {evalItem.origin_trace_id && (
        <div className="text-sm">
          <span className="text-[var(--muted)]">Origin trace: </span>
          <a
            href={`/traces/${evalItem.origin_trace_id}`}
            className="text-[var(--accent)] hover:underline font-mono"
          >
            {evalItem.origin_trace_id.slice(0, 16)}...
          </a>
        </div>
      )}
    </div>
  );
}
