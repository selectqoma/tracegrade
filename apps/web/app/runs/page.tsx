import { api, type Run } from "@/lib/api";

function statusColor(status: string) {
  switch (status) {
    case "completed":
      return "text-[var(--success)]";
    case "failed":
      return "text-[var(--error)]";
    case "running":
      return "text-[var(--warning)]";
    default:
      return "text-[var(--muted)]";
  }
}

export default async function RunsPage() {
  // The API doesn't have a list runs endpoint yet, so we show a placeholder
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Runs</h1>
      </div>

      <div className="border border-[var(--border)] rounded-lg p-6">
        <p className="text-[var(--muted)] text-sm mb-4">
          Eval runs will appear here after you trigger them via the CLI or CI.
        </p>
        <pre className="text-xs bg-black/30 p-3 rounded">
{`# Run evals from the CLI
tracegrade eval run --suite default

# Or trigger from CI
- uses: tracegrade/action@v1
  with:
    instance: \${{ secrets.TRACEGRADE_URL }}
    api_key: \${{ secrets.TRACEGRADE_KEY }}
    suite: default
    fail_on: regression`}
        </pre>
      </div>
    </div>
  );
}
