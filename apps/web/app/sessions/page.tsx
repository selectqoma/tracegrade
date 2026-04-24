import { api, type SessionListResponse } from "@/lib/api";

function formatDuration(ms: number) {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatCost(usd: number | null) {
  if (usd === null || usd === 0) return "-";
  return `$${usd.toFixed(4)}`;
}

function formatTokens(n: number | null) {
  if (n === null) return "-";
  if (n > 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n > 1000) return `${(n / 1000).toFixed(1)}k`;
  return n.toString();
}

function timeAgo(date: string) {
  const seconds = Math.floor(
    (Date.now() - new Date(date).getTime()) / 1000
  );
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default async function SessionsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; has_error?: string; cursor?: string }>;
}) {
  const params = await searchParams;
  let data: SessionListResponse;

  try {
    const query = new URLSearchParams();
    if (params.q) query.set("q", params.q);
    if (params.has_error) query.set("has_error", params.has_error);
    if (params.cursor) query.set("cursor", params.cursor);
    data = await api<SessionListResponse>(
      `/api/sessions?${query.toString()}`,
      { next: { revalidate: 10 } }
    );
  } catch {
    data = { items: [], next_cursor: null };
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Sessions</h1>
        <div className="flex gap-2">
          <form className="flex gap-2">
            <input
              name="q"
              defaultValue={params.q || ""}
              placeholder="Search sessions..."
              className="bg-[var(--card)] border border-[var(--border)] rounded px-3 py-1.5 text-sm"
            />
            <select
              name="has_error"
              defaultValue={params.has_error || ""}
              className="bg-[var(--card)] border border-[var(--border)] rounded px-3 py-1.5 text-sm"
            >
              <option value="">All</option>
              <option value="true">Errors only</option>
              <option value="false">No errors</option>
            </select>
            <button
              type="submit"
              className="bg-[var(--accent)] text-white rounded px-3 py-1.5 text-sm"
            >
              Filter
            </button>
          </form>
        </div>
      </div>

      <div className="border border-[var(--border)] rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Session</th>
              <th className="px-4 py-3 font-medium">Last Seen</th>
              <th className="px-4 py-3 font-medium text-right">Traces</th>
              <th className="px-4 py-3 font-medium text-right">Spans</th>
              <th className="px-4 py-3 font-medium text-right">Tokens</th>
              <th className="px-4 py-3 font-medium text-right">Cost</th>
              <th className="px-4 py-3 font-medium text-center">Status</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td
                  colSpan={7}
                  className="px-4 py-12 text-center text-[var(--muted)]"
                >
                  No sessions found. Send some traces to get started.
                </td>
              </tr>
            )}
            {data.items.map((s) => (
              <tr
                key={s.id}
                className="border-b border-[var(--border)] hover:bg-[var(--card)]"
              >
                <td className="px-4 py-3">
                  <a
                    href={`/sessions/${s.id}`}
                    className="text-[var(--accent)] hover:underline font-mono text-xs"
                  >
                    {s.id.length > 24 ? `${s.id.slice(0, 24)}...` : s.id}
                  </a>
                </td>
                <td className="px-4 py-3 text-[var(--muted)]">
                  {timeAgo(s.last_seen)}
                </td>
                <td className="px-4 py-3 text-right">{s.trace_count}</td>
                <td className="px-4 py-3 text-right">{s.span_count}</td>
                <td className="px-4 py-3 text-right text-[var(--muted)]">
                  {formatTokens(
                    (s.total_tokens_in || 0) + (s.total_tokens_out || 0)
                  )}
                </td>
                <td className="px-4 py-3 text-right text-[var(--muted)]">
                  {formatCost(s.total_cost_usd)}
                </td>
                <td className="px-4 py-3 text-center">
                  {s.has_error ? (
                    <span className="inline-block w-2 h-2 rounded-full bg-[var(--error)]" />
                  ) : (
                    <span className="inline-block w-2 h-2 rounded-full bg-[var(--success)]" />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.next_cursor && (
        <div className="flex justify-center">
          <a
            href={`/sessions?cursor=${data.next_cursor}${params.q ? `&q=${params.q}` : ""}${params.has_error ? `&has_error=${params.has_error}` : ""}`}
            className="text-sm text-[var(--accent)] hover:underline"
          >
            Load more
          </a>
        </div>
      )}
    </div>
  );
}
