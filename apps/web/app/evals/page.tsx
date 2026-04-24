import { api, type EvalItem } from "@/lib/api";

export default async function EvalsPage() {
  let evals: EvalItem[];
  try {
    evals = await api<EvalItem[]>("/api/evals", { next: { revalidate: 10 } });
  } catch {
    evals = [];
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Evals</h1>
      </div>

      <div className="border border-[var(--border)] rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Suite</th>
              <th className="px-4 py-3 font-medium">Version</th>
              <th className="px-4 py-3 font-medium text-center">Enabled</th>
              <th className="px-4 py-3 font-medium">Created</th>
            </tr>
          </thead>
          <tbody>
            {evals.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-12 text-center text-[var(--muted)]"
                >
                  No evals yet. Annotate a session failure and synthesize an
                  eval to get started.
                </td>
              </tr>
            )}
            {evals.map((e) => (
              <tr
                key={e.id}
                className="border-b border-[var(--border)] hover:bg-[var(--card)]"
              >
                <td className="px-4 py-3">
                  <a
                    href={`/evals/${e.id}`}
                    className="text-[var(--accent)] hover:underline"
                  >
                    {e.name}
                  </a>
                </td>
                <td className="px-4 py-3 font-mono text-xs text-[var(--muted)]">
                  {e.suite_id.slice(0, 8)}
                </td>
                <td className="px-4 py-3">v{e.version}</td>
                <td className="px-4 py-3 text-center">
                  {e.enabled ? (
                    <span className="text-[var(--success)]">Yes</span>
                  ) : (
                    <span className="text-[var(--muted)]">No</span>
                  )}
                </td>
                <td className="px-4 py-3 text-[var(--muted)]">
                  {new Date(e.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
